#!/usr/bin/env python3
"""Reviewer script: tabulate unit_controls results of the three sources (ref f56ad5e / parent 450a99f / cand a77d884).

    python unit_compare.py <out dir>
"""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
r = {t: json.load(open(D / f"unit_{t}.json"))["rows"] for t in ("ref", "parent", "cand")}
n = len(r["ref"])
for t in r:
    assert len(r[t]) == n
print(f"{'variant / parameters':92s} ref     parent  cand")
for i in range(n):
    a, b, c = (r[t][i] for t in ("ref", "parent", "cand"))
    strip = lambda d: {k: v for k, v in d["params"].items() if k != "hide_fraction"}  # noqa: E731
    assert a["name"] == b["name"] == c["name"] and strip(a) == strip(b) == strip(c)
    p = ", ".join(f"{k}={v}" for k, v in strip(a).items())
    flag = "" if a["decision"] == b["decision"] == c["decision"] else "   <-- sources differ"
    print(f"{a['name'] + ' ' + p:92s} {a['decision']:7s} {b['decision']:7s} {c['decision']:7s}{flag}")
