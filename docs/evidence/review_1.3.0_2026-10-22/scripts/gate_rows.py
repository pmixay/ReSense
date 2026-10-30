#!/usr/bin/env python3
"""Reviewer's comparison of two regression-gate work directories (per-frame detector rows, A = control,
B = candidate), independent of the gate's own grading. Per recording / ride piece:
frames, STOP frames (obstacle), STOP episodes (maximal runs), A STOP frames not STOP in B (lost), A episode
onsets at which B is not STOP (delayed onset), B STOP frames not STOP in A (new), and B episodes containing no A
STOP frame (added episodes), each with its frames, the nearest STOP detection (distance, lateral) at the onset and
whether A had a warning or detection on the same object there (|dd| <= 1.5 m, |dlat| <= 1.0 m).
    gate_rows.py <workA> <workB> [--json out]
"""
import argparse, glob, json, os

ap = argparse.ArgumentParser()
ap.add_argument("A"); ap.add_argument("B"); ap.add_argument("--json", default="")
a = ap.parse_args()


def rows(p):
    return [json.loads(l) for l in open(p)]


def runs(S):
    out = []
    for i in sorted(S):
        if out and i == out[-1][1] + 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


res = {}
for pa in sorted(glob.glob(os.path.join(a.A, "*.jsonl"))):
    name = os.path.basename(pa)[:-6]
    pb = os.path.join(a.B, name + ".jsonl")
    A, B = rows(pa), rows(pb)
    assert len(A) == len(B), name
    for x, y in zip(A, B):
        assert (x["frame"], x["stamp"]) == (y["frame"], y["stamp"]), (name, x["frame"])
    sa = {k for k, r in enumerate(A) if r["obstacle"]}
    sb = {k for k, r in enumerate(B) if r["obstacle"]}
    ea, eb = runs(sa), runs(sb)
    added = []
    for e in eb:
        if any(k in sa for k in range(e[0], e[1] + 1)):
            continue
        r = B[e[0]]
        d = min(r["detections"], key=lambda d: d["distance"]) if r["detections"] else None
        ref = A[e[0]]["detections"] + A[e[0]]["warnings"]
        same = d is not None and any(abs(w["distance"] - d["distance"]) <= 1.5 and abs(w["lateral"] - d["lateral"]) <= 1.0
                                     for w in ref)
        added.append({"frames": [A[e[0]]["frame"], A[e[1]]["frame"]],
                      "det": None if d is None else [round(d["distance"], 2), round(d["lateral"], 2)],
                      "A_had_same_object": same})
    res[name] = {"frames": len(A), "A_stop": len(sa), "B_stop": len(sb), "A_eps": len(ea), "B_eps": len(eb),
                 "lost": [A[k]["frame"] for k in sorted(sa - sb)],
                 "delayed_onsets": [A[e[0]]["frame"] for e in ea if e[0] not in sb],
                 "new": [B[k]["frame"] for k in sorted(sb - sa)], "added_episodes": added}
print(json.dumps(res, indent=1))
if a.json:
    open(a.json, "w").write(json.dumps(res, indent=1))
