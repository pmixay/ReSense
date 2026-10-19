#!/usr/bin/env python3
"""A gauge_stability.py-style track.json from a gate per-frame jsonl (PROXY: the gate's eval_real pipeline on the
int16 gate cache, not the judge node replica on the decoded cache). R = identity; asserts every frame's mount
correction is roll = pitch = yaw = 0 (as in the B6 base tracks of these recordings).
gate2track.py <gate jsonl> <out track.json>"""
import json, sys
import numpy as np
rows = []
for k, l in enumerate(open(sys.argv[1])):
    r = json.loads(l)
    m = r.get("mount") or {}
    assert all(abs(float(m.get(a, 0.0) or 0.0)) == 0.0 for a in ("roll_deg", "pitch_deg", "yaw_deg")), (k, m)
    t = r["track"]
    row = {"i": k, "decision": "STOP" if r["obstacle"] else ("CAUTION" if r["warning"] else "GO"),
           "R": np.eye(3).tolist(), "center": t["center"], "tan_yaw": float(np.tan(t["yaw"])),
           "half_curv": 0.5 * t["curvature"], "axis_valid": t["axis_valid"]}
    if t.get("curv_step"):
        row.update(half_step=0.5 * t["curv_step"], knot=t["curv_knot"])
    rows.append(row)
json.dump({"cache": sys.argv[1], "repo": "gate-proxy", "range_max": 250.0, "rows": rows}, open(sys.argv[2], "w"))
print(sys.argv[2], len(rows))
