#!/usr/bin/env python3
"""Reviewer script: for the frames in which the new branch REJECTS a cluster of a real box in an approach scene, print
where the returns that define the 'head surface' S come from: their along-track X relative to the cluster's bbox
and to the box's true extent, their height, and whether they lie on the box's top face.

Scene: box standing on the bed against a rail (z0 = bed, top = real head + delta), approach 58 m -> 22 m, 0.8 m per
frame (synth_controls 'approach_bed'). The truth is known (the box top is at real head + delta); S is compared with
it: S - box_top ~ 0 means the 'surface' is the object's own top face (self-support).

    RESENSE_REPO=<checkout> python self_support_check.py raise side L W delta [frames up to]
"""
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth_controls as sc  # noqa: E402
from resense import lowobj  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
import resense.detector as detm  # noqa: E402
from resense.frame import Frame  # noqa: E402

raise_, side, length, width, delta = (float(v) for v in sys.argv[1:6])
upto = int(sys.argv[6]) if len(sys.argv) > 6 else 45
rc = sc.rc
orig_surf, orig_check = lowobj._rail_surface_reference, detm.rail_reference_check
cur = {}


def surf(c, X, dy, h, d0, d1, cfg, sp):
    r = orig_surf(c, X, dy, h, d0, d1, cfg, sp)
    if r is not None:
        w = cfg.local_rail_window
        m = (np.abs(h - r) < 1e-4) & (dy >= d0) & (dy <= d1) & (X > c.bbox_min[0] - w) & (X < c.bbox_max[0] + w)
        cur.setdefault("calls", []).append(dict(S=float(r), x_top=sorted(set(np.round(X[m], 2).tolist())),
                                               bbox_x=(round(float(c.bbox_min[0]), 2), round(float(c.bbox_max[0]), 2)),
                                               lat=round(float(c.lateral), 3), cap=round(float(c.height_max), 3)))
    else:
        cur.setdefault("calls", []).append(None)
    return r


def check(clusters, X, dy, h, cfg, sp, free=None):
    cur.clear()
    out = orig_check(clusters, X, dy, h, cfg, sp, free)
    cur["rejected"] = [any(c is o for o in out) for c in clusters if c.kind == "low"]
    return out


lowobj._rail_surface_reference = surf
detm.rail_reference_check = check
det = Detector(DetectorConfig())
for k in range(upto):
    d_k = 58.0 - 0.8 * k
    rr, boxes, yc, head = sc.make_scene(raise_, d_k, "rail", int(side), length, width, delta, "bed")
    fr = rc.frame(rail_raise=rr, boxes=boxes, seed=1000 * k + 7, stamp=0.1 * k)
    cur.clear()
    det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
    calls = [c for c in cur.get("calls", []) if c is not None]
    if calls:
        # box top in the detector's height frame = real head + delta - model rail plane at the object
        model_err = float(det.track.rail_z(d_k)) - head          # plane minus real head (negative = plane low)
        box_top_h = delta - model_err
        for c in calls:
            on_box = [x for x in c["x_top"] if d_k <= x <= d_k + length]
            print(f"f{k:02d} box x [{d_k:.2f}, {d_k + length:.2f}] box top in h-frame {box_top_h:+.3f} | S {c['S']:+.3f} "
                  f"(S - box top {c['S'] - box_top_h:+.3f}) defined by returns at x {c['x_top']} "
                  f"({len(on_box)} of {len(c['x_top'])} on the box) | cluster bbox x {c['bbox_x']} lat {c['lat']} "
                  f"capped top {c['cap']} | rejected {cur.get('rejected')}")
