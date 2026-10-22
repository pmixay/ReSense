#!/usr/bin/env python3
"""Finding N1 reproducer: the node's new default clear_range_policy (conservative) with the default
sensor_profile (manual) / range_sensor_model (unknown) reports clear_distance 0.0 on every frame.

Calls the node's own projection (ros2_ws/.../decision_policy.candidate_ranges) exactly as
detector_node.py does under each policy, on a GO frame with 180 m clear. Positive control: the same
row with range_sensor_model pandar128 keeps a non-zero clear range.
    RESENSE_REPO=<tree> python node_policy_unknown.py
"""
import os, sys, json
R = os.environ["RESENSE_REPO"]
sys.path[:0] = [R, R + "/ros2_ws/src/resense_ros"]
from resense_ros.decision_policy import candidate_ranges  # noqa: E402
import resense_ros.decision_policy as dp  # noqa: E402

row = {"obstacle": False, "warning": False, "detections": [], "warnings": [], "clear_distance": 180.0,
       "health": {"level": "ok", "decision_level": "ok", "messages": [], "monitored_range": 180.0,
                  "clear_distance": 180.0}, "freshness": {"valid": True}}
pol = "v1"
out = {"repo": R, "decision_policy_file": dp.__file__}
for model in ("unknown", "pandar128", "falcon_prime"):
    r = candidate_ranges(row, pol, sensor_model=model, min_points_far=3, max_range=250.0 if model != "falcon_prime" else 400.0,
                         cap_small_target=True, profile="conservative_2026_10_17")
    out[model] = {"clear_distance": r["clear_distance"], "monitored_range": r["health"]["monitored_range"],
                  "monitored_small": r["monitored_small"], "decision": dp.evaluate_decision(r, pol).decision}
out["legacy"] = {"clear_distance": row["clear_distance"], "decision": dp.evaluate_decision(row, pol).decision}
print(json.dumps(out, indent=1))
