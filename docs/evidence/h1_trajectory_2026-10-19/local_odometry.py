"""Test generalized ICP short-step motion without detector model input."""
import argparse
import json
from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation

import direct_gicp as experiment


def cloud(points, voxel):
    p = points[(points[:, 0] > 3) & (points[:, 0] < 80) & (np.abs(points[:, 1]) < 6)]
    return o3d.geometry.PointCloud(o3d.utility.Vector3dVector(p)).voxel_down_sample(voxel)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sequence', choices=['A', 'C'], required=True)
    p.add_argument('--end', type=int, default=100)
    p.add_argument('--voxel', type=float, default=.2)
    p.add_argument('--initial-dx', type=float, default=0.)
    p.add_argument('--deskew-from', type=Path)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    assert not args.out.exists()
    rows = []
    pose, guess = np.eye(4), np.eye(4)
    guess[0, 3] = args.initial_dx
    previous = None
    motion_rows = json.loads(args.deskew_from.read_text())['rows'] if args.deskew_from else None
    stamps = json.loads((experiment.raw.WORK / f'sequence-{args.sequence}-v2.json').read_text())['rows']
    for i in range(args.end):
        xyz, sha = experiment.observed(args.sequence, i, False)
        if motion_rows:
            j = min(i + 1, len(motion_rows) - 1)
            with np.load(experiment.raw.WORK / f'timing-{args.sequence}' / f'f_{i:05d}.npz') as timing:
                fraction = timing['dt'] / (stamps[j]['stamp'] - stamps[j-1]['stamp'])
            xyz = experiment.deskew.compensate(xyz, fraction, np.asarray(motion_rows[j]['T']))
        current = cloud(xyz, args.voxel)
        row = dict(i=i, sha256=sha)
        if previous is not None:
            fit = o3d.pipelines.registration.registration_generalized_icp(current, previous, .7, guess,
                o3d.pipelines.registration.TransformationEstimationForGeneralizedICP(epsilon=.001),
                o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-8, relative_rmse=1e-8, max_iteration=80))
            guess = fit.transformation
            pose = pose @ guess
            row.update(T=guess.tolist(), fitness=float(fit.fitness), rmse=float(fit.inlier_rmse))
        row.update(pose=pose.tolist())
        rows.append(row)
        previous = current
        if i % 10 == 0:
            print(args.sequence, i, 'translation', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist(), flush=True)
    with args.out.open('x') as stream:
        json.dump(dict(sequence=args.sequence, voxel=args.voxel, initial_dx=args.initial_dx,
                       deskew_from=str(args.deskew_from), rows=rows), stream, indent=2)


if __name__ == '__main__':
    main()
