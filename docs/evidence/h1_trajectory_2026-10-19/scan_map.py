"""Rolling scan-to-map reconstruction, independently of detector axes."""
import argparse
from collections import deque
import json
from pathlib import Path

import numpy as np
import open3d as o3d
from scipy.spatial.transform import Rotation

import direct_gicp as base


def down(points, voxel):
    return o3d.geometry.PointCloud(o3d.utility.Vector3dVector(points)).voxel_down_sample(voxel)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--sequence', choices=['A', 'C'], required=True)
    p.add_argument('--end', type=int, required=True)
    p.add_argument('--initial-dx', type=float, required=True)
    p.add_argument('--method', choices=['gicp', 'point'], default='gicp')
    p.add_argument('--backward', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    assert not args.out.exists()
    order = list(range(args.end))
    if args.backward:
        order.reverse()
    pose, guess = np.eye(4), np.eye(4)
    guess[0, 3] = args.initial_dx * (-1 if args.backward else 1)
    history = deque(maxlen=12)
    rows = []
    for frame in order:
        xyz, sha = base.observed(args.sequence, frame, False)
        use = (xyz[:, 0] > 4) & (xyz[:, 0] < 80) & (np.abs(xyz[:, 1]) < 7)
        current = down(xyz[use], .15)
        if history:
            previous_pose = pose.copy()
            inv = np.linalg.inv(pose)
            # Build map in the preceding frame, avoiding loss of conditioning
            # as absolute coordinates grow into hundreds of metres.
            mapped = []
            for past_points, past_pose in history:
                t = inv @ past_pose
                points = past_points @ t[:3, :3].T + t[:3, 3]
                keep = (points[:, 0] > -2) & (points[:, 0] < 90) & (np.abs(points[:, 1]) < 9)
                mapped.append(points[keep])
            target = down(np.vstack(mapped), .15)
            if args.method == 'gicp':
                reg = o3d.pipelines.registration.registration_generalized_icp(current, target, .5, guess,
                    o3d.pipelines.registration.TransformationEstimationForGeneralizedICP(epsilon=.001),
                    o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-8, relative_rmse=1e-8, max_iteration=80))
            else:
                reg = o3d.pipelines.registration.registration_icp(current, target, .3, guess,
                    o3d.pipelines.registration.TransformationEstimationPointToPoint(),
                    o3d.pipelines.registration.ICPConvergenceCriteria(relative_fitness=1e-8, relative_rmse=1e-8, max_iteration=80))
            guess = reg.transformation
            pose = previous_pose @ guess
            result = dict(T=guess.tolist(), fitness=float(reg.fitness), rmse=float(reg.inlier_rmse))
        else:
            result = {}
        rows.append(dict(i=frame, sha256=sha, pose=pose.tolist(), **result))
        history.append((np.asarray(current.points).copy(), pose.copy()))
        if frame % 20 == 0:
            print(args.sequence, args.method, 'backward', args.backward, frame, 't', pose[:3, 3].round(3).tolist(), 'rxyz', Rotation.from_matrix(pose[:3, :3]).as_euler('xyz', degrees=True).round(3).tolist(), flush=True)
    if args.backward:
        rows.reverse()
        frame0 = np.linalg.inv(np.asarray(rows[0]['pose']))
        for row in rows:
            row['pose'] = (frame0 @ np.asarray(row['pose'])).tolist()
    with args.out.open('x') as stream:
        json.dump(dict(sequence=args.sequence, method=args.method, backward=args.backward, rows=rows), stream, indent=2)


if __name__ == '__main__':
    main()
