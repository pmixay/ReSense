#!/usr/bin/env python3
"""Robustness probes (8.4) on cached node-decoded clouds through the node-faithful replica.
Transforms (applied to every frame, sensor frame, before the axis mapping):
  --pitch/--roll/--yaw DEG : rigid rotation of the cloud in the vehicle frame (a re-mounted / tilted LiDAR)
  --drop P                 : random point dropout with probability P (per point, seeded)
  --dedup                  : keep one point of each identical dual-return pair (a single-return driver)
  --every N                : process every N-th frame only (10 Hz -> 10/N Hz input)
  --noise S                : Gaussian noise of S m along each axis
  --frame-id ID            : replace the frame_id (the node takes any)
Writes <out>.jsonl in the same record format as judge_runner.py (index = original frame index).
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_runner import NodeReplica, record  # noqa: E402
from range_test import run_frame  # noqa: E402


def rot(roll, pitch, yaw):
    r, p, y = np.radians([roll, pitch, yaw])
    Rx = np.array([[1, 0, 0], [0, np.cos(r), -np.sin(r)], [0, np.sin(r), np.cos(r)]])
    Ry = np.array([[np.cos(p), 0, np.sin(p)], [0, 1, 0], [-np.sin(p), 0, np.cos(p)]])
    Rz = np.array([[np.cos(y), -np.sin(y), 0], [np.sin(y), np.cos(y), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("out")
    ap.add_argument("--pitch", type=float, default=0.0)
    ap.add_argument("--roll", type=float, default=0.0)
    ap.add_argument("--yaw", type=float, default=0.0)
    ap.add_argument("--drop", type=float, default=0.0)
    ap.add_argument("--dedup", action="store_true")
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--noise", type=float, default=0.0)
    ap.add_argument("--frame-id", default="")
    ap.add_argument("--end", type=int, default=10 ** 9)
    a = ap.parse_args()
    meta = json.load(open(os.path.join(a.cache, "meta.json")))
    files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
    rep = NodeReplica()
    Rvs = rep.R_vs.astype(np.float64)
    Rt = rot(a.roll, a.pitch, a.yaw)
    rng = np.random.default_rng(7)
    with open(a.out + ".jsonl", "w") as fj:
        for k, (m, f) in enumerate(zip(meta, files)):
            if k >= a.end:
                break
            if k % a.every:
                continue
            d = np.load(f)
            xyz, inten, ring = d["xyz"], d["inten"], d["ring"]
            if a.dedup:
                _, first = np.unique(xyz, axis=0, return_index=True)
                keep = np.sort(first)
                xyz, inten, ring = xyz[keep], inten[keep], ring[keep]
            if a.drop > 0:
                keep = rng.random(len(xyz)) >= a.drop
                xyz, inten, ring = xyz[keep], inten[keep], ring[keep]
            if a.pitch or a.roll or a.yaw:
                v = xyz.astype(np.float64) @ Rvs.T
                v = v @ Rt.T
                xyz = (v @ Rvs).astype(np.float32)
            if a.noise > 0:
                xyz = (xyz + rng.normal(0, a.noise, xyz.shape)).astype(np.float32)
            if a.frame_id:
                m = dict(m, frame_id=a.frame_id)
            res = run_frame(rep, xyz, inten, ring, m, k)
            fj.write(json.dumps(record(k, m["bag_t"], m["stamp"], res, 0.0, 0.0, m["frame_id"], m["topic"])) + "\n")
    print(a.out, "done; resets", rep.resets[:5])


if __name__ == "__main__":
    main()
