#!/usr/bin/env python3
"""Diagnostic (read-only wrap): run one review approach_bed scene on RESENSE_REPO and log, per frame, every call of
lowobj.rail_head_top (its result) and every cluster the bounded branch could judge: capped top, uncapped top, the
four region maxima, the top-surface spread. Also checks traced == plain (matched rows).

    RESENSE_REPO=<cand> python trace_scene.py raise side length width delta
"""
import json, os, sys
from pathlib import Path
import numpy as np
ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT); sys.path.insert(0, str(Path(ROOT) / "docs/evidence/f1a_b1_2026-10-20"))
sys.path.insert(0, "/home/user/ReSense/docs/evidence/f1a_completion_review_2026-10-20")
import synth_controls as sc  # noqa
from resense import lowobj

raise_, side, length, width, delta = float(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
spec = dict(raise_=raise_, dist=58.0, kind="rail", side=side, length=length, width=width, delta=delta, bottom="bed",
            nframes=45, approach_step=0.8)
plain = sc.run_scene(dict(spec))
log, frame = [], {"k": -1}
orig = lowobj.rail_head_top

def wrapped(c, X, dy, h, d0, d1, cfg, sp):
    r = orig(c, X, dy, h, d0, d1, cfg, sp)
    half = 0.5 * sp
    s = 1.0 if c.lateral > 0 else -1.0
    x0, x1 = float(c.bbox_min[0]), float(c.bbox_max[0]); xc = 0.5 * (x0 + x1)
    ok = (h > -0.3) & (h < cfg.foot_max_top)
    own = ok & (np.abs(dy - s * half) <= 0.1); oth = ok & (np.abs(dy + s * half) <= 0.1)
    def mx(m, lo, hi):
        k = m & (X >= lo) & (X <= hi)
        return None if not k.any() else [round(float(h[k].max()), 3), round(float(X[k][np.argmax(h[k])]), 2)]
    log.append(dict(call=len(log), x0=round(x0, 2), x1=round(x1, 2), lat=round(float(c.lateral), 3), cap=round(float(c.height_max), 3),
                    head=None if r is None else round(r, 3),
                    regions=[mx(own, x0 - 5, x0 - 0.3), mx(own, x1 + 0.3, x1 + 5), mx(oth, x0 - 5, xc), mx(oth, xc, x1 + 5)]))
    return r
lowobj.rail_head_top = wrapped
import resense.detector as detm
orig_check = detm.rail_reference_check
def check(clusters, X, dy, h, cfg, sp, free=None):
    out = orig_check(clusters, X, dy, h, cfg, sp, free)
    for c in clusters:
        if c.kind == "low" and c.zone == "gauge" and not c.reason:
            d = dy[c.points_idx]
            foot = (X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top)
            top = float(h[foot].max()) if foot.any() else None
            fx = X[foot]; fh = h[foot]
            log.append(dict(cluster=True, d=round(float(c.distance), 2), lat=round(float(c.lateral), 3), cap=round(float(c.height_max), 3),
                            uncapped=None if top is None else round(top, 3), rejected=any(c is o for o in out),
                            foot_top_pts=sorted([[round(float(a), 2), round(float(b), 3)] for a, b in zip(fx, fh)], key=lambda t: -t[1])[:4]))
    return out
detm.rail_reference_check = check
spec2 = dict(spec)
traced = []
det_rows = sc.run_scene(spec2)
print("traced == plain:", [r["matched"] for r in det_rows["rows"]] == [r["matched"] for r in plain["rows"]])
print(json.dumps(dict(matched=[r["matched"] for r in plain["rows"]], dist=[r["dist"] for r in plain["rows"]],
                      model_err=[r["rail_model_err"] for r in plain["rows"]][:1])))
for e in log:
    print(json.dumps(e))
