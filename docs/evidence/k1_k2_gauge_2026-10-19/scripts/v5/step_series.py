#!/usr/bin/env python3
"""Signed axis bend parts at 150 m per frame: quadratic part (k 150^2/2), step part (s 90^2/2) for a recording jsonl.
step_series.py <jsonl> [every]"""
import json, sys
every = int(sys.argv[2]) if len(sys.argv) > 2 else 10
rows = [json.loads(l) for l in open(sys.argv[1])]
for i, r in enumerate(rows):
    if i % every:
        continue
    t = r["track"]
    kq = 0.5 * t["curvature"] * 150 ** 2
    st = 0.5 * t.get("curv_step", 0.0) * max(150 - t.get("curv_knot", 0.0), 0) ** 2
    print(f"{r['frame_id']} k*{t['curvature']*1e4:+6.2f}e-4 step {t.get('curv_step',0)*1e4:+6.2f}e-4 quad150 {kq:+6.2f} step150 {st:+6.2f} valid {t['axis_valid']:6.1f} sides {t['axis_sides']} stop {int(r['obstacle'])}")
