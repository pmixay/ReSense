#!/usr/bin/env python3
"""Falcon (4,443 frames) control vs a candidate, from falcon_trace.py records: alignment (index, stamp, bag time; fails
closed); person STOP frames R = control STOP frames with i > 2900 minus the attributed false set of score_falcon_pos.py
{159, 2312-2314, 4394-4401}; lost = R - cand STOP; first person STOP (frame, distance of the nearest STOP detection);
new cand STOP frames with their nearest STOP detection and the nearest control detection/warning (distance, vehicle Y);
STOP episodes (maximal runs) over the whole recording for both.
    score_falcon.py <control.jsonl> <cand.jsonl>"""
import json, sys
A = [json.loads(l) for l in open(sys.argv[1])]; B = [json.loads(l) for l in open(sys.argv[2])]
assert len(A) == len(B) == 4443
for x, y in zip(A, B):
    assert (x["i"], x["stamp"], x["bag_t"]) == (y["i"], y["stamp"], y["bag_t"]), x["i"]
FALSE = {159, 2312, 2313, 2314} | set(range(4394, 4402))
sa = {r["i"] for r in A if r["decision"] == "STOP"}; sb = {r["i"] for r in B if r["decision"] == "STOP"}
R = {i for i in sa if i > 2900} - FALSE
lost = sorted(R - sb)
def first(rows, S):
    i = min(S); r = rows[i]
    return i, min(d["d"] for d in r["dets"]) if r["dets"] else None
def eps(S):
    S = sorted(S); n = 0; prev = None
    for i in S:
        n += prev is None or i != prev + 1; prev = i
    return n
print("control STOP", len(sa), "cand STOP", len(sb), "| person R", len(R), "lost", len(lost), lost[:20])
print("first person STOP control", first(A, R), "cand", first(B, sb & {i for i in range(2901, 4443)} - FALSE))
new = sorted(sb - sa)
print("new STOP frames", len(new), "| control STOP frames not STOP in cand (any)", sorted(sa - sb)[:20])
print("STOP episodes control", eps(sa), "cand", eps(sb), "| outside the person segment (i<=2900 or FALSE):",
      eps({i for i in sa if i <= 2900 or i in FALSE}), "->", eps({i for i in sb if i <= 2900 or i in FALSE}))
far = []
for i in new:
    d = min(B[i]["dets"], key=lambda d: d["d"]); ref = A[i]["dets"] + A[i]["warns"]
    m = min(ref, key=lambda r: abs(r["d"] - d["d"]) + abs(r["c"][1] - d["c"][1])) if ref else None
    ok = m is not None and abs(m["d"] - d["d"]) <= 1.5 and abs(m["c"][1] - d["c"][1]) <= 1.0
    if not ok:
        far.append(i)
    print(f"  new {i}: cand STOP d={d['d']} Y={d['c'][1]} | nearest control obj {None if m is None else (m['d'], m['c'][1])} {'same object' if ok else 'NO MATCH'}")
print("new STOP frames without a control detection/warning at the same place:", far)
