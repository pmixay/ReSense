#!/usr/bin/env python3
"""Node decisions (STOP > FAULT > CAUTION > GO, judge_runner.node_decision) per recording of two gate work
directories, and the per-frame transitions between them. ``decisions.py WORK_BASE WORK_CAND``"""
import glob
import json
import os
import sys
from collections import Counter


def dec(d):
    """The node's decision; a health warn whose only messages are wall-clock latency lines counts as ok
    (timing noise of a shared machine, not detector output)."""
    h = dict(d.get("health") or {})
    msgs = h.get("messages") or []
    if msgs and all("latency" in m for m in msgs):
        h["level"] = h["decision_level"] = "ok"
    level = h.get("level", "ok")
    if d["obstacle"]:
        return "STOP"
    if level == "error":
        return "FAULT"
    if d["warning"] or h.get("decision_level", level) == "warn":
        return "CAUTION"
    return "GO"


out = {}
for fa in sorted(glob.glob(os.path.join(sys.argv[1], "*.jsonl"))):
    name = os.path.basename(fa)[:-6]
    key = "new_data" if name.startswith("new_data_") else name
    a = [dec(json.loads(x)) for x in open(fa)]
    b = [dec(json.loads(x)) for x in open(os.path.join(sys.argv[2], os.path.basename(fa)))]
    o = out.setdefault(key, {"base": Counter(), "cand": Counter(), "transitions": Counter()})
    o["base"].update(a)
    o["cand"].update(b)
    o["transitions"].update(f"{x}->{y}" for x, y in zip(a, b) if x != y)
print(json.dumps({k: {kk: dict(vv) for kk, vv in v.items()} for k, v in out.items()}, indent=1))
