#!/usr/bin/env python3
"""Reviewer script (own): why does the candidate NOT reject 13 of the 98 archived flips?  Reason codes derived
from the raw snapshot with my own reading of the rule (not by calling the production function):
  wide        bbox width > 0.45 (rail_start_max_width)
  not_rail    lateral interval [d0, d1] does not reach |dy| = 0.795 +- 0.10
  no_side     no low-free band return in (x0-5, x0-0.3) or in (x1+0.3, x1+5)
  one_return  the highest low-free return has < 2 distinct returns within 0.05 of it
  top_above   top - S > 0.05 (the cluster sticks out above the surface)
  rejected    would be rejected (S exists and top <= S + 0.05)
Cross-check: my 'rejected' set must equal the production replay's rejected set (snap_pad_wt_cand.json).

    python classify_kept.py <trace_fix dir> <snap_pad_wt_cand.json>
"""
import json
import sys
from pathlib import Path

import numpy as np

snap = Path(sys.argv[1])
cand = {(r["stem"], r["k"]): r for r in json.load(open(sys.argv[2]))["rows"]}
HALF, TOL = 0.795, 0.10
counts, mism = {}, []
for path in sorted(snap.glob("*.fix.ndjson")):
    piece = path.name.removesuffix(".fix.ndjson")
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if not r["A"] or r["D"]:
            continue
        with np.load(snap / f"{piece}_fix" / f"{r['stem']}_{r['k']}.npz") as z:
            X, dy, h, own, free = (z[k] for k in ("X", "dy", "h", "own", "free"))
        X, dy, h = X.astype(float), dy.astype(float), h.astype(float)
        d0, d1 = dy[own].min(), dy[own].max()
        x0, x1 = r["bbox"][0][0], r["bbox"][1][0]
        top = r["top_new"]
        if r["size"][1] > 0.45:
            code = "wide"
        elif not any(d0 <= s * HALF + TOL and d1 >= s * HALF - TOL for s in (-1, 1)):
            code = "not_rail"
        else:
            band = free & (dy >= d0) & (dy <= d1) & (h > -0.3) & (h < 0.35)
            before = band & (X > x0 - 5) & (X < x0 - 0.3)
            after = band & (X > x1 + 0.3) & (X < x1 + 5)
            win = band & (X > x0 - 5) & (X < x1 + 5)
            if not before.any() or not after.any():
                code = "no_side"
            else:
                key = {(round(a, 3), round(b, 3)): c for a, b, c in zip(X[win], dy[win], h[win])}
                v = np.array(list(key.values()))
                S = v.max()
                if (v >= S - 0.05).sum() < 2:
                    code = "one_return"
                elif top <= S + 0.05:
                    code = "rejected"
                else:
                    code = "top_above"
        counts[code] = counts.get(code, 0) + 1
        prod = cand[(r["stem"], r["k"])]["rejected"]
        if (code == "rejected") != prod:
            mism.append((r["stem"], r["k"], code, prod))
        if code != "rejected":
            print(f"{r['stem']}:{r['k']} d={r['d']} lat={r['lat']} w={r['size'][1]} top={top} -> {code}")
print(counts)
print("mismatches between my classification and the production replay:", mism)
