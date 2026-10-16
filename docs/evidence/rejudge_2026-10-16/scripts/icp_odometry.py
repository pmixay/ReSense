#!/usr/bin/env python3
"""Frame-to-frame forward travel of the train from the cached clouds (open3d point-to-plane ICP on 0.15 m
voxels of the 3-80 m part of the cloud, vehicle frame), independent of the detector.
  icp_odometry.py <cache_dir> <out.json> [--start N --end M]
out: {"i": [...], "dx": [...], "fitness": [...]}  dx = forward travel from frame i-1 to i (m)
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import open3d as o3d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_runner import NodeReplica  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("cache")
p.add_argument("out")
p.add_argument("--start", type=int, default=0)
p.add_argument("--end", type=int, default=10 ** 9)
a = p.parse_args()
R = NodeReplica().R_vs
files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
files = [f for f in files if a.start <= int(os.path.basename(f)[2:7]) < a.end]


def pcd_of(f):
    xyz = np.load(f)["xyz"].astype(np.float64) @ R.T
    m = (xyz[:, 0] > 3) & (xyz[:, 0] < 80) & (np.abs(xyz[:, 1]) < 6)
    pc = o3d.geometry.PointCloud(o3d.utility.Vector3dVector(xyz[m]))
    pc = pc.voxel_down_sample(0.15)
    pc.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=0.6, max_nn=20))
    return pc


out = {"i": [], "dx": [], "dy": [], "fitness": [], "rmse": []}
prev, guess = None, np.eye(4)
for f in files:
    i = int(os.path.basename(f)[2:7])
    cur = pcd_of(f)
    if len(cur.points) < 2000:          # view blocked (e.g. a synthetic box right in front of the sensor)
        out["i"].append(i)
        out["dx"].append(out["dx"][-1] if out["dx"] else 0.0)
        out["dy"].append(0.0)
        out["fitness"].append(0.0)
        out["rmse"].append(0.0)
        continue
    if prev is not None:
        # cur (frame i) registered onto prev (frame i-1): a static point at X_prev is at X_cur = X_prev - dx
        reg = o3d.pipelines.registration.registration_icp(
            cur, prev, 0.5, guess, o3d.pipelines.registration.TransformationEstimationPointToPlane(),
            o3d.pipelines.registration.ICPConvergenceCriteria(max_iteration=40))
        T = reg.transformation
        guess = T.copy()
        out["i"].append(i)
        out["dx"].append(float(T[0, 3]))
        out["dy"].append(float(T[1, 3]))
        out["fitness"].append(float(reg.fitness))
        out["rmse"].append(float(reg.inlier_rmse))
    prev = cur
json.dump(out, open(a.out, "w"))
print(a.cache, len(out["i"]), "pairs; travel", round(sum(out["dx"]), 1), "m")
