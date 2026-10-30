#!/usr/bin/env python3
"""Picture + numbers of one attack.py scene frame: the raw returns near the target (side view x-z and top view x-y),
the target box outline, and, in the candidate's own height frame, each candidate cluster's footprint returns and
whether the face test (_faces_sensor) finds stacked returns.  Read-only wrap of rail_reference_check.
    RESENSE_REPO=<cand> python pic_frame.py <family> <scene index> <frame> <out.png>"""
import os, sys, json
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parent))
import attack as A
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
import resense.detector as detm
from resense import lowobj
fam, si, fk, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
spec = A.scenes(fam)[si]
det = Detector(DetectorConfig()); rays = A.ray_set(spec)
orig = detm.rail_reference_check; info = {}
def check(clusters, X, dy, h, cfg, sp, free=None):
    o = orig(clusters, X, dy, h, cfg, sp, free)
    if info.get("k") == fk:
        rows = []
        for c in clusters:
            if c.kind != "low" or c.zone != "gauge":
                continue
            d = dy[c.points_idx]
            foot = (X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top)
            top = max(float(c.height_max), float(h[foot].max()))
            surf = foot & (h >= top - cfg.rail_head_top_band)
            Xr, dyr, hr = X[free], dy[free], h[free]
            H = lowobj.rail_head_top(c, Xr, dyr, hr, float(d.min()), float(d.max()), cfg, sp)
            face = lowobj._faces_sensor(X, dy, h, surf, foot, cfg)
            rows.append(dict(d=round(float(c.distance), 2), lat=round(float(c.lateral), 3), top=round(top, 3), H=H and round(H, 3),
                             face=face, rejected=any(c is q for q in o),
                             foot=sorted([[round(float(a), 3), round(float(b), 3), round(float(e), 3)] for a, b, e in zip(X[foot], dy[foot], h[foot])])))
        info["rows"] = rows
    return o
detm.rail_reference_check = check
for k in range(fk + 1):
    d = spec.get("start", 58.0) - spec.get("step", 0.8) * k
    fr, yt = A.build_frame(spec, d, k, rays); info["k"] = k
    res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
o0 = spec["objects"][0]
for r in info["rows"]:
    print(json.dumps(r))
P = fr.xyz; m = (P[:, 0] > d - 1.5) & (P[:, 0] < d + o0["length"] + 1.5) & (np.abs(P[:, 1] - yt) < 0.5)
fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
ax[0].scatter(P[m, 0], P[m, 2], s=6); ax[0].set_xlabel("x (m)"); ax[0].set_ylabel("z vehicle (m)")
# outline: the target's bounding box from its spec (box, wedge or cylinder alike)
x0 = d + o0.get("dx", 0.0); L, W = o0["length"], o0["width"]
if o0.get("type") == "cyl_y":
    L, W = o0["length"], o0["width"]
b = (x0, x0 + L, yt - W / 2, yt + W / 2, A.rc2.FLOOR if o0.get("bottom", "bed") == "bed" else A.head_at(spec, x0, o0["side"]),
     A.head_at(spec, x0, o0["side"]) + o0["delta"])
ax[0].add_patch(plt.Rectangle((b[0], b[4]), b[1] - b[0], b[5] - b[4], fill=False, color="r"))
ax[0].axhline(A.head_at(spec, d, o0["side"]), color="g", ls="--", lw=0.8, label="real head top")
ax[0].legend(); ax[0].set_title(f"{fam}#{si} frame {fk}: side view, |y - y_box| < 0.5")
ax[1].scatter(P[m, 0], P[m, 1], s=6, c=P[m, 2], cmap="viridis"); ax[1].add_patch(plt.Rectangle((b[0], b[2]), b[1] - b[0], b[3] - b[2], fill=False, color="r"))
ax[1].set_xlabel("x (m)"); ax[1].set_ylabel("y (m)"); ax[1].set_title("top view (colour = z)")
plt.tight_layout(); plt.savefig(out, dpi=110); print("saved", out)
