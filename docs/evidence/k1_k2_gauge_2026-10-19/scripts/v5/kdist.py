#!/usr/bin/env python3
"""Share of frames with |base curvature| >= thresholds, per group, from a gate work dir.  kdist.py <gatework>"""
import glob, json, os, sys
import numpy as np
SETF = {"46", "68", "98", "140", "168", "172"}
wd = sys.argv[1]
def load(pat):
    out = []
    for f in sorted(glob.glob(os.path.join(wd, pat))):
        out += [json.loads(l) for l in open(f)]
    return out
ride = load("new_data_*.jsonl")
groups = {"ride_setF_files": [r for r in ride if r["frame_id"].split("_")[2] in SETF], "ride_all": ride}
for b in ("roundT_squareT_pressureGate_squareT", "roundT_doubleT", "roundT_pressureGate_roundT", "doubleT_platform",
          "squareT_platform_squareT_switch", "doubleT_obstacle", "cloud_with_fake_obj"):
    groups[b] = load(b + ".jsonl")
for g, rows in groups.items():
    k = np.abs(np.array([r["track"]["curvature"] for r in rows]))
    print(f"{g:38s} n {len(rows):6d}  |k|>=0.7e-4 {np.mean(k>=0.7e-4):.3f}  >=1e-4 {np.mean(k>=1e-4):.3f}  >=2e-4 {np.mean(k>=2e-4):.3f}  >=5e-4 {np.mean(k>=5e-4):.3f}  p50 {np.median(k)*1e4:.2f}e-4")
