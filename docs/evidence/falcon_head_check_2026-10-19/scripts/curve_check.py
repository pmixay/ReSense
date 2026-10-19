"""Independent check of "the gauge under-bends a curve": driven-path curvature (ICP poses) vs the detector's axis.

Method differs from scripts/gauge_stability.py: fit y = b x + c x^2 to the driven path of each frame (x <= 100 m)
and compare 2c (path curvature) with the detector's 2 * half_curv, and the lateral gap at X m.

    python curve_check.py <unpacked b6_raw> <recording> <version dir> <first frame> <last frame> [X]
"""
import json
import sys

import numpy as np

b6, rec, ver = sys.argv[1], sys.argv[2], sys.argv[3]
lo, hi = int(sys.argv[4]), int(sys.argv[5])
x_at = float(sys.argv[6]) if len(sys.argv) > 6 else 90.0
P = json.load(open(f"{b6}/poses_{rec}.json"))["rows"]
T = json.load(open(f"{b6}/{ver}/track_{rec}.json"))["rows"]
n = len(P)
poses, seg, M = [], 0, np.eye(4)                 # compose poses within segments
for k, r in enumerate(P):
    if r["T"] is None:
        if k:
            seg += 1
        M = np.eye(4)
    else:
        M = M @ np.array(r["T"])
    poses.append((seg, M.copy()))
rows = []
for k in range(lo, hi):
    t = T[k]
    if "center" not in t:
        continue
    s, Pk = poses[k]
    Pi, R = np.linalg.inv(Pk), np.array(t["R"])
    pts = []
    for j in range(k, n):
        if poses[j][0] != s:
            break
        p = R @ (Pi @ poses[j][1])[:3, 3]
        pts.append(p)
        if p[0] > 130:
            break
    pts = np.array(pts)
    pts = pts[np.argsort(pts[:, 0])]
    if len(pts) < 20 or pts[-1, 0] < 80:
        continue
    x, y = pts[:, 0], pts[:, 1] - pts[0, 1]
    m = x <= 100
    (b, c), *_ = np.linalg.lstsq(np.column_stack([x[m], x[m] ** 2]), y[m], rcond=None)
    gap = abs((t["tan_yaw"] * x_at + t["half_curv"] * x_at ** 2) - (b * x_at + c * x_at ** 2))
    rows.append((k, 2 * c, 2 * t["half_curv"], gap, t["axis_valid"], pts[-1, 0]))
rows = np.array(rows)
print(f"{rec} {ver} frames {lo}-{hi}: usable {len(rows)}")
if len(rows):
    print("path curvature   median %.5f /m  (radius ~%.0f m)" % (np.median(rows[:, 1]), 1 / abs(np.median(rows[:, 1]))))
    print("detector curv.   median %.5f /m" % np.median(rows[:, 2]))
    print("ratio path/detector (median of per-frame ratios): %.1f" % np.median(rows[:, 1] / rows[:, 2]))
    print("lateral gap at X m  median %.2f m, p90 %.2f m; axis_valid median %.0f m"
          % (np.median(rows[:, 3]), np.percentile(rows[:, 3], 90), np.median(rows[:, 4])))
