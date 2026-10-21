#!/usr/bin/env python3
"""Where each tree placed a range-job object, against the driven path (B6 ICP poses, gauge_stability.driven_path):
the true track lateral at the object's X in frame k is center(0) of control's object-free model + the sensor path's
lateral at X (the sensor rides at a fixed offset from the track axis). Only frames whose path reaches X.
    placement_truth.py <poses.json> <ctl_baseline.json> <ctl_job.json> <cand_job.json> [L]"""
import json, sys
import numpy as np
sys.path.insert(0, "/home/user/ReSense/scripts")
import gauge_stability as g

poses, base = json.load(open(sys.argv[1]))["rows"], json.load(open(sys.argv[2]))
ja, jb = json.load(open(sys.argv[3]))["rows"], json.load(open(sys.argv[4]))["rows"]
L = float(sys.argv[5]) if len(sys.argv) > 5 else 0.5
ps = g.driven_path(poses)
n = len(poses)
out = []
for ra, rb in zip(ja, jb):
    k = ra["k"]
    if ra.get("Y") is None or rb.get("Y") is None:
        continue
    X = ra["X"] + 0.5 * L
    seg, Pk = ps[k]
    Pinv = np.linalg.inv(Pk)
    Rk = np.array(base[k]["R"])
    pts = [np.zeros(3)]
    for j in range(k + 1, n):
        if ps[j][0] != seg:
            break
        p = Rk @ (Pinv @ ps[j][1])[:3, 3]
        pts.append(p)
        if p[0] > X + 5:
            break
    pts = np.array(pts)
    pts = pts[pts[:, 0] >= np.maximum.accumulate(pts[:, 0])]
    if pts[-1, 0] < X:
        continue
    yt = base[k]["center"] + float(np.interp(X, pts[:, 0], pts[:, 1]))
    out.append((k, round(X, 1), round(yt, 2), ra["Y"], rb["Y"], ra["hit"], rb["hit"]))
ea = [abs(o[3] - o[2]) for o in out]; eb = [abs(o[4] - o[2]) for o in out]
print("frames with truth:", len(out), "|ctl placement - truth| p50", round(float(np.median(ea)), 2) if ea else None, "|cand placement - truth| p50", round(float(np.median(eb)), 2) if eb else None)
for o in out[:: max(1, len(out) // 12)]:
    print("  k=%d X=%.1f truthY=%.2f ctlY=%.2f candY=%.2f ctl_hit=%s cand_hit=%s" % o)
