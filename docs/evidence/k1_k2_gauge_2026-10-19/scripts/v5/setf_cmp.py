#!/usr/bin/env python3
"""Per-sequence set F straight comparison of two (or more) setF_straight.json files.
setf_cmp.py A.json B.json [C.json ...]  -> per sequence: kind, file, lateral, first per run; and per run the
frame-to-frame jitter of the placed object's vehicle Y (gt_vehicle_y_m) at 100-200 m, monitored range 'mon' median"""
import json, sys
import numpy as np
runs = [json.load(open(p)) for p in sys.argv[1:]]
seqs = [r["sequences"] for r in runs]
print("kind     file lat    | first per run | mon p50 (frames d 100-200) | |dY| frame-to-frame p50/p90 at 100-200 m | n>0 frames 100-200")
for i, s0 in enumerate(seqs[0]):
    f0 = s0["rows"][0]["frame"].split("_")[2]
    firsts = [s[i]["first"] for s in seqs]
    line = f"{s0['kind']:8s} {f0:4s} {s0['lateral']:+.2f} | " + " ".join(f"{(x if x is not None else float('nan')):6.1f}" for x in firsts)
    mons, jit, npts = [], [], []
    for s in seqs:
        assert s[i]["kind"] == s0["kind"] and abs(s[i]["lateral"] - s0["lateral"]) < 1e-9
        rows = [r for r in s[i]["rows"] if 100 <= r["d"] <= 200]
        mons.append(np.median([r["mon"] for r in rows]) if rows else float("nan"))
        y = np.array([r["gt_vehicle_y_m"] for r in rows])
        dy = np.abs(np.diff(y)) if y.size > 1 else np.array([np.nan])
        jit.append((np.median(dy), np.percentile(dy, 90)))
        npts.append(sum(r["n"] > 0 for r in rows))
    line += " | " + " ".join(f"{m:6.1f}" for m in mons) + " | " + " ".join(f"{a:.2f}/{b:.2f}" for a, b in jit) + " | " + " ".join(str(n) for n in npts)
    print(line)
