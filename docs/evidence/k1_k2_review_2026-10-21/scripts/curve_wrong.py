#!/usr/bin/env python3
"""How often the published curve is wrong where it is trusted: on the candidate's curve frames (rows with half_step,
i.e. joint_used), |published axis - driven path| at X in 60..160 m within the published trusted range, against
control's model on the same frames (gauge_stability.path_errors; truth = B6 poses).
    curve_wrong.py <track_control.json> <track_cand.json> <poses.json>"""
import json, sys
import numpy as np
sys.path.insert(0, "/home/user/ReSense/scripts")
import gauge_stability as g
ctl = json.load(open(sys.argv[1]))["rows"]; cand = json.load(open(sys.argv[2]))["rows"]
ps = g.driven_path(json.load(open(sys.argv[3]))["rows"])
xs = [60.0, 80.0, 100.0, 120.0, 140.0, 160.0]
ec, ek = g.path_errors(ctl, ps, xs), g.path_errors(cand, ps, xs)
curve = [k for k, r in enumerate(cand) if "half_step" in r]
n = worse = cbad = kbad = 0
rows = []
for k in curve:
    if k not in ek or k not in ec:
        continue
    vk = {x: e for x, e in ek[k].items() if x <= cand[k]["axis_valid"]}
    vc = {x: e for x, e in ec[k].items() if x <= ctl[k]["axis_valid"]}
    if not vk:
        continue
    n += 1
    mk, mc = max(vk.values()), max(vc.values()) if vc else 0.0
    kbad += mk > 1.05; cbad += mc > 1.05
    rows.append((k, round(mk, 2), round(mc, 2), cand[k]["axis_valid"], ctl[k]["axis_valid"]))
print(f"curve frames with truth in the trusted range: {n}; curve > 1.05 m off somewhere 60-160 m within its range: {kbad}; "
      f"control > 1.05 m within its own range on the same frames: {cbad}")
bad = [r for r in rows if r[1] > 1.05]
for r in bad[:15]:
    print("  frame %d: curve max err %.2f m (range %.0f) | control %.2f m (range %.0f)" % (r[0], r[1], r[3], r[2], r[4]))
