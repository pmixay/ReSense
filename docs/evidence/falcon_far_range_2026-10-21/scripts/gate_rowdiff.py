#!/usr/bin/env python3
"""Criterion 12: per-frame comparison of two regression-gate work directories (v1.2.0 vs candidate).
Every field is compared except wall-clock timing (``*_ms``, ``latency*``, ``wall_s``); differences are
listed per path, and the health-message differences are printed so they can be checked by eye.

    gate_rowdiff.py <v120_work> <cand_work> --out <json>"""
import argparse
import glob
import json
import os
from collections import Counter


def timing(k):
    return k.endswith("_ms") or "latency" in k or k in ("wall_s", "elapsed_s")


def walk(a, b, p, c):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in set(a) | set(b):
            if not timing(k):
                walk(a.get(k), b.get(k), p + "." + k, c)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for x, y in zip(a, b):
            walk(x, y, p + "[]", c)
    elif a != b:
        c[p] += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    for f in sorted(glob.glob(os.path.join(a.a, "*.jsonl"))):
        g = os.path.join(a.b, os.path.basename(f))
        A = [json.loads(line) for line in open(f)]
        B = [json.loads(line) for line in open(g)]
        c, rows, msgs = Counter(), [], []
        for i, (x, y) in enumerate(zip(A, B)):
            ci = Counter()
            walk(x, y, "", ci)
            if ci:
                rows.append(i)
                c.update(ci)
                mx = (x.get("health") or {}).get("messages")
                my = (y.get("health") or {}).get("messages")
                if mx != my:
                    msgs.append({"row": i, "a": sorted(set(mx or []) - set(my or [])), "b": sorted(set(my or []) - set(mx or []))})
        res[os.path.basename(f)] = {"rows": [len(A), len(B)], "differing_rows": len(rows), "fields": dict(c),
                                    "message_differences": msgs[:200]}
    for f in sorted(glob.glob(os.path.join(a.a, "*.json"))):
        g = os.path.join(a.b, os.path.basename(f))
        c = Counter()

        def walk2(x, y, p):
            if isinstance(x, dict) and isinstance(y, dict):
                for k in set(x) | set(y):
                    walk2(x.get(k), y.get(k), p + "." + k)
            elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
                for u, v in zip(x, y):
                    walk2(u, v, p + "[]")
            elif x != y:
                c[p] += 1
        walk2(json.load(open(f)), json.load(open(g)), "")
        res[os.path.basename(f)] = {"fields": dict(c)}
    json.dump(res, open(a.out, "w"), indent=1)
    for k, v in res.items():
        print(k, v.get("rows"), v.get("differing_rows"), v["fields"])


if __name__ == "__main__":
    main()
