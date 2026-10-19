#!/usr/bin/env python3
"""Trusted range (track.axis_valid capped at 250) and monitored range per recording; share of frames with the joint shape.
range_stats.py <work> [<work> ...]"""
import glob, json, os, sys
import numpy as np
NAMES = ["new_data", "roundT_doubleT", "roundT_pressureGate_roundT", "roundT_squareT_pressureGate_squareT",
         "squareT_platform_squareT_switch", "doubleT_platform", "doubleT_obstacle", "cloud_with_fake_obj"]
for wd in sys.argv[1:]:
    print("==", wd)
    for n in NAMES:
        files = sorted(glob.glob(os.path.join(wd, n + "*.jsonl")), key=lambda p: int(p.rsplit("_", 1)[1].split(".")[0]) if n == "new_data" else 0)
        rows = [json.loads(l) for f in files for l in open(f)]
        av = np.array([min(r["track"]["axis_valid"], 250.0) for r in rows])
        mon = np.array([r["health"].get("monitored_range") or 0.0 for r in rows])
        ju = [r["track"].get("joint_used") for r in rows]
        jtxt = "" if ju[0] is None else f" joint_used {np.mean([bool(x) for x in ju]):.2f}"
        print(f"  {n:38s} axis_valid p50 {np.median(av):6.1f} >=180 {np.mean(av>=180):.2f} | monitored p50 {np.median(mon):6.1f}{jtxt}")
