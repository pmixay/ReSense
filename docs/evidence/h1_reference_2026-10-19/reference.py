"""Detector-free near rails and full rigid scan registration for H1 analysis."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import open3d as o3d
from scipy.signal import find_peaks

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-reference')
R_VS = np.array([[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]])
CACHES = {
    'A': Path('/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT'),
    'C': Path('/tmp/opencode/r3-h1/supplement-range/decoded/roundT_pressureGate_roundT'),
}
INITIAL_METHOD = False


def raw_cloud(cache, index):
    path = cache / f'f_{index:05d}.npz'
    with np.load(path) as data:
        return (data['xyz'].astype(np.float64) @ R_VS.T), hashlib.sha256(path.read_bytes()).hexdigest()


def near_rails(xyz):
    """Raw bed detrending and independent lateral ridge pairing in three slabs.

    No production model, percentile helper or rail finder is imported. Ambiguous
    raw alternatives are retained and are not chosen by proximity to a model.
    """
    p = xyz[(xyz[:, 0] >= 6) & (xyz[:, 0] < 28) & (np.abs(xyz[:, 1]) < 2.2) & (xyz[:, 2] < -.4)]
    if len(p) < 200:
        return dict(accepted=False, slabs=[], reason='insufficient_near_points')
    bx, bz = [], []
    for x0 in np.arange(6., 28., 1.):
        z = p[(p[:, 0] >= x0) & (p[:, 0] < x0 + 1) & (np.abs(p[:, 1]) < 1.2), 2]
        if len(z) >= 10:
            bx.append(x0 + .5)
            bz.append(float(np.percentile(z, 20)))
    if len(bx) < 8:
        return dict(accepted=False, slabs=[], reason='insufficient_bed_bins')
    coef = np.polyfit(bx, bz, 1)
    for _ in range(3):
        residual = np.asarray(bz) - np.polyval(coef, bx)
        keep = np.abs(residual) < .12
        if keep.sum() < 6:
            return dict(accepted=False, slabs=[], reason='inconsistent_bed')
        coef = np.polyfit(np.asarray(bx)[keep], np.asarray(bz)[keep], 1)
    heights = p[:, 2] - np.polyval(coef, p[:, 0])
    edges = np.arange(-2.2, 2.20001, .05)
    centres = (edges[:-1] + edges[1:]) / 2
    slabs = []
    for x0, x1 in [(6., 13.), (13., 20.), (20., 27.)]:
        sel = (p[:, 0] >= x0) & (p[:, 0] < x1)
        cloud, h = p[sel], heights[sel]
        profile = np.full(len(centres), np.nan)
        counts = np.zeros(len(centres), int)
        bins = np.searchsorted(edges, cloud[:, 1], side='right') - 1
        for j in range(len(centres)):
            z = h[bins == j]
            counts[j] = len(z)
            if len(z) >= 8:
                profile[j] = np.percentile(z, 85)
        prominence = np.full(len(centres), np.nan)
        for j in range(5, len(centres) - 5):
            around = np.r_[profile[j - 5:j - 2], profile[j + 3:j + 6]]
            if np.isfinite(profile[j]) and np.isfinite(around).sum() >= 4:
                prominence[j] = profile[j] - np.nanmedian(around)
        peaks, _ = find_peaks(np.nan_to_num(prominence, nan=-1.), height=.06, distance=3)
        peaks = [j for j in peaks if .06 < profile[j] < .55]
        pairs = []
        for i, left in enumerate(peaks):
            for right in peaks[i + 1:]:
                width = centres[right] - centres[left]
                if abs(width - 1.59) > .08 or abs(profile[right] - profile[left]) > .15:
                    continue
                centre = float((centres[left] + centres[right]) / 2)
                if abs(centre) > .8:
                    continue
                heads = []
                for j in [left, right]:
                    support = (bins == j) & (np.abs(h - profile[j]) <= .04)
                    points = cloud[support]
                    heads.append(dict(y=float(np.median(points[:, 1])), z=float(np.median(points[:, 2])),
                        x=float(np.median(points[:, 0])), n=len(points), sample_xyz=points[:8].tolist()))
                pairs.append(dict(centre=float(np.mean([head['y'] for head in heads])),
                    station=float(np.mean([head['x'] for head in heads])), heads=heads,
                    prominence=float(min(prominence[left], prominence[right])), spacing=float(width)))
        slabs.append(dict(range=[x0, x1], pairs=pairs,
            profile=dict(y=centres.tolist(), height=np.where(np.isfinite(profile), profile, None).tolist(),
                         prominence=np.where(np.isfinite(prominence), prominence, None).tolist(), counts=counts.tolist())))
    chosen = [s['pairs'][0] for s in slabs if len(s['pairs']) == 1]
    accepted = len(chosen) >= 2 and not any(len(s['pairs']) > 1 for s in slabs)
    return dict(accepted=accepted, reason='paired' if accepted else 'missing_or_ambiguous_pair',
                bed_coef=coef.tolist(), slabs=slabs, chosen=chosen if accepted else [])


def pcd(xyz, alternate=False):
    x, y, z = xyz.T
    if INITIAL_METHOD:
        use = (x > 3) & (x < (60 if alternate else 80)) & (np.abs(y) < 6) & ((np.abs(y) > 1.4) | (z < -.5))
    else:
        use = (x > (5 if alternate else 3)) & (x < (65 if alternate else 80)) & (np.abs(y) < 6)
    cloud = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz[use]))
    cloud = cloud.voxel_down_sample(.25 if alternate else .15)
    cloud.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=.75 if alternate else .6, max_nn=30))
    return cloud


def register(current, previous, guess, alternate=False):
    estimate = (o3d.pipelines.registration.TransformationEstimationPointToPoint() if INITIAL_METHOD and alternate
                else o3d.pipelines.registration.TransformationEstimationPointToPlane())
    result = o3d.pipelines.registration.registration_icp(current, previous, .6 if INITIAL_METHOD else .5, guess, estimate,
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=50 if INITIAL_METHOD else 40))
    return dict(T=result.transformation.tolist(), fitness=float(result.fitness), rmse=float(result.inlier_rmse))


def controls():
    fixture = __import__('runpy').run_path(str(ROOT / 'tests/fixtures/h1_physical.py'))['physical_column']
    checks = []
    for centre in [-.25, 0., .25]:
        xyz, _, _ = fixture(rails=True, rail_center=centre)
        result = near_rails(xyz)
        assert result['accepted'], result
        measured = [p['centre'] for p in result['chosen']]
        assert max(abs(c - centre) for c in measured) < .06
        checks.append(dict(rail_centre=centre, measured=measured))
    for name, args in [('flat', dict(rails=False)), ('wrong_spacing', dict(rails=True, rail_spacing=2.1))]:
        xyz, _, _ = fixture(**args)
        result = near_rails(xyz)
        assert not result['accepted'], (name, result)
        checks.append(dict(control=name, accepted=False))
    xyz, _ = raw_cloud(CACHES['A'], 180)
    previous = pcd(xyz)
    identity = register(previous, previous, np.eye(4))
    assert np.max(np.abs(np.asarray(identity['T']) - np.eye(4))) < 1e-6
    yaw = np.radians(.2)
    truth = np.eye(4)
    truth[:3, :3] = [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
    truth[:3, 3] = [1.2, .1, .02]
    # Transform the already selected cloud, preserving the same physical points.
    current = o3d.geometry.PointCloud(previous)
    current.transform(np.linalg.inv(truth))
    seed = np.eye(4)
    seed[:3, 3] = [1.0, .05, 0.]
    got = register(current, previous, seed)
    delta = np.linalg.inv(truth) @ np.asarray(got['T'])
    assert np.linalg.norm(delta[:3, 3]) < .02
    assert abs(np.degrees(np.arctan2(delta[1, 0], delta[0, 0]))) < .01
    return dict(rails=checks, identity=identity,
                manufactured_transform=dict(truth=truth.tolist(), seed=seed.tolist(), result=got))


def sequence(name, end):
    cache = CACHES[name]
    metadata = json.loads((cache / 'meta.json').read_text())
    records, poses, alternate_poses = [], [np.eye(4)], [np.eye(4)]
    previous = alternate_previous = None
    guess = alternate_guess = np.eye(4)
    for i in range(end):
        xyz, digest = raw_cloud(cache, i)
        current, alternate_current = pcd(xyz), pcd(xyz, True)
        row = dict(i=i, stamp=metadata[i]['stamp'], input_sha256=digest, rails=near_rails(xyz))
        if previous is not None:
            primary = register(current, previous, guess)
            alternate = register(alternate_current, alternate_previous, alternate_guess, True)
            guess, alternate_guess = np.asarray(primary['T']), np.asarray(alternate['T'])
            poses.append(poses[-1] @ guess)
            alternate_poses.append(alternate_poses[-1] @ alternate_guess)
            row.update(primary=primary, alternate=alternate,
                       speed_mps=float(np.linalg.norm(guess[:3, 3]) / (metadata[i]['stamp'] - metadata[i - 1]['stamp'])))
        row.update(pose=poses[-1].tolist(), alternate_pose=alternate_poses[-1].tolist())
        records.append(row)
        previous, alternate_previous = current, alternate_current
        if i % 25 == 0:
            print(name, i, 'rails', row['rails']['accepted'], 'travel', round(float(poses[-1][0, 3]), 2), flush=True)
    return dict(name=name, cache=str(cache), rows=records)


def main():
    global INITIAL_METHOD
    parser = argparse.ArgumentParser()
    parser.add_argument('--sequence', choices=list(CACHES))
    parser.add_argument('--end', type=int)
    parser.add_argument('--controls', action='store_true')
    parser.add_argument('--initial-method', action='store_true', help='reconstruct the initial rejected registration configuration')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    INITIAL_METHOD = args.initial_method
    started = time.time()
    result = controls() if args.controls else sequence(args.sequence, args.end or (340 if args.sequence == 'A' else 268))
    result['wall_s'] = time.time() - started
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    print('COMPLETE', args.out, result['wall_s'], flush=True)


if __name__ == '__main__':
    main()
