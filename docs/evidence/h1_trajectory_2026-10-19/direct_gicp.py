"""Detector-free overlap-symmetric registration experiments on fixed H1 pairs."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / 'docs/evidence/h1_reference_2026-10-19'
spec = importlib.util.spec_from_file_location('h1_raw_reference', OLD / 'reference.py')
raw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(raw)
spec2 = importlib.util.spec_from_file_location('h1_deskew_reference', OLD / 'deskew_reference.py')
sys.path.insert(0, str(OLD))
deskew = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(deskew)
RAW_COVARIANCE = False


def observed(name, index, corrected):
    xyz, digest = raw.raw_cloud(raw.CACHES[name], index)
    if corrected:
        rows = json.loads((raw.WORK / f'sequence-{name}-v2.json').read_text())['rows']
        j = min(index + 1, len(rows) - 1)
        with np.load(raw.WORK / f'timing-{name}' / f'f_{index:05d}.npz') as data:
            xyz = deskew.compensate(xyz, data['dt'] / (rows[j]['stamp'] - rows[j-1]['stamp']), np.asarray(rows[j]['primary']['T']))
    return xyz, digest


def cloud(points, voxel):
    p = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    p = p.voxel_down_sample(voxel)
    # Let generalized ICP construct its epsilon-regularized plane covariances.
    # Raw sample covariances are singular on exact planar positive controls.
    if RAW_COVARIANCE:
        p.estimate_covariances(o3d.geometry.KDTreeSearchParamHybrid(radius=max(1.0, voxel * 4), max_nn=30))
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=max(1.0, voxel * 4), max_nn=30))
    return p


def overlap(source, target, seed):
    # Both directions use the same fixed common physical bounding region. The
    # earlier scan is sparse and must not be compared to unseen near geometry.
    mapped = target @ seed[:3, :3] + (-seed[:3, 3] @ seed[:3, :3])
    source_keep = (source[:, 0] > 8) & (source[:, 0] < 75) & (np.abs(source[:, 1]) < 7)
    target_keep = (mapped[:, 0] > 8) & (mapped[:, 0] < 75) & (np.abs(mapped[:, 1]) < 7)
    mapped_source = source @ seed[:3, :3].T + seed[:3, 3]
    source_keep &= (mapped_source[:, 0] > 6) & (mapped_source[:, 0] < 180) & (np.abs(mapped_source[:, 1]) < 10)
    target_keep &= (target[:, 0] > 6) & (target[:, 0] < 180) & (np.abs(target[:, 1]) < 10)
    return source[source_keep], target[target_keep]


def align(source, target, seed, method):
    transform = seed.copy()
    stages = []
    for voxel, radius, iterations in [(.5, 2., 80), (.3, 1., 80), (.15, .6, 80)]:
        src, dst = cloud(source, voxel), cloud(target, voxel)
        criteria = o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-8, relative_rmse=1e-8, max_iteration=iterations)
        if method == 'gicp':
            fit = o3d.pipelines.registration.registration_generalized_icp(src, dst, radius, transform,
                o3d.pipelines.registration.TransformationEstimationForGeneralizedICP(epsilon=.001), criteria)
        else:
            fit = o3d.pipelines.registration.registration_icp(src, dst, radius, transform,
                o3d.pipelines.registration.TransformationEstimationPointToPlane(o3d.pipelines.registration.TukeyLoss(k=.25)), criteria)
        transform = fit.transformation
        stages.append(dict(voxel=voxel, fitness=float(fit.fitness), rmse=float(fit.inlier_rmse)))
    return dict(T=transform.tolist(), stages=stages)


def metrics(first, second, reverse, point):
    a, b, r = [np.asarray(item['T']) for item in (first, second, reverse)]
    cycle = a @ r
    spread = float(np.linalg.norm((a @ point)[:3] - (b @ point)[:3]))
    translation = float(np.linalg.norm(cycle[:3, 3]))
    rotation = float(np.linalg.norm(Rotation.from_matrix(cycle[:3, :3]).as_rotvec()) * 180 / np.pi)
    fitness = min(item['stages'][-1]['fitness'] for item in (first, second, reverse))
    valid = spread <= .1 and translation <= .1 and rotation <= .05 and fitness >= .7
    return dict(projected_disagreement_m=spread, reverse_translation_m=translation,
                reverse_rotation_deg=rotation, min_fitness=fitness, consistent=valid)


def main():
    global RAW_COVARIANCE
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--count', type=int, default=36)
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--deskew', action='store_true')
    p.add_argument('--method', choices=['gicp', 'robust-plane'], default='gicp')
    p.add_argument('--new-seeds', action='store_true')
    p.add_argument('--sample-covariances', action='store_true', help='reproduce the rejected pre-control configuration')
    args = p.parse_args()
    assert not args.out.exists(), args.out
    RAW_COVARIANCE = args.sample_covariances
    started = time.monotonic()
    old = json.loads((OLD / ('direct-reference-deskew.json' if args.deskew else 'direct-reference.json')).read_text())
    if args.new_seeds:
        work = Path('/tmp/opencode/h1-trajectory')
        selected = []
        for name, starts in [('A', [50, 100, 150, 180, 220, 260]), ('C', [0, 25, 50, 75, 100, 125])]:
            geo = json.loads((work / f'local-gicp-{name}-seeded.json').read_text())['rows']
            color = json.loads((work / f'colored-{name}-sequence.json').read_text())['rows']
            rails = json.loads((raw.WORK / f'sequence-{name}-v2.json').read_text())['rows']
            poses, alts = np.array([r['pose'] for r in geo]), np.array([r['pose'] for r in color])
            for i in starts:
                for wanted in [60., 100., 140.]:
                    choices = []
                    for row in rails[i+1:]:
                        j = row['i']
                        for pair in row['rails'].get('chosen', []):
                            point = np.array([np.mean([h[k] for h in pair['heads']]) for k in ['x', 'y', 'z']] + [1.])
                            seed = np.linalg.inv(poses[i]) @ poses[j]
                            q = seed @ point
                            if abs(q[0] - wanted) < 8:
                                choices.append((abs(q[0] - wanted), j, point, seed))
                    if not choices:
                        raise RuntimeError((name, i, wanted, 'no future raw rail observation'))
                    _, j, point, seed = min(choices, key=lambda item: item[0])
                    selected.append(dict(sequence=name, frame=i, future_frame=j, station=wanted,
                        near_point=point.tolist(), primary_seed=seed.tolist(),
                        alternate_seed=(np.linalg.inv(alts[i]) @ alts[j]).tolist()))
        old = dict(rows=selected)
    results = []
    for row in old['rows'][args.offset:args.offset + args.count]:
        name, i, j = row['sequence'], row['frame'], row['future_frame']
        source, shash = observed(name, j, args.deskew)
        target, thash = observed(name, i, args.deskew)
        seed, alternate = np.asarray(row['primary_seed']), np.asarray(row['alternate_seed'])
        src, dst = overlap(source, target, seed)
        first = align(src, dst, seed, args.method)
        second = align(src, dst, alternate, args.method)
        reverse = align(dst, src, np.linalg.inv(np.asarray(first['T'])), args.method)
        point = np.asarray(row['near_point'])
        result = dict(sequence=name, frame=i, future_frame=j, station=row['station'], source_hash=shash,
                      target_hash=thash, input_points=[len(src), len(dst)], primary_seed=seed.tolist(),
                      alternate_seed=alternate.tolist(), primary=first, alternate=second, reverse=reverse,
                      near_point=point.tolist(), projected_point=(np.asarray(first['T']) @ point).tolist(),
                      **metrics(first, second, reverse, point))
        results.append(result)
        print(name, i, j, row['station'], {key: result[key] for key in ['consistent', 'projected_disagreement_m', 'reverse_translation_m', 'reverse_rotation_deg', 'min_fitness']}, flush=True)
        with args.out.open('w') as stream:
            json.dump(dict(method=args.method, deskew=args.deskew, sample_covariances=RAW_COVARIANCE,
                           rows=results, wall_s=time.monotonic()-started), stream, indent=2)
    print('TOTAL', sum(row['consistent'] for row in results), '/', len(results), flush=True)


if __name__ == '__main__':
    main()
