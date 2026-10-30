"""Margin of the bed-lost criterion (excess <= 0: no fire) from the author's committed traces (own aggregation).
usage: bed_margin.py <pandar trace_bed dir> <falcon final x.jsonl.xz>"""
import glob, json, lzma, os, sys
import numpy as np
d, fx = sys.argv[1], sys.argv[2]
tot = ev = 0
for f in sorted(glob.glob(d + "/*.jsonl")):
    v = [json.loads(l)["bed_excess"] for l in open(f)]; w = np.array([x for x in v if x is not None]); tot += len(v); ev += len(w)
    print(f"{os.path.basename(f)[:-6]:38s} frames={len(v):5d} evaluated(mount final)={len(w):5d} max_excess={w.max():7.3f}  fires={(w>0).sum()}")
print("Pandar total frames", tot, "evaluated", ev)
x = [json.loads(l) for l in lzma.open(fx, "rt")]
v = [(i, r["bed_excess"]) for i, r in enumerate(x) if r["bed_excess"] is not None]
print("Falcon evaluated", len(v), "first evaluated frame", v[0][0], "fires", sum(e > 0 for _, e in v), "rows", [i for i, e in v if e > 0][0], "-", [i for i, e in v if e > 0][-1])
print("Falcon outside the run, max excess", max(e for i, e in v if e <= 0), "; rows within 0.3 m of firing:", sum(e > -0.3 for _, e in v if e <= 0))
