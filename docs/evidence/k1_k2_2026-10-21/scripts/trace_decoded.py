#!/usr/bin/env python3
"""Replay a node-decoded cache (judgement_2026-10-13/scripts/cache_decoded.py) through the jury NodeReplica of
$RESENSE_REPO with optional --set overrides and write one JSON line per frame: the node decision, every detection and
warning, the base track and (K2 union) the curve model with its trusted range and the number of curve clusters added.

  RESENSE_REPO=<tree> trace_decoded.py <decoded dir> <out.jsonl> [--set track.k=v ...] [--start N --end M]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import yaml

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402
from resense.frame import Frame  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("cache")
p.add_argument("out")
p.add_argument("--set", action="append", default=[])
p.add_argument("--start", type=int, default=0)
p.add_argument("--end", type=int, default=10 ** 9)
a = p.parse_args()
sets = {k: yaml.safe_load(v) for k, v in (s.split("=", 1) for s in a.set)}
meta = json.load(open(os.path.join(a.cache, "meta.json")))
files = sorted(glob.glob(os.path.join(a.cache, "f_*.npz")))
rep = jr.NodeReplica(overrides=sets)


def shape(t):
    return {"c": t.center, "yaw": t.yaw, "k": t.curvature, "step": t.curv_step, "knot": t.curv_knot,
            "valid": float(min(t.axis_valid, 9999.0))}


def det(d):
    return {"id": d.id, "d": round(float(d.distance), 3), "lat": round(float(d.lateral), 3), "zone": d.zone,
            "reason": d.reason, "kind": d.kind, "w": round(float(d.size[1]), 2), "y": round(float(d.center[1]), 3)}


with open(a.out, "w") as fo:
    for k, (m, f) in enumerate(zip(meta, files)):
        if k < a.start or k >= a.end:
            continue
        d = np.load(f)
        rep.continuity(m["topic"], m["frame_id"], m["stamp"], k)
        xyz_v = d["xyz"] @ rep.R_vs.T
        fr = Frame(xyz=xyz_v.astype(np.float32), intensity=d["inten"], ring=d["ring"] if m["has_ring"] else None,
                   stamp=m["stamp"], frame_id=m["frame_id"], meta={"n_raw": m["n_raw"], "n_near": m["n_near"]})
        det_ = rep.detector
        det_._curve_added = 0
        res = det_.process(fr, ego_speed=None)
        t = rep.detector.track                       # the model the detector reads (res.track: the published one)
        cv = getattr(t, "curve", None)
        fo.write(json.dumps({"i": k, "stamp": m["stamp"], "decision": jr.node_decision(res),
                             "clear": res.clear_distance, "det": [det(x) for x in res.detections],
                             "warn": [det(x) for x in res.warnings], "track": shape(t), "published": shape(res.track),
                             "curve": shape(cv) if cv is not None else None,
                             "added": int(getattr(rep.detector, "_curve_added", 0)),
                             "speed": res.ego_speed}) + "\n")
print(a.out, file=sys.stderr)
