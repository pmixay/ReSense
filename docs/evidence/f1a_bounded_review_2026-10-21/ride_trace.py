#!/usr/bin/env python3
"""Reviewer's read-only tracer for a continuous replay (``f1_false_alarms_2026-10-19/scripts/replay.py``).

Wraps ``resense.detector.rail_reference_check``: at every call the v1.2.0 function (control worktree's
``resense/lowobj.py``, loaded by path) is evaluated on the same arguments; each cluster the candidate rejects and
v1.2.0 keeps is a new-branch rejection, logged with the frame index and
  pre0 (capped top < all-returns line + margin: the condition in the code),
  pre1 (capped top < low-free line + margin, line present: the pre-repair rule of 0acb18c),
  H, uncapped top, lines. Also counts clusters v1.2.0 rejects that the candidate keeps (must be 0).
The replay itself runs unchanged (runpy of replay.py's main with the given argv); the traced output must equal
the plain output, checked by the caller.

    RESENSE_REPO=<cand> python ride_trace.py <trace.jsonl> -- <replay.py args...>
"""
import importlib.util
import json
import os
import runpy
import sys
from pathlib import Path

ROOT = os.environ["RESENSE_REPO"]
sys.path.insert(0, ROOT)
REPLAY = "/home/user/ReSense/docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py"
CONTROL_LOWOBJ = "/home/user/wt/control/resense/lowobj.py"

out_path = sys.argv[1]
assert sys.argv[2] == "--"
argv = sys.argv[3:]

import resense.detector as detm  # noqa: E402
from resense import lowobj  # noqa: E402

spec = importlib.util.spec_from_file_location("ctrl_lowobj", CONTROL_LOWOBJ)
ctrl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctrl)
orig = detm.rail_reference_check
fh = open(out_path, "w")
state = {"call": 0}


def check(clusters, X, dy, h, cfg, sp, free=None):
    out = orig(clusters, X, dy, h, cfg, sp, free)
    cout = ctrl.rail_reference_check(clusters, X, dy, h, cfg, sp, free)
    io, ic = {id(c) for c in out}, {id(c) for c in cout}
    new = [c for c in out if id(c) not in ic]
    only_ctrl = sum(id(c) not in io for c in cout)
    rows = []
    Xr, dyr, hr = (X, dy, h) if free is None else (X[free], dy[free], h[free])
    for c in new:
        d = dy[c.points_idx]
        foot = (X >= c.bbox_min[0]) & (X <= c.bbox_max[0]) & (dy >= d.min()) & (dy <= d.max()) & (h < cfg.foot_max_top)
        top = max(float(c.height_max), float(h[foot].max()) if foot.any() else -9.0)
        ol = ctrl.local_rail_reference(c, X, dy, h, cfg, sp)
        fl = ctrl.local_rail_reference(c, Xr, dyr, hr, cfg, sp)
        H = lowobj.rail_head_top(c, Xr, dyr, hr, float(d.min()), float(d.max()), cfg, sp)
        m = cfg.local_rail_margin
        rows.append(dict(d=round(float(c.distance), 2), lat=round(float(c.lateral), 3), w=round(float(c.size[1]), 3),
                         cap=round(float(c.height_max), 3), top=round(top, 3), H=None if H is None else round(H, 3),
                         orig_line=None if ol is None else round(ol, 3), free_line=None if fl is None else round(fl, 3),
                         pre0=ol is not None and float(c.height_max) < ol + m,
                         pre1=fl is not None and float(c.height_max) < fl + m, n=int(c.points_idx.size)))
    if rows or only_ctrl:
        fh.write(json.dumps(dict(call=state["call"], new=rows, only_ctrl=only_ctrl)) + "\n")
        fh.flush()
    state["call"] += 1
    return out


detm.rail_reference_check = check
sys.argv = [REPLAY] + argv
try:
    runpy.run_path(REPLAY, run_name="__main__")
finally:
    fh.write(json.dumps(dict(calls=state["call"])) + "\n")
    fh.close()
