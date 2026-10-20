#!/usr/bin/env python3
"""Per-frame identity of two gate work directories (A8): every per-frame JSONL row equal in every field
except wall-clock timing (``timing_ms``, ``health.latency_p95_ms``) and what the latency drives
(a health ``level`` / ``decision_level`` "warn" and its message "latency p95 ... over the ... budget" only
where the other run has the same row without it). Also set F straight (``setF_straight.json``) except timings.
``cmp_frames.py WORK_A WORK_B``"""
import glob
import json
import os
import sys

A, B = sys.argv[1], sys.argv[2]


def norm(d):
    d = dict(d)
    d.pop("timing_ms", None)
    h = dict(d.get("health") or {})
    h.pop("latency_p95_ms", None)
    msgs = [m for m in h.get("messages", []) if "latency" not in m]
    h["messages"] = msgs
    d["health"] = h
    return d


def lat_only(x, y):
    """the rows differ only by a latency-driven health level"""
    hx, hy = dict(x["health"]), dict(y["health"])
    for h in (hx, hy):
        h.pop("level", None)
        h.pop("decision_level", None)
    return {**x, "health": hx} == {**y, "health": hy}


rows = files = diff = latency = 0
first = []
for fa in sorted(glob.glob(os.path.join(A, "*.jsonl"))):
    fb = os.path.join(B, os.path.basename(fa))
    la, lb = open(fa).read().splitlines(), open(fb).read().splitlines()
    files += 1
    if len(la) != len(lb):
        print("ROW COUNT", os.path.basename(fa), len(la), len(lb))
        diff += 1
        continue
    for i, (x, y) in enumerate(zip(la, lb)):
        rows += 1
        nx, ny = norm(json.loads(x)), norm(json.loads(y))
        if nx != ny:
            if lat_only(nx, ny):
                latency += 1
            else:
                diff += 1
                if len(first) < 10:
                    first.append((os.path.basename(fa), i))


def strip_t(o):
    if isinstance(o, dict):
        return {k: strip_t(v) for k, v in o.items() if "time" not in k and "wall" not in k and "_ms" not in k}
    if isinstance(o, list):
        return [strip_t(v) for v in o]
    return o


sf = None
pa, pb = os.path.join(A, "setF_straight.json"), os.path.join(B, "setF_straight.json")
if os.path.exists(pa) and os.path.exists(pb):
    sa, sb = json.load(open(pa)), json.load(open(pb))
    sf = strip_t(sa.get("summary")) == strip_t(sb.get("summary")) and strip_t(sa.get("results", sa.get("sequences"))) == strip_t(sb.get("results", sb.get("sequences")))
print(json.dumps({"files": files, "rows": rows, "rows_different": diff, "rows_latency_level_only": latency,
                  "first_differences": first, "setF_straight_equal": sf}))
