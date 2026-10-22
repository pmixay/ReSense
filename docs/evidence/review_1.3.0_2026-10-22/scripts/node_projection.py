#!/usr/bin/env python3
"""The node's clear_range_policy applied offline to detector records (no ROS in this container): for each frame
the row the node builds before publishing (obstacle, warning, warnings with their distances, health level /
decision level, monitored range, clear distance, a valid freshness record) is passed through the node's own
resense_ros.decision_policy.candidate_ranges exactly as detector_node.py calls it for `conservative`
(cap_small_target true, profile conservative_2026_10_17, min_points_far from the config = 3), and compared with
legacy (the record as is). Reports decisions before / after (evaluate_decision), clear and monitored lowered /
raised, median clear, GO frames with clear 0.
    RESENSE_REPO=<tree> node_projection.py <records.jsonl> --model pandar128|falcon_prime|unknown --max-range M
"""
import argparse, json, os, sys
import numpy as np
R = os.environ["RESENSE_REPO"]
sys.path[:0] = [R, R + "/ros2_ws/src/resense_ros"]
from resense_ros.decision_policy import candidate_ranges, evaluate_decision  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("records")
ap.add_argument("--model", required=True)
ap.add_argument("--max-range", type=float, default=250.0)
ap.add_argument("--json", default="")
a = ap.parse_args()
n = dec_changed = low_c = rai_c = low_m = rai_m = go_zero = 0
cl, cc = [], []
for line in open(a.records):
    r = json.loads(line)
    if r.get("monitored") is None:
        continue
    row = {"obstacle": bool(r["obstacle"]), "warning": bool(r["warning"]),
           "warnings": [{"distance": float(w["d"]), "reason": w.get("reason", "")} for w in r["warns"]],
           "health": {"level": r["level"], "decision_level": r.get("dlevel", r["level"]),
                      "monitored_range": float(r["monitored"]), "clear_distance": float(r["clear"])},
           "clear_distance": float(r["clear"]), "freshness": {"valid": True}}
    d0 = evaluate_decision(row).decision
    p = candidate_ranges(row, "v1", sensor_model=a.model, min_points_far=3, max_range=a.max_range,
                         cap_small_target=True, profile="conservative_2026_10_17")
    d1 = evaluate_decision(p).decision
    n += 1
    dec_changed += d0 != d1 or d0 != r["decision"]
    c0, c1 = float(r["clear"]), float(p["clear_distance"])
    m0, m1 = float(r["monitored"]), float(p["health"]["monitored_range"])
    low_c += c1 < c0; rai_c += c1 > c0 + 1e-9; low_m += m1 < m0; rai_m += m1 > m0 + 1e-9
    go_zero += d1 == "GO" and c1 == 0.0
    cl.append(c0); cc.append(c1)
out = {"records": a.records, "model": a.model, "frames": n, "decision_changed": dec_changed,
       "clear_lowered": low_c, "clear_raised": rai_c, "monitored_lowered": low_m, "monitored_raised": rai_m,
       "go_frames_with_clear_0": go_zero, "median_clear_legacy": float(np.median(cl)) if cl else None,
       "median_clear_conservative": float(np.median(cc)) if cc else None,
       "max_clear_conservative": float(max(cc)) if cc else None}
print(json.dumps(out))
if a.json:
    open(a.json, "a").write(json.dumps(out) + "\n")
