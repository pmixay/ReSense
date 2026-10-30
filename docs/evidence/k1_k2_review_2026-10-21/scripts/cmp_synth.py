#!/usr/bin/env python3
"""Pairs control (base__) and candidate (cand3__) rows of attack_synth.py per scene: STOP frames, false STOP frames
(STOP detections matching no object), true STOP frames per object, first true STOP, curve frames / additions.
    cmp_synth.py <dir> [--json out.json]"""
import glob, json, os, sys
from collections import defaultdict

d = sys.argv[1]
rows = {}
for f in sorted(glob.glob(os.path.join(d, "base__*.jsonl"))):
    name = os.path.basename(f)[6:-6]
    g = os.path.join(d, f"cand3__{name}.jsonl")
    if not os.path.exists(g):
        continue
    A = [json.loads(l) for l in open(f)]
    B = [json.loads(l) for l in open(g)]
    if len(A) != len(B) or not A:
        continue

    def summ(R):
        false_f = [r["frame"] for r in R if any(x["zone"] == "gauge" and x["obj"] is None for x in r["dets"])]
        true_f = [r["frame"] for r in R if any(x["zone"] == "gauge" and x["obj"] is not None for x in r["dets"])]
        first = None
        if true_f:
            r = R[true_f[0]]
            first = round(min(x["distance"] for x in r["dets"] if x["zone"] == "gauge" and x["obj"] is not None), 1)
        return dict(stop=sum(r["stop"] for r in R), false=false_f, true=true_f, first=first,
                    curve=sum(r["curve"] for r in R), added=sum(r["added"] for r in R))
    a, b = summ(A), summ(B)
    obj_pts = [r["obj_pts"] for r in A]
    rows[name] = dict(control=a, cand=b, lost_true=sorted(set(a["true"]) - set(b["true"])),
                      new_true=sorted(set(b["true"]) - set(a["true"])),
                      new_false=sorted(set(b["false"]) - set(a["false"])),
                      gone_false=sorted(set(a["false"]) - set(b["false"])),
                      objpts_first_last=[obj_pts[0], obj_pts[-1]])
print(f"{'scene':28s} {'ctl STOP/false/true/first':>28s} {'cand STOP/false/true/first':>28s}  lost_true new_false new_true  curve/added")
for n, r in rows.items():
    a, b = r["control"], r["cand"]
    fl = lambda s: f"{s['stop']:3d}/{len(s['false']):3d}/{len(s['true']):3d}/{s['first']}"
    flag = "LOSS " if r["lost_true"] or (a["first"] and (b["first"] is None or b["first"] < a["first"] - 0.01)) else ""
    flag += "FALSE+" if r["new_false"] else ""
    print(f"{n:28s} {fl(a):>28s} {fl(b):>28s}  {len(r['lost_true']):3d} {len(r['new_false']):3d} {len(r['new_true']):3d}  {b['curve']}/{b['added']} {flag}")
if len(sys.argv) > 3 and sys.argv[2] == "--json":
    json.dump(rows, open(sys.argv[3], "w"), indent=1)
