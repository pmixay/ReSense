#!/usr/bin/env python3
"""Independent check of labels/doubleT_obstacle.json against the raw cloud, without the detector's
track model: rails found as the two ridges of the near-field cloud (X 8-30 m), rail-head plane fitted
from them; then for chosen frames the points in X 50-62 m are clustered (scipy single linkage 0.4 m)
and each cluster's nearest X, lateral offset from the rail axis, height above the rail head and
in-envelope status (|dy| <= 1.05 m, 0.12..3.0 m above the rail head) are printed next to the label.
"""
import json
import sys

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage

sys.path.insert(0, "/tmp/claude-0/-home-user-ReSense/a8531feb-4e7f-5021-abc8-41e329ea6e28/scratchpad/judgement_2026-10-13/scripts")
from judge_runner import iter_raw, db3_files, NodeReplica  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

BAG = sys.argv[1]
LAB = json.load(open("/home/user/ReSense/labels/doubleT_obstacle.json"))
FRAMES = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [0, 7, 8, 20, 40, 60, 68, 69, 70, 100, 150, 200]

rep = NodeReplica()
R = rep.R_vs


def rails(xyz):
    """Rail lines fitted in X 6-30 m without the detector: scan yaw (-3..3 deg) and a 0.15 m height band, take
    the y - tan(yaw) x histogram pair 1.59 +- 0.06 m apart with the most points in its weaker ridge; then the
    rail-head height as a line in x (80th percentile of the ridge points per 2 m). Returns axis(x), spacing,
    railhead_z(x), yaw (deg)."""
    m = (xyz[:, 0] > 6) & (xyz[:, 0] < 30) & (np.abs(xyz[:, 1]) < 3)
    p = xyz[m]
    zmed = np.percentile(p[:, 2], 20)
    best = (-1, 0, 0, 0, 0)
    for yaw in np.arange(-3, 3, 0.05):
        t = np.tan(np.radians(yaw))
        for zlo in np.arange(zmed - 0.3, zmed + 0.5, 0.1):
            b = p[(p[:, 2] > zlo) & (p[:, 2] < zlo + 0.15)]
            h, e = np.histogram(b[:, 1] - t * b[:, 0], bins=np.arange(-3, 3, 0.04))
            c = 0.5 * (e[1:] + e[:-1])
            for i in range(len(c)):
                for jj in range(i + 37, min(i + 43, len(c))):
                    if abs(c[jj] - c[i] - 1.59) < 0.06 and abs(c[i] + c[jj]) < 2.0:
                        sc = min(h[i], h[jj])
                        if sc > best[0]:
                            best = (sc, yaw, zlo, c[i], c[jj])
    _, yaw, zlo, yl, yr = best
    t = np.tan(np.radians(yaw))
    yp = p[:, 1] - t * p[:, 0]
    rh = p[((np.abs(yp - yl) < 0.05) | (np.abs(yp - yr) < 0.05)) & (p[:, 2] > zlo - 0.2) & (p[:, 2] < zlo + 0.35)]
    xs, zs = [], []
    for x0 in np.arange(6, 30, 2.0):
        q = rh[(rh[:, 0] >= x0) & (rh[:, 0] < x0 + 2)]
        if len(q) > 3:
            xs.append(x0 + 1)
            zs.append(np.percentile(q[:, 2], 80))
    a, b = np.polyfit(xs, zs, 1)
    yc0 = 0.5 * (yl + yr)
    return (lambda x: yc0 + t * x), yr - yl, (lambda x: a * x + b), yaw, zmed


want = set(FRAMES)
for i, (ts, topic, raw) in enumerate(iter_raw(db3_files(BAG)[0])):
    if i not in want:
        continue
    msg = fastcloud.parse_pointcloud2(raw)
    xyz_s, inten, ring, _, _ = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
    xyz = xyz_s @ R.T.astype(np.float32)
    axis, gauge_w, zrail, yawd, zb = rails(xyz)
    yc, zr = axis(56.0), zrail(56.0)
    m = (xyz[:, 0] > 50) & (xyz[:, 0] < 62) & (np.abs(xyz[:, 1] - yc) < 4) & (xyz[:, 2] > zr - 0.3) & (xyz[:, 2] < zr + 2.3)
    p = xyz[m]
    print(f"frame {i}: axis y0={axis(0):+.3f} yaw={yawd:+.2f} deg -> y(56m)={yc:+.2f}; spacing={gauge_w:.2f}; railhead z(0)={zrail(0):+.2f} z(56)={zr:+.2f}; {len(p)} pts")
    if len(p) >= 2:
        Z = linkage(p, "single")
        lab = fcluster(Z, 0.4, "distance")
        for k in np.unique(lab):
            q = p[lab == k]
            if len(q) < 5:
                continue
            dy = q[:, 1] - yc
            h = q[:, 2] - zr
            inside = (np.abs(dy) <= 1.05) & (h >= 0.12) & (h <= 3.0)
            print(f"   cluster n={len(q):3d} Xmin={q[:,0].min():6.2f} dy=[{dy.min():+.2f},{dy.max():+.2f}] mean {dy.mean():+.2f} "
                  f"h=[{h.min():+.2f},{h.max():+.2f}] in-envelope pts={int(inside.sum())}")
    for o in LAB.get(f"{i:05d}", []):
        print(f"   LABEL {o['label']:16s} d={o['distance']} lat={o['lateral']} in_gauge={o['in_gauge']} n={o.get('n_points')} h={o.get('h_above_rail')}")
