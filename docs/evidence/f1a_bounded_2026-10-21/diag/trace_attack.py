#!/usr/bin/env python3
"""Diagnostic (read-only): one review attack.py scene on RESENSE_REPO; at every frame, every cluster the bounded
branch rejects (switch-off decision computed alongside) with H, the four region maxima, the max of the extended
search, the footprint returns, and whether the face test fires. Checks traced == plain.
    RESENSE_REPO=<cand> REVIEW_DIR=<dir> python trace_attack.py <family> <scene index>"""
import dataclasses, json, os, sys
import numpy as np
sys.path.insert(0, os.environ["REVIEW_DIR"])
import attack
from resense import lowobj
import resense.detector as detm
fam, idx = sys.argv[1], int(sys.argv[2])
spec = attack.scenes(fam)[idx]
plain = attack.run_scene(dict(spec, trace=False))
cur = {"k": -1}
orig_process, orig_check = detm.Detector.process, detm.rail_reference_check
log = []
def process(self, *a, **kw):
    cur["k"] += 1
    return orig_process(self, *a, **kw)
def check(cl, X, dy, h, cfg, sp, free=None):
    out = orig_check(cl, X, dy, h, cfg, sp, free)
    off = orig_check(cl, X, dy, h, dataclasses.replace(cfg, rail_head_bounded=False), sp, free)
    for c in out:
        if any(c is o for o in off):
            continue
        d = dy[c.points_idx]; x0, x1 = float(c.bbox_min[0]), float(c.bbox_max[0])
        Xr, dyr, hr = X[free], dy[free], h[free]
        H = lowobj.rail_head_top(c, Xr, dyr, hr, float(d.min()), float(d.max()), cfg, sp)
        ext = (X >= x0 - .3) & (X <= x1 + cfg.rail_head_extent) & (dy >= d.min() - .05) & (dy <= d.max() + .05) & (h < 1.5)
        e = np.flatnonzero(ext)
        top_e = sorted([[round(float(X[i]), 2), round(float(dy[i]), 3), round(float(h[i]), 3)] for i in e], key=lambda t: -t[2])[:6]
        foot = (X >= x0) & (X <= x1) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top)
        fp = sorted([[round(float(X[i]), 2), round(float(dy[i]), 3), round(float(h[i]), 3)] for i in np.flatnonzero(foot)], key=lambda t: -t[2])
        # object returns anywhere near (x0-1 .. x1+3, |dy - lat| < 0.4), highest
        near = (X >= x0 - 1) & (X <= x1 + 3) & (np.abs(dy - float(c.lateral)) < 0.4) & (h < 1.5)
        nr = sorted([[round(float(X[i]), 2), round(float(dy[i]), 3), round(float(h[i]), 3)] for i in np.flatnonzero(near)], key=lambda t: -t[2])[:8]
        log.append(dict(frame=cur["k"], x0=round(x0, 2), x1=round(x1, 2), d=[round(float(d.min()), 3), round(float(d.max()), 3)],
                        H=H, ext_top=top_e, footprint=fp, near_top=nr))
    return out
detm.Detector.process = process; detm.rail_reference_check = check
tr = attack.run_scene(dict(spec, trace=False))
print("spec", json.dumps(spec))
print("traced == plain:", [r["matched"] for r in tr["rows"]] == [r["matched"] for r in plain["rows"]])
print("matched frames", [r["frame"] for r in plain["rows"] if r["matched"]])
for e in log:
    print(json.dumps(e))
