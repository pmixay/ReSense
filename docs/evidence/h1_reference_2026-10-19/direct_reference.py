"""Direct long-baseline cross-view alignment, independent of chained drift."""
import json
import argparse

import numpy as np
import open3d as o3d

from reference import CACHES, HERE, WORK, raw_cloud


def cloud(xyz):
    select = (xyz[:, 0] > 3) & (xyz[:, 0] < 190) & (np.abs(xyz[:, 1]) < 10)
    p = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz[select]))
    p = p.voxel_down_sample(.25)
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=2., max_nn=40))
    return p


def align(source, target, seed):
    # Restrict to the common physical region, using geometry only. This keeps
    # non-overlap from being mistaken for a low-fitness registration failure.
    sp = np.asarray(source.points)
    mapped = sp @ seed[:3, :3].T + seed[:3, 3]
    used = np.flatnonzero((mapped[:, 0] > 6) & (mapped[:, 0] < 180) & (np.abs(mapped[:, 1]) < 9))
    selected = source.select_by_index(used)
    result = o3d.pipelines.registration.registration_icp(selected, target, .8, seed,
        o3d.pipelines.registration.TransformationEstimationPointToPlane(),
        o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=60))
    return dict(T=result.transformation.tolist(), fitness=float(result.fitness), rmse=float(result.inlier_rmse), points=len(used))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--deskew', action='store_true')
    args = parser.parse_args()
    from deskew_reference import compensate

    def observed_cloud(name, index, original):
        if not args.deskew:
            return cloud(original)
        old = json.loads((WORK / f'sequence-{name}-v2.json').read_text())['rows']
        j = min(index + 1, len(old) - 1)
        period = old[j]['stamp'] - old[j - 1]['stamp']
        with np.load(WORK / f'timing-{name}' / f'f_{index:05d}.npz') as data:
            dt = data['dt']
        return cloud(compensate(original, dt / period, np.asarray(old[j]['primary']['T'])))
    xyz, _ = raw_cloud(CACHES['A'], 180)
    known_target = cloud(xyz)
    truth = np.eye(4)
    angle = np.radians(1.)
    truth[:3, :3] = [[np.cos(angle), -np.sin(angle), 0], [np.sin(angle), np.cos(angle), 0], [0, 0, 1]]
    truth[:3, 3] = [80., .2, .05]
    known_source = o3d.geometry.PointCloud(known_target)
    known_source.transform(np.linalg.inv(truth))
    current = np.asarray(known_source.points)
    known_source = known_source.select_by_index(np.flatnonzero((current[:, 0] > 3) & (np.abs(current[:, 1]) < 10)))
    seed = truth.copy()
    seed[0, 3] += .2
    control = align(known_source, known_target, seed)
    error = np.linalg.inv(truth) @ np.asarray(control['T'])
    assert np.linalg.norm(error[:3, 3]) < .02 and control['fitness'] > .7
    controls = dict(known_long_baseline=dict(truth=truth.tolist(), seed=seed.tolist(), result=control))
    report = []
    for name, starts in [('A', [50, 100, 150, 180, 220, 260]), ('C', [0, 25, 50, 75, 100, 125])]:
        rows = json.loads((WORK / f'sequence-{name}-{"deskew" if args.deskew else "v2"}.json').read_text())['rows']
        poses, alt = (np.asarray([r[field] for r in rows]) for field in ['pose', 'alternate_pose'])
        for i in starts:
            earlier, old_hash = raw_cloud(CACHES[name], i)
            target = observed_cloud(name, i, earlier)
            for wanted in [60., 100., 140.]:
                possible = []
                for row in rows[i + 1:]:
                    for pair in row['rails'].get('chosen', []):
                        point = np.array([np.mean([h[k] for h in pair['heads']]) for k in ['x', 'y', 'z']] + [1.])
                        seed = np.linalg.inv(poses[i]) @ poses[row['i']]
                        q = seed @ point
                        if abs(q[0] - wanted) <= 8:
                            possible.append((abs(q[0] - wanted), row['i'], point))
                if not possible:
                    report.append(dict(sequence=name, frame=i, station=wanted, reason='no_near_rail_observation'))
                    continue
                _, j, point = min(possible, key=lambda p: p[0])
                later, new_hash = raw_cloud(CACHES[name], j)
                source = observed_cloud(name, j, later)
                seed = np.linalg.inv(poses[i]) @ poses[j]
                second_seed = np.linalg.inv(alt[i]) @ alt[j]
                first, second = align(source, target, seed), align(source, target, second_seed)
                t1, t2 = np.asarray(first['T']), np.asarray(second['T'])
                q1, q2 = t1 @ point, t2 @ point
                reverse = align(target, source, np.linalg.inv(t1))
                cycle = t1 @ np.asarray(reverse['T'])
                translation = float(np.linalg.norm(cycle[:3, 3]))
                rotation = float(np.degrees(np.arccos(np.clip((np.trace(cycle[:3, :3]) - 1) / 2, -1, 1))))
                spread = float(np.linalg.norm(q1[:3] - q2[:3]))
                valid = spread <= .1 and translation <= .1 and rotation <= .05 and min(first['fitness'], second['fitness'], reverse['fitness']) >= .7
                record = dict(sequence=name, frame=i, station=wanted, future_frame=j, near_point=point.tolist(),
                    source_sha256=[old_hash, new_hash], primary=first, alternate_seed_result=second, reverse=reverse,
                    projected_point=q1[:3].tolist(), projected_disagreement_m=spread,
                    reverse_translation_m=translation, reverse_rotation_deg=rotation, consistent=valid,
                    primary_seed=seed.tolist(), alternate_seed=second_seed.tolist())
                report.append(record)
                print(name, i, wanted, 'later', j, 'consistent', valid, 'agreement', spread,
                      'closure', translation, rotation, 'fitness', first['fitness'], second['fitness'], reverse['fitness'], flush=True)
    with (HERE / ('direct-reference-deskew.json' if args.deskew else 'direct-reference.json')).open('x') as stream:
        json.dump(dict(controls=controls, rows=report), stream, indent=2)


if __name__ == '__main__':
    main()
