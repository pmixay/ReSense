"""Raw-timestamp compensation for the offline H1 reference, not production."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
from scipy.linalg import expm, logm
from scipy.spatial.transform import Rotation

import reference
from reference import CACHES, HERE, WORK, near_rails, pcd, register

sys.path.insert(0, str(reference.ROOT / 'ros2_ws/src/resense_ros'))
from resense_ros.fastcloud import decode, parse_pointcloud2  # noqa: E402


def compensate(xyz, fraction, transform):
    w = Rotation.from_matrix(transform[:3, :3]).as_rotvec()
    v = np.asarray(logm(transform).real[:3, 3])
    theta = float(np.linalg.norm(w))
    f = np.asarray(fraction, float)
    cross = np.cross(w, xyz)
    cross2 = np.cross(w, cross)
    wv, wwv = np.cross(w, v), np.cross(w, np.cross(w, v))
    if theta < 1e-7:
        a, b, c = f, .5 * f * f, f ** 3 / 6
    else:
        a = np.sin(theta * f) / theta
        b = (1 - np.cos(theta * f)) / theta ** 2
        c = (theta * f - np.sin(theta * f)) / theta ** 3
    return xyz + a[:, None] * cross + b[:, None] * cross2 + f[:, None] * v + b[:, None] * wv + c[:, None] * wwv


def prepare(name):
    cache = CACHES[name]
    bag = Path('/tmp/opencode/resense-b4-data/for_hackathon') / cache.name / (cache.name + '_0.db3')
    records = json.loads((WORK / f'sequence-{name}-v2.json').read_text())['rows']
    target = WORK / f'timing-{name}'
    target.mkdir(exist_ok=False)
    manifest = []
    with sqlite3.connect(f'file:{bag}?mode=ro', uri=True) as connection:
        cursor = connection.execute("SELECT m.data FROM messages m JOIN topics t ON m.topic_id=t.id WHERE t.type='sensor_msgs/msg/PointCloud2' ORDER BY m.timestamp LIMIT ?", (len(records),))
        for i, (raw,) in enumerate(cursor):
            msg = parse_pointcloud2(raw)
            xyz, _, _, _, _ = decode(msg, 2.5, 250.)
            with np.load(cache / f'f_{i:05d}.npz') as data:
                assert np.array_equal(data['xyz'], xyz), (name, i)
            field = next(f for f in msg.fields if f.name == 'timestamp')
            dtype = np.dtype(dict(names=['xyz', 'timestamp'], formats=[('f4', 3), '<f8'],
                                  offsets=[0, field.offset], itemsize=msg.point_step))
            points = np.frombuffer(msg.data, dtype=dtype)
            coords = points['xyz']
            x, y, z = coords.T
            r2 = x ** 2
            r2 += y * y
            r2 += z * z
            keep = np.isfinite(r2) & (r2 > .0025) & (r2 >= 2.5 ** 2) & (r2 <= 250. ** 2)
            assert np.array_equal(coords[keep], xyz)
            offsets = points['timestamp'][keep] - records[i]['stamp']
            assert offsets.min() >= -.001 and offsets.max() <= .101
            np.savez_compressed(target / f'f_{i:05d}.npz', dt=offsets.astype(np.float32))
            manifest.append(dict(i=i, raw_sha256=hashlib.sha256(raw).hexdigest(), points=len(xyz),
                dt_min=float(offsets.min()), dt_max=float(offsets.max()), cached_XYZ_byte_equal=True))
    assert len(manifest) == len(records)
    with (HERE / f'timestamp-alignment-{name}.json').open('x') as stream:
        json.dump(manifest, stream, indent=2)
    print('ALIGNED', name, len(manifest), flush=True)


def sequence(name):
    seed_rows = json.loads((WORK / f'sequence-{name}-v2.json').read_text())['rows']
    primary_poses, alternate_poses, records = [np.eye(4)], [np.eye(4)], []
    previous = alternate_previous = None
    guess = alternate_guess = np.eye(4)
    for i, row in enumerate(seed_rows):
        xyz, digest = reference.raw_cloud(CACHES[name], i)
        with np.load(WORK / f'timing-{name}' / f'f_{i:05d}.npz') as data:
            dt = data['dt']
        j = min(i + 1, len(seed_rows) - 1)
        period = seed_rows[j]['stamp'] - seed_rows[j - 1]['stamp']
        motion = np.asarray(seed_rows[j]['primary']['T'])
        corrected = compensate(xyz, dt / period, motion)
        current, alternate_current = pcd(corrected), pcd(corrected, True)
        saved = dict(i=i, stamp=row['stamp'], input_sha256=digest, rails=near_rails(corrected))
        if previous is not None:
            primary, alternate = register(current, previous, guess), register(alternate_current, alternate_previous, alternate_guess, True)
            guess, alternate_guess = np.asarray(primary['T']), np.asarray(alternate['T'])
            primary_poses.append(primary_poses[-1] @ guess)
            alternate_poses.append(alternate_poses[-1] @ alternate_guess)
            saved.update(primary=primary, alternate=alternate,
                speed_mps=float(np.linalg.norm(guess[:3, 3]) / (row['stamp'] - seed_rows[i - 1]['stamp'])))
        saved.update(pose=primary_poses[-1].tolist(), alternate_pose=alternate_poses[-1].tolist())
        records.append(saved)
        previous, alternate_previous = current, alternate_current
    with (WORK / f'sequence-{name}-deskew.json').open('x') as stream:
        json.dump(dict(name=name, rows=records), stream, indent=2)
    print('DESKEWED', name, len(records), flush=True)


def controls():
    rng = np.random.default_rng(3)
    points = rng.normal(size=(100, 3))
    fraction = np.linspace(0, .333, 100)
    twist = np.zeros((4, 4))
    twist[:3, :3] = [[0, -.004, .001], [.004, 0, -.002], [-.001, .002, 0]]
    twist[:3, 3] = [1.5, .03, .01]
    transform = expm(twist)
    wanted = np.asarray([(expm(twist * f) @ np.r_[point, 1.])[:3] for point, f in zip(points, fraction, strict=True)])
    actual = compensate(points, fraction, transform)
    assert np.max(np.abs(actual - wanted)) < 1e-8
    assert np.max(np.abs(compensate(points, np.zeros(100), transform) - points)) == 0
    print('CONTROL', float(np.max(np.abs(actual - wanted))), 'max_shift', float(np.max(np.linalg.norm(actual - points, axis=1))), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'sequence', 'controls'])
    parser.add_argument('--name', choices=['A', 'C'])
    args = parser.parse_args()
    {'prepare': prepare, 'sequence': sequence, 'controls': lambda _: controls()}[args.phase](args.name)


if __name__ == '__main__':
    main()
