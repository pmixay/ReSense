#!/usr/bin/env python3
"""The ROS node's range path (``detector_node.py``: ``evaluate_decision``, then ``candidate_ranges`` with the
small-target cap for ``clear_range_policy`` conservative) applied to gate per-frame rows (every recording of a
regression-gate work directory), for one ``range_sensor_model``. Per recording: frames, decisions differing between
legacy and conservative, detection / warning / flag rows changed (must be 0), clear and monitored lowered / raised /
zeroed against the legacy (detector) values.

    node_policy_rows.py <gate work dir> --model unknown|pandar128|falcon_prime
"""
import argparse, glob, json, os, sys

ap = argparse.ArgumentParser(); ap.add_argument("work"); ap.add_argument("--model", default="unknown")
a = ap.parse_args()
from resense_ros.decision_policy import candidate_ranges, evaluate_decision  # noqa: E402
tot = {"frames": 0, "decision_differs": 0, "dets_or_warns_changed": 0, "clear_lowered": 0, "clear_raised": 0,
       "clear_zero": 0, "monitored_lowered": 0, "monitored_raised": 0}
for f in sorted(glob.glob(os.path.join(a.work, "*.jsonl"))):
    t = dict.fromkeys(tot, 0)
    for line in open(f):
        r = json.loads(line)
        row = {"obstacle": r["obstacle"], "warning": r["warning"], "health": dict(r["health"]),
               "clear_distance": float(r["clear_distance"]), "freshness": {"valid": True},
               "warnings": r["warnings"], "detections": r["detections"]}
        legacy = evaluate_decision(row, "v1").decision
        p = candidate_ranges(row, "v1", sensor_model=a.model, min_points_far=3, max_range=250.0,
                             cap_small_target=True, profile="conservative_2026_10_17")
        t["frames"] += 1
        t["decision_differs"] += evaluate_decision(p, "v1").decision != legacy
        t["dets_or_warns_changed"] += (p["detections"], p["warnings"], p["obstacle"], p["warning"]) != (
            row["detections"], row["warnings"], row["obstacle"], row["warning"])
        c0, c1 = row["clear_distance"], p["clear_distance"]
        m0, m1 = r["health"]["monitored_range"], p["health"]["monitored_range"]
        t["clear_lowered"] += c1 < c0; t["clear_raised"] += c1 > c0; t["clear_zero"] += c1 == 0 < c0
        t["monitored_lowered"] += m1 < m0; t["monitored_raised"] += m1 > m0
    print(f"{os.path.basename(f):45s} {t}")
    for k in tot:
        tot[k] += t[k]
print(f"TOTAL model {a.model}: {tot}")
