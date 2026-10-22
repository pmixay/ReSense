#!/usr/bin/env python3
"""Two judge-runner record files (A = control, B = candidate) of the same recording, frame by frame: STOP frames,
A STOP frames not STOP in B (lost), A STOP-episode onsets where B is not STOP (delayed onset), B STOP frames not
STOP in A (new) with whether A had a detection or warning on the same object (|dd| <= 1.5 m, |dY| <= 1.0 m),
decision changes by kind. Alignment (index, stamp, bag time) fails closed.
    rec_cmp.py A.jsonl B.jsonl"""
import json, sys
from collections import Counter
A = [json.loads(l) for l in open(sys.argv[1])]; B = [json.loads(l) for l in open(sys.argv[2])]
assert len(A) == len(B)
for x, y in zip(A, B):
    assert (x["i"], x["stamp"], x["bag_t"]) == (y["i"], y["stamp"], y["bag_t"]), x["i"]
sa = {r["i"] for r in A if r["decision"] == "STOP"}; sb = {r["i"] for r in B if r["decision"] == "STOP"}
onsets = [i for i in sorted(sa) if i - 1 not in sa]
new = []
for i in sorted(sb - sa):
    d = min(B[i]["dets"], key=lambda d: d["d"]) if B[i]["dets"] else None
    ref = A[i]["dets"] + A[i]["warns"]
    same = d is not None and any(abs(w["d"] - d["d"]) <= 1.5 and abs(w["c"][1] - d["c"][1]) <= 1.0 for w in ref)
    new.append([i, None if d is None else round(d["d"], 1), same])
ch = Counter(f'{x["decision"]}->{y["decision"]}' for x, y in zip(A, B) if x["decision"] != y["decision"])
print(json.dumps({"A": sys.argv[1], "B": sys.argv[2], "frames": len(A), "A_stop": len(sa), "B_stop": len(sb),
                  "lost": sorted(sa - sb), "delayed_onsets": [i for i in onsets if i not in sb],
                  "new": new, "decision_changes": dict(ch)}))
