#!/usr/bin/env python3
"""Reviewer script: why does the replay of new_data_52_0016 k=1 differ from the P4 trace (footprint top 0.163)?"""
import json
import sys
from pathlib import Path

import numpy as np

snap = Path(sys.argv[1])
rows = [json.loads(l) for l in (snap / "new_data_1.fix.ndjson").read_text().splitlines()]
row = [r for r in rows if r["stem"] == "new_data_52_0016" and r["k"] == 1][0]
print(row)
with np.load(snap / "new_data_1_fix" / "new_data_52_0016_1.npz") as z:
    X, dy, h, own, fp = (z[k].astype(np.float64) if k in ("X", "dy", "h") else z[k] for k in ("X", "dy", "h", "own", "fp"))
d = dy[own]
b0, b1 = row["bbox"]
for pad in (0.0, 0.0005, 0.001):
    f = (X >= b0[0] - pad) & (X <= b1[0] + pad) & (dy >= d.min()) & (dy <= d.max()) & (h < 0.35)
    print("pad", pad, "footprint n", int(f.sum()), "top", float(h[f].max()) if f.any() else None)
print("archived fp mask n", int(fp.sum()), "top", float(h[fp].max()))
print("own X range", X[own].min(), X[own].max(), "bbox x", b0[0], b1[0])
idx = np.flatnonzero(fp)
for i in idx[np.argsort(-h[idx])][:6]:
    print("fp point X=%.4f dy=%.4f h=%.4f own=%s" % (X[i], dy[i], h[i], bool(own[i])))
