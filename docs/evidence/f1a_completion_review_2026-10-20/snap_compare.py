#!/usr/bin/env python3
"""Reviewer script: compare the three snapshot replays (reference f56ad5e, parent 450a99f, candidate a77d884)."""
import json
import sys
from pathlib import Path

PREFIX = sys.argv[1] if len(sys.argv) > 1 else "snap_"
D = Path(__file__).resolve().parent / "out"
r = {w: json.load(open(D / f"{PREFIX}{w}.json"))["rows"] for w in ("wt_ref", "wt_parent", "wt_cand")}
n = len(r["wt_ref"])
assert n == len(r["wt_cand"]) == len(r["wt_parent"])
print("rows", n)
for w in r:
    print(w, "rejected", sum(x["rejected"] for x in r[w]))
odd = [i for i in range(n) if r["wt_ref"][i]["rejected"] or not r["wt_cand"][i]["surface_branch_reached"]]
for i in odd:
    print("REF  ", r["wt_ref"][i])
    print("PAR  ", r["wt_parent"][i])
    print("CAND ", r["wt_cand"][i])
# rows rejected by candidate but not by parent, and vice versa
print("cand rejects, parent keeps:", sum(r["wt_cand"][i]["rejected"] and not r["wt_parent"][i]["rejected"] for i in range(n)))
print("parent rejects, cand keeps:", sum(r["wt_parent"][i]["rejected"] and not r["wt_cand"][i]["rejected"] for i in range(n)))
print("cand rejects, ref keeps   :", sum(r["wt_cand"][i]["rejected"] and not r["wt_ref"][i]["rejected"] for i in range(n)))
print("ref rejects, cand keeps   :", sum(r["wt_ref"][i]["rejected"] and not r["wt_cand"][i]["rejected"] for i in range(n)))
