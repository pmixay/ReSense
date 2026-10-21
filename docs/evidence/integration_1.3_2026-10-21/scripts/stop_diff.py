#!/usr/bin/env python3
"""STOP frames of two aligned record files (Falcon falcon_multi / falcon_trace records, judge_runner records, or one
gate work file): alignment by row count and stamp (fails closed); STOP frames lost (control STOP, candidate not) and
new (candidate STOP, control not), each listed with the candidate's / control's nearest STOP detection; STOP episodes
(maximal runs) of both; first STOP frame. A row is STOP when ``decision == "STOP"`` or ``obstacle`` is true.

    stop_diff.py <control.jsonl[.xz]> <cand.jsonl[.xz]> [--from I] [--to J]
"""
import argparse, json, lzma


def load(p):
    f = lzma.open(p, "rt") if p.endswith(".xz") else open(p)
    return [json.loads(l) for l in f if l.strip()]


def is_stop(r):
    return r.get("decision") == "STOP" if "decision" in r else bool(r.get("obstacle"))


def dets(r):
    for k in ("dets", "detections"):
        if r.get(k):
            return [(d.get("d", d.get("distance")), (d.get("c") or d.get("center") or [None, None])[1]) for d in r[k]]
    return []


def eps(s):
    s = sorted(s); n = 0; prev = None
    for i in s:
        n += prev is None or i != prev + 1; prev = i
    return n


def runs(s):
    out = []
    for i in sorted(s):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


ap = argparse.ArgumentParser(); ap.add_argument("a"); ap.add_argument("b")
ap.add_argument("--from", dest="lo", type=int, default=0); ap.add_argument("--to", dest="hi", type=int, default=10**9)
x = ap.parse_args()
A, B = load(x.a), load(x.b)
assert len(A) == len(B), (len(A), len(B))
for i, (p, q) in enumerate(zip(A, B)):
    assert p.get("stamp") == q.get("stamp"), (i, p.get("stamp"), q.get("stamp"))
idx = range(max(0, x.lo), min(len(A), x.hi + 1))
sa = {i for i in idx if is_stop(A[i])}; sb = {i for i in idx if is_stop(B[i])}
lost, new = sorted(sa - sb), sorted(sb - sa)
print(f"rows {len(A)} (window {idx.start}-{idx.stop - 1}); STOP control {len(sa)} cand {len(sb)}; "
      f"episodes control {eps(sa)} cand {eps(sb)}; first STOP control {min(sa) if sa else None} cand {min(sb) if sb else None}")
print(f"lost {len(lost)} {runs(lost)}")
print(f"new {len(new)} {runs(new)}")
for i in new:
    print(f"  new {i}: cand dets {dets(B[i])[:3]} | control decision {A[i].get('decision', A[i].get('obstacle'))} dets {dets(A[i])[:3]}")
for i in lost:
    print(f"  lost {i}: control dets {dets(A[i])[:3]} | cand decision {B[i].get('decision', B[i].get('obstacle'))} dets {dets(B[i])[:3]}")
