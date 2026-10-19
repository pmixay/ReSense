#!/usr/bin/env python3
"""Compare two dev jsonl runs frame by frame: equal track (without joint_used/joint_reach) and decisions; for v5 runs
print joint_used frames.   devcmp.py A.jsonl B.jsonl"""
import json, sys
A = [json.loads(l) for l in open(sys.argv[1])]
B = [json.loads(l) for l in open(sys.argv[2])]
def norm(r):
    r = dict(r); r.pop("timing_ms", None)
    t = dict(r["track"]); t.pop("joint_used", None); t.pop("joint_reach", None); r["track"] = t
    h = dict(r.get("health") or {}); h.pop("latency_p95_ms", None); h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]
    h.pop("level", None); h.pop("decision_level", None); r["health"] = h
    return r
first = None; nd = 0
for i, (a, b) in enumerate(zip(A, B)):
    if norm(a) != norm(b):
        nd += 1
        first = i if first is None else first
used = [i for i, b in enumerate(B) if b["track"].get("joint_used")]
print(f"frames {len(A)}/{len(B)}  differing {nd}  first differing {first}  joint_used frames in B: {len(used)}",
      (used[:5], used[-5:]) if used else "")
# runs of joint_used
runs, s = [], None
for i, b in enumerate(B):
    u = bool(b["track"].get("joint_used"))
    if u and s is None: s = i
    if not u and s is not None: runs.append((s, i - 1)); s = None
if s is not None: runs.append((s, len(B) - 1))
print("joint_used runs:", runs[:30], "... n runs", len(runs))
# differing frames that are not joint_used and not right after
nd2 = [i for i, (a, b) in enumerate(zip(A, B)) if norm(a) != norm(b) and not b["track"].get("joint_used")]
print("differing frames with joint_used False:", len(nd2), nd2[:20])
