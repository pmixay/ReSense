#!/usr/bin/env python3
"""Amendment-2 design check on the ride (design set dumps): lateral spread of the top surface measured over the
object-extent region (lateral extent + 0.05, x0 - 0.3 .. x1 + 1.0) instead of the strict footprint box: returns
within BAND of the region's highest return (h < 1.5).   python ride_spread_ext.py <dump dir>"""
import glob, sys
import numpy as np
for band in (0.01, 0.02):
    sp = []
    for f in sorted(glob.glob(sys.argv[1] + "/*.npz")):
        d = np.load(f); X, dy, h, own, bb = d["X"].astype(float), d["dy"], d["h"], d["own"], d["bbox"]
        dd = dy[own]
        ext = (X >= bb[0] - .3) & (X <= bb[3] + 1.0) & (dy >= dd.min() - .05) & (dy <= dd.max() + .05) & (h < 1.5)
        top = h[ext].max(); s = ext & (h >= top - band)
        sp.append(float(dy[s].max() - dy[s].min()))
    sp = np.array(sp)
    print(f"band {band}: spread p50 {np.median(sp):.3f} p90 {np.percentile(sp, 90):.3f} max {sp.max():.3f}; "
          f"<= 0.10: {(sp <= 0.10).sum()}/{sp.size}", sorted(np.round(sp, 3)))
