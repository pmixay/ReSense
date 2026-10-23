#!/usr/bin/env python3
"""Revision-2 design study on the ride (design set): for every cluster the r1 branch rejected on the ride /
doubleT_platform (trace_piece.py dumps: all returns within 6 m along, |dy| < 1.7, -0.6 < h < 0.6), compute
  * H (r1 rail_head_top on the dumped low-free returns) and the four region maxima,
  * own-rail level (min of own before/after) vs other-rail level (min of other before/after),
  * the highest return in the cluster's lateral extent [d0, d1] over [x0 - 0.3, x1 + E] (E = 1, 2, 3, 5 m), minus H.
    python ride_extent.py <dump dir>"""
import glob, sys
import numpy as np
HALF = 0.795
rows = []
for f in sorted(glob.glob(sys.argv[1] + "/*.npz")):
    d = np.load(f); X, dy, h, own, free, bb = d["X"].astype(float), d["dy"], d["h"], d["own"], d["free"], d["bbox"]
    x0, x1 = bb[0], bb[3]; dd = dy[own]; d0, d1 = dd.min(), dd.max(); xc = 0.5 * (x0 + x1)
    s = [t for t in (-1.0, 1.0) if d0 <= t * HALF + 0.1 and d1 >= t * HALF - 0.1][0]
    ok = free & (h > -0.3) & (h < 0.35)
    o = ok & (np.abs(dy - s * HALF) <= 0.1); q = ok & (np.abs(dy + s * HALF) <= 0.1)
    mx = lambda m, lo, hi: float(h[m & (X >= lo) & (X <= hi)].max())
    r = [mx(o, x0 - 5, x0 - .3), mx(o, x1 + .3, x1 + 5), mx(q, x0 - 5, xc), mx(q, xc, x1 + 5)]
    H = min(r)
    lat = (dy >= d0) & (dy <= d1) & (h < 1.5)
    ext = {E: float(h[lat & (X >= x0 - .3) & (X <= x1 + E)].max()) - H for E in (1, 2, 3, 5)}
    lat5 = (dy >= d0 - 0.05) & (dy <= d1 + 0.05) & (h < 1.5)
    ext5 = float(h[lat5 & (X >= x0 - .3) & (X <= x1 + 2)].max()) - H
    rows.append((f.split("/")[-1], H, min(r[:2]) - min(r[2:]), ext, ext5))
    print(f"{f.split('/')[-1]:32s} H {H:.3f} own-other {min(r[:2]) - min(r[2:]):+.3f} ext-H " +
          " ".join(f"E{E} {v:+.3f}" for E, v in ext.items()) + f" | widened E2 {ext5:+.3f}")
a = np.array([[r[2]] + [r[3][E] for E in (1, 2, 3, 5)] + [r[4]] for r in rows])
print("|own-other| p50 %.3f p90 %.3f max %.3f" % tuple(np.percentile(np.abs(a[:, 0]), [50, 90, 100])))
for j, E in enumerate((1, 2, 3, 5)):
    print(f"E{E}: ext-H p50 {np.percentile(a[:, j+1], 50):+.3f} p90 {np.percentile(a[:, j+1], 90):+.3f} max {a[:, j+1].max():+.3f}; "
          f"<= 0.03: {(a[:, j+1] <= 0.03).sum()}/{len(a)}  <= 0.04: {(a[:, j+1] <= 0.04).sum()}")
