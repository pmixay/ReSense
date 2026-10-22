#!/usr/bin/env python3
"""PROTOCOL B3: P4's raised-rail physical scenes (f1a_b1_2026-10-20/physical.py output), control vs candidate.
Per scene key: matched STOP frames on each side, frames lost / gained; empty scenes (top None): any gauge detection.
Positive control (--selftest): one injected loss must be found. Exit 1 on any loss or any empty-scene detection.

    python compare_physical.py <control.json> <candidate.json> [--selftest]
"""
import copy
import json
import sys


def compare(A, B):
    bad, lines = 0, []
    assert A.keys() == B.keys()
    for k in A:
        a = [r["matched_stop"] for r in A[k]]
        b = [r["matched_stop"] for r in B[k]]
        lost = [i for i, (u, v) in enumerate(zip(a, b)) if u and not v]
        gain = [i for i, (u, v) in enumerate(zip(a, b)) if v and not u]
        empty = "topNone" in k
        gauge = [sum(bool(r["result"].get("detections")) for r in X[k]) for X in (A, B)] if empty else None
        bad += bool(lost) or (empty and gauge[1] > 0)
        lines.append(f"{k}: matched {sum(a)} -> {sum(b)} lost {lost} gained {gain}"
                     + (f" empty-scene frames with detections {gauge[0]} -> {gauge[1]}" if empty else ""))
    return bad, lines


A = json.load(open(sys.argv[1]))
B = json.load(open(sys.argv[2]))
if "--selftest" in sys.argv:
    assert compare(A, A)[0] == 0
    C = copy.deepcopy(B)
    k = next(k for k in C if any(r["matched_stop"] for r in C[k]))
    next(r for r in C[k] if r["matched_stop"])["matched_stop"] = False
    assert compare(B, C)[0] == 1
    print("selftest PASS")
bad, lines = compare(A, B)
print("\n".join(lines))
print("scenes failing:", bad)
sys.exit(1 if bad else 0)
