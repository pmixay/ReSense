"""Attribute the gate rows that differ between the shipped gate (cc6226e) and fb92213 to the F1a completion's new branch.

    change_summary.py <shipped gate work dir> <fb92213 gate work dir> <surface_trace dir> [--margin 0.05]

For every piece the trace covers: rows whose decision word differs (STOP lost / gained, other changes counted), and for
each STOP change the rows of the trace in that frame (and the 3 frames before it: a tracker chain breaks earlier than the
frame where the decision flips) where the new branch rejected a cluster: distance, lateral, size, the cluster's own top
(footprint top), the surface the branch read, and top - surface (rejection needs <= margin). Totals: rejections by the
new branch, their distribution of top - surface, whether the recomputed rule equals the detector's verdict on every
traced cluster (``match``), and whether the traced replay equals the plain gate rows (``plain``: decision, detections,
warnings, every row).
"""
import glob
import json
import os
import sys
from collections import Counter

A, B, T = sys.argv[1:4]
margin = float(sys.argv[sys.argv.index("--margin") + 1]) if "--margin" in sys.argv else 0.05


def word(d):
    h = d.get("health") or {}
    if d["obstacle"]:
        return "STOP"
    if h.get("level") == "error":
        return "FAULT"
    return "CAUTION" if d["warning"] or h.get("decision_level", h.get("level")) == "warn" else "GO"


tot, match_bad, margins, rej_all = Counter(), 0, [], []
for fa in sorted(glob.glob(os.path.join(T, "*.jsonl"))):
    n = os.path.basename(fa)
    stem = n[:-6]
    old = [json.loads(line) for line in open(os.path.join(A, n))]
    new = [json.loads(line) for line in open(os.path.join(B, n))]
    trace = [json.loads(line) for line in open(fa)]
    plain_bad = sum((x["obstacle"], x["warning"], x["detections"], x["warnings"]) != (y["obstacle"], y["warning"], y["detections"], y["warnings"])
                    for x, y in zip(new, trace))
    sfile = [json.loads(line) for line in open(os.path.join(T, stem + ".surface.ndjson"))]
    by_stem = {}
    for r in sfile:
        match_bad += not r["match"]
        by_stem.setdefault(r["stem"], []).append(r)
        if r["surface_rule"]:
            rej_all.append(r)
            margins.append(r["top"] - r["surface"])
    print(f"== {n}: rows {len(new)}, traced run vs plain gate rows differ in {plain_bad}; clusters that reached the new branch {len(sfile)}, "
          f"rejected by it {sum(r['surface_rule'] for r in sfile)}")
    for i, (x, y) in enumerate(zip(old, new)):
        wx, wy = word(x), word(y)
        if wx == wy and (x["detections"], x["warnings"]) == (y["detections"], y["warnings"]):
            continue
        tot[f"{wx}->{wy}"] += 1
        if "STOP" not in (wx, wy):
            continue
        fid = y["frame_id"]
        base, idx = fid.rsplit("_", 1)
        near = []
        for j in range(max(0, i - 3), i + 1):
            f2 = new[j]["frame_id"]
            near += [(f2, r) for r in by_stem.get(f2, []) if r["surface_rule"]]
        print(f"   row {i} {fid}: {wx} -> {wy}; STOP detections old {[(d['distance'], d['lateral']) for d in x['detections']]} new "
              f"{[(d['distance'], d['lateral']) for d in y['detections']]}")
        for f2, r in near:
            print(f"        {f2}: new branch rejected d {r['d']} lat {r['lat']} size {r['size']} top {r['top']} surface {r['surface']} "
                  f"(top - surface {r['top'] - r['surface']:+.3f}) original {r['original']}")
print()
print("decision-word / detection changes in the traced pieces:", dict(tot))
print(f"clusters rejected by the new branch in these pieces: {len(rej_all)}; top - surface: min {min(margins):+.3f} max {max(margins):+.3f}; "
      f"> margin {sum(m > margin + 1e-9 for m in margins)}")
print(f"recomputed rule differs from the detector's verdict on {match_bad} traced clusters")
