"""Intensity-textured registration breaks circular-tunnel roll/axial ambiguity."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

import direct_gicp as base


DESKEW_ROWS = None
STAMP_ROWS = None


def raw(name, index):
    points, sha = base.observed(name, index, False)
    if DESKEW_ROWS:
        j = min(index + 1, len(DESKEW_ROWS) - 1)
        with np.load(base.raw.WORK / f'timing-{name}' / f'f_{index:05d}.npz') as timing:
            fraction = timing['dt'] / (STAMP_ROWS[j]['stamp'] - STAMP_ROWS[j-1]['stamp'])
        points = base.deskew.compensate(points, fraction, np.asarray(DESKEW_ROWS[j]['T']))
    with np.load(base.raw.CACHES[name] / f'f_{index:05d}.npz') as data:
        intensity = data['inten'].astype(float)
    use = (points[:, 0] > 4) & (points[:, 0] < 70) & (np.abs(points[:, 1]) < 6)
    return points[use], intensity[use], sha


def cloud(points, intensity, voxel):
    p = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points))
    colors = np.log1p(np.clip(intensity, 0, 255)) / np.log(256)
    p.colors = o3d.utility.Vector3dVector(np.repeat(colors[:, None], 3, axis=1))
    p = p.voxel_down_sample(voxel)
    p.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel * 3, max_nn=30))
    return p


def align(source, target, seed, weight=.8):
    transform = seed.copy()
    stages = []
    for voxel, radius in [(.3, .7), (.15, .4), (.08, .2)]:
        a, b = cloud(*source[:2], voxel), cloud(*target[:2], voxel)
        result = o3d.pipelines.registration.registration_colored_icp(a, b, radius, transform,
            o3d.pipelines.registration.TransformationEstimationForColoredICP(lambda_geometric=weight),
            o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-8, relative_rmse=1e-8, max_iteration=60))
        transform = result.transformation
        stages.append(dict(voxel=voxel, fitness=float(result.fitness), rmse=float(result.inlier_rmse)))
    # Fresh raw validation samples, not the averaged optimizer color voxels.
    xyz = source[0][::7] @ transform[:3, :3].T + transform[:3, 3]
    distance, indices = cKDTree(target[0]).query(xyz)
    color_error = np.abs(np.log1p(source[1][::7]) - np.log1p(target[1][indices])) / np.log(256)
    close = distance < .15
    return dict(T=transform.tolist(), stages=stages, validation_close_fraction=float(close.mean()),
                validation_color_median=float(np.median(color_error[close])),
                validation_distance_median=float(np.median(distance)),
                validation_joint_cost=float(np.mean(np.minimum(distance, .3) ** 2 + .2 * np.minimum(color_error, .3) ** 2)))


def main():
    global DESKEW_ROWS, STAMP_ROWS
    p = argparse.ArgumentParser()
    p.add_argument('--sequence', choices=['A', 'C'], default='A')
    p.add_argument('--frame', type=int, default=1)
    p.add_argument('--end', type=int, default=0)
    p.add_argument('--initial-dx', type=float, default=1.34)
    p.add_argument('--deskew-from', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.deskew_from:
        DESKEW_ROWS = json.loads(args.deskew_from.read_text())['rows']
        STAMP_ROWS = json.loads((base.raw.WORK / f'sequence-{args.sequence}-v2.json').read_text())['rows']
    if args.end:
        previous = raw(args.sequence, 0)
        pose = np.eye(4)
        guess = np.eye(4)
        guess[0, 3] = args.initial_dx
        rows = [dict(i=0, sha256=previous[2], pose=pose.tolist())]
        for i in range(1, args.end):
            current = raw(args.sequence, i)
            result = align(current, previous, guess)
            guess = np.asarray(result['T'])
            pose = pose @ guess
            rows.append(dict(i=i, sha256=current[2], pose=pose.tolist(), **result))
            previous = current
            if i % 20 == 0:
                print(args.sequence, i, 'translation', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist(), flush=True)
        with args.out.open('x') as stream:
            json.dump(dict(sequence=args.sequence, method='colored', initial_dx=args.initial_dx,
                           deskew_from=str(args.deskew_from), rows=rows), stream, indent=2)
        return
    source, target = raw(args.sequence, args.frame), raw(args.sequence, args.frame - 1)
    rows = []
    for dx in [0., .6, 1.2, 1.8, 2.4]:
        seed = np.eye(4)
        seed[0, 3] = dx
        result = align(source, target, seed)
        transform = np.array(result['T'])
        print('SEED', dx, 't', transform[:3, 3].round(4).tolist(), 'rxyz', Rotation.from_matrix(transform[:3, :3]).as_euler('xyz', degrees=True).round(4).tolist(), {key: value for key, value in result.items() if key not in ['T', 'stages']}, flush=True)
        rows.append(dict(dx=dx, result=result))
    with args.out.open('x') as stream:
        json.dump(dict(sequence=args.sequence, frame=args.frame, rows=rows), stream, indent=2)


if __name__ == '__main__':
    main()
