"""Independent short-step pose from reflective, localized raw scene texture."""
import argparse
import json
from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation

import direct_gicp as base


def observe(name, i, threshold):
    points, sha = base.observed(name, i, False)
    with np.load(base.raw.CACHES[name] / f'f_{i:05d}.npz') as data:
        intensity = data['inten']
    use = (points[:, 0] > 4) & (points[:, 0] < 100) & (np.abs(points[:, 1]) < 7) & (intensity >= threshold)
    return np.unique(points[use], axis=0), sha


def fit(source, target, seed):
    a = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(source))
    b = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(target))
    transform = seed.copy()
    stages = []
    for voxel, radius in [(.1, .5), (.05, .25), (.02, .15)]:
        reg = o3d.pipelines.registration.registration_icp(a.voxel_down_sample(voxel), b.voxel_down_sample(voxel), radius, transform,
            o3d.pipelines.registration.TransformationEstimationPointToPoint(),
            o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-9, relative_rmse=1e-9, max_iteration=100))
        transform = reg.transformation
        stages.append(dict(voxel=voxel, fitness=float(reg.fitness), rmse=float(reg.inlier_rmse)))
    return dict(T=transform.tolist(), stages=stages)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sequence', choices=['A', 'C'], required=True)
    p.add_argument('--end', type=int, required=True)
    p.add_argument('--threshold', type=float, default=30.)
    p.add_argument('--initial-dx', type=float, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    assert not args.out.exists()
    pose, guess = np.eye(4), np.eye(4)
    guess[0, 3] = args.initial_dx
    previous, sha = observe(args.sequence, 0, args.threshold)
    rows = [dict(i=0, points=len(previous), sha256=sha, pose=pose.tolist())]
    for i in range(1, args.end):
        current, sha = observe(args.sequence, i, args.threshold)
        if len(current) < 20 or len(previous) < 20:
            raise RuntimeError((i, 'insufficient texture', len(current), len(previous)))
        result = fit(current, previous, guess)
        guess = np.asarray(result['T'])
        pose = pose @ guess
        reverse = fit(previous, current, np.linalg.inv(guess))
        delta = guess @ np.asarray(reverse['T'])
        rows.append(dict(i=i, points=len(current), sha256=sha, pose=pose.tolist(), reverse=reverse,
            closure_translation=float(np.linalg.norm(delta[:3, 3])),
            closure_rotation_deg=float(np.linalg.norm(Rotation.from_matrix(delta[:3, :3]).as_rotvec())*180/np.pi), **result))
        previous = current
        if i % 20 == 0:
            print(args.sequence, i, 't', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist(), 'closure', rows[-1]['closure_translation'], rows[-1]['closure_rotation_deg'], flush=True)
    with args.out.open('x') as stream:
        json.dump(dict(sequence=args.sequence, method='reflective point-to-point', threshold=args.threshold, rows=rows), stream, indent=2)


if __name__ == '__main__':
    main()
