#!/usr/bin/env python3
"""Two regression-gate JSONs equal in every row except commit / config hash / date / latency / timing fields,
and (optionally) the per-frame work files equal except timing.   gate_identity.py <a.json> <b.json> [<work a> <work b>]"""
import glob
import json
import os
import sys

# metadata only, by exact path prefix (review C1: a substring list skipped e.g. every "doubleT_platform" row)
SKIP = ("created", "code.", "config.", "native.", "run.", "latency_ms.", "gate.baseline_")


def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from flat(v, f"{p}.{k}" if p else str(k))
    else:
        yield p, d


def strip(r):
    """a per-frame record without its wall-clock parts (timing_ms, health latency fields and latency messages)"""
    if isinstance(r, dict):
        out = {k: strip(v) for k, v in r.items() if k not in ("timing_ms", "latency_ms")}
        if isinstance(r.get("health"), dict):
            h = {k: v for k, v in r["health"].items() if "latency" not in k}
            h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]
            out["health"] = h
        return out
    if isinstance(r, list):
        return [strip(v) for v in r]
    return r


def same(x, y) -> bool:
    """equal without wall-clock parts; the health level is ignored only when either record has a latency message
    (the latency budget can raise the level by itself)"""
    sx, sy = strip(x), strip(y)
    lat = any("latency" in m for r in (x, y) for m in (r.get("health") or {}).get("messages", []))
    if lat:
        for s_ in (sx, sy):
            s_.get("health", {}).pop("level", None)
            s_.get("health", {}).pop("decision_level", None)
    return sx == sy


if __name__ != "__main__":
    raise SystemExit
a, b = (dict(flat(json.load(open(p)))) for p in sys.argv[1:3])
keys = [k for k in sorted(set(a) | set(b)) if not k.startswith(SKIP)]
diff = [k for k in keys if a.get(k) != b.get(k)]
health = [k for k in diff if ".health." in k]          # health level counts move with wall-clock latency
other = [k for k in diff if k not in health]
print("json rows compared", len(keys), "of", len(set(a) | set(b)), "| differing:", len(other), other[:30],
      "| health-level counts differing (latency-dependent):", health)
if len(sys.argv) > 4:
    nd = 0
    for f in sorted(glob.glob(os.path.join(sys.argv[3], "*.jsonl"))):
        g = os.path.join(sys.argv[4], os.path.basename(f))
        la, lb = open(f).read().splitlines(), open(g).read().splitlines()
        bad = sum(not same(json.loads(x), json.loads(y)) for x, y in zip(la, lb)) + abs(len(la) - len(lb))
        nd += bad
        if bad:
            print("  frames differing", os.path.basename(f), bad)
    print("per-frame files: frames differing in total (timing excluded):", nd)
