#!/usr/bin/env python3
"""Amendment-1 design check on B1's real ride states: does a rail fragment's footprint show a sensor-facing column
(a return below a top-surface return at the same x and dy, |dx| <= DX, |ddy| <= DDY, dh in [0.03, 0.30])?
Printed per B1-flipped eligible cluster.  python facing.py <snapshot dir> <audit json>"""
import json, sys
from pathlib import Path
import numpy as np
snaps, audit = Path(sys.argv[1]), json.loads(Path(sys.argv[2]).read_text())
for DX, DDY in ((0.05, 0.02), (0.05, 0.03), (0.10, 0.03)):
    hits, n, ex = 0, 0, []
    for r in audit["rows"]:
        if r["candidate_weak"]:
            continue
        d = np.load(snaps / f"frame_{r['frame']:05d}.npz")
        X, dy, h = d["X"].astype(float), d["dy"], d["h"]
        st, idx = d[f"state_{r['cluster']}"], d[f"idx_{r['cluster']}"]
        dd = dy[idx]
        if dd.max() - dd.min() > 0.45 or abs(abs(float(st[6])) - 0.795) > 0.25:
            continue
        foot = (X >= st[0]) & (X <= st[3]) & (dy >= dd.min()) & (dy <= dd.max()) & (h < 0.35)
        top = float(h[foot].max())
        T = np.flatnonzero(foot & (h >= top - 0.02)); F = np.flatnonzero(foot)
        face = any(((np.abs(X[F] - X[t]) <= DX) & (np.abs(dy[F] - dy[t]) <= DDY) & (h[t] - h[F] >= 0.03)
                    & (h[t] - h[F] <= 0.30)).any() for t in T)
        n += 1; hits += face
        if face:
            ex.append(f"{r['frame']}c{r['cluster']}")
    print(f"dx {DX} ddy {DDY}: facing column in {hits}/{n} eligible flips {ex}")
