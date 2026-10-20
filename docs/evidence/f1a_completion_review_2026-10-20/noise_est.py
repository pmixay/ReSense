#!/usr/bin/env python3
"""Reviewer script (own): estimate from the 98 real snapshots the quantities the 'invisible band' depends on.

For each snapshot (the cluster's own lateral band [dy_min, dy_max], low-free returns, h < 0.35, within +-5 m of the
cluster, i.e. what ``_rail_surface_reference`` reads):
  S            = highest low-free return (the candidate's surface),
  n_near       = number of distinct returns within 0.05 m of S (the rule needs >= 2),
  n_window     = number of distinct returns in the window,
  sd_top       = standard deviation of the returns within 0.05 m of S (a measure of the local scatter of the head
                 top, includes any slope/model error over +-5 m, so an upper bound of the pure noise),
  gap2         = S minus the second-highest distinct return (how much the maximum sticks out).
Prints distributions.  Used to choose realistic parameters for the noise Monte Carlo of unit_controls.py.

    python noise_est.py <trace_fix dir> <replay cand json>
"""
import json
import sys
from pathlib import Path

import numpy as np

snap = Path(sys.argv[1])
cand = {(r["stem"], r["k"]): r for r in json.load(open(sys.argv[2]))["rows"]}
rows = []
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
        m = free & (dy >= d0) & (dy <= d1) & (h > -0.3) & (h < 0.35) & (X > x0 - 5) & (X < x1 + 5)
        key = {(round(a, 3), round(b, 3)): c for a, b, c in zip(X[m], dy[m], h[m])}
        v = np.array(sorted(key.values(), reverse=True))
        if v.size < 2:
            continue
        S = v[0]
        near = v[v >= S - 0.05]
        xv = np.array([k[0] for k in key])
        hv = np.array(list(key.values()))
        b = np.floor(xv - (x0 - 5)).astype(int)
        ub = np.unique(b)
        slope = float("nan")
        if ub.size >= 4:
            bx = np.array([xv[b == q].mean() for q in ub])
            bm = np.array([hv[b == q].max() for q in ub])
            head_bins = bm >= S - 0.08          # only bins in which a ring actually hit the head surface
            if head_bins.sum() >= 3:
                slope = float(np.polyfit(bx[head_bins], bm[head_bins], 1)[0])
        rows.append(dict(stem=r["stem"], k=r["k"], slope=slope, S=S, n_near=int(near.size), n_window=int(v.size),
                         sd_top=float(near.std()), gap2=float(v[0] - v[1]),
                         surface_cand=cand[(r["stem"], r["k"])]["surface"]))
arr = lambda key: np.array([q[key] for q in rows])  # noqa: E731
print("snapshots", len(rows))
for key in ("S", "n_near", "n_window", "sd_top", "gap2"):
    a = arr(key)
    print(f"{key:9s} min {a.min():.3f} p10 {np.percentile(a, 10):.3f} p50 {np.percentile(a, 50):.3f} "
          f"p90 {np.percentile(a, 90):.3f} max {a.max():.3f}")
sl = arr("slope")
sl = sl[np.isfinite(sl)]
print(f"slope of the head-hit per-metre maxima (bins within 0.08 of S, >= 3 bins) along the track (m/m), n={sl.size}: p10 {np.percentile(sl, 10):+.4f} "
      f"p50 {np.percentile(sl, 50):+.4f} p90 {np.percentile(sl, 90):+.4f}; |slope| p50 {np.percentile(abs(sl), 50):.4f} "
      f"p90 {np.percentile(abs(sl), 90):.4f} max {abs(sl).max():.4f}; share |slope| >= 0.01: {(abs(sl) >= 0.01).mean():.2f}")
S = arr("S")
print("S >= 0.28:", int((S >= 0.28).sum()), " S >= 0.30 (S+0.05 >= foot_max_top 0.35):", int((S >= 0.30).sum()))
agree = sum(1 for q in rows if q["surface_cand"] is not None and abs(q["surface_cand"] - q["S"]) < 1e-3)
print("my S equals the production function's surface in", agree, "of", sum(q["surface_cand"] is not None for q in rows),
      "snapshots where the production function returned a surface")
print("snapshots where the production function returned None:", sum(q["surface_cand"] is None for q in rows),
      [(q["stem"], q["k"], q["n_near"], round(q["S"], 3)) for q in rows if q["surface_cand"] is None])
json.dump(rows, open(Path(sys.argv[0]).resolve().parent / "out" / "noise_est.json", "w"), indent=1)
