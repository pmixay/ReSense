#!/usr/bin/env python3
"""Rows of one set F sequence (kind, file) in several setF_straight.json: d, n points, cand, hit, gt vehicle Y.
setf_seq.py <kind> <file> <dmin> <dmax> A.json B.json ..."""
import json, sys
kind, fil, dmin, dmax = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
runs = [json.load(open(p)) for p in sys.argv[5:]]
seqs = []
for r in runs:
    s = [s for s in r["sequences"] if s["kind"] == kind and s["rows"][0]["frame"].split("_")[2] == fil][0]
    seqs.append(s)
print("firsts", [s["first"] for s in seqs])
for i, row in enumerate(seqs[0]["rows"]):
    if not dmin <= row["d"] <= dmax:
        continue
    parts = []
    for s in seqs:
        r = s["rows"][i]
        assert r["frame"] == row["frame"]
        parts.append(f"n{r['n']:3d} c{int(bool(r['cand']))} h{int(bool(r['hit']))} y{r['gt_vehicle_y_m']:+6.2f} ax{r['axis_error_m']:+5.2f}")
    print(f"{row['frame']} d{row['d']:6.1f} | " + " | ".join(parts))
