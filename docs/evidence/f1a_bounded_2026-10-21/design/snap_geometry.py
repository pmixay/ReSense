#!/usr/bin/env python3
"""Design study (own code, no detector import): rail-head geometry around the low clusters that the pre-repair
F1a rule rejected in B1's 250 captured real ride states (f1a_b1_2026-10-20/raw-evidence.tar.gz,
f1a-b1-compact-snapshots). Per cluster: the uncapped footprint top (B1's `full_top`), the rail line it reaches,
the head-top estimate of that rail BEFORE and AFTER the cluster's own along-track extent (per 0.5 m bin maxima,
guard 0.3 m, window 5 m), and the OTHER rail's head top over the same x-range.

    python snap_geometry.py <compact snapshot dir> <compact audit json> --out geometry.json
"""
import argparse
import json
from pathlib import Path

import numpy as np

HALF, BAND, W, G, FOOT_MAX = 0.795, 0.10, 5.0, 0.3, 0.35


def bins(X, h, lo, hi, step=0.5):
    m = (X >= lo) & (X < hi)
    if not m.any():
        return np.zeros(0), np.zeros(0)
    b = np.floor((X[m] - lo) / step).astype(int)
    top = np.full(b.max() + 1, -np.inf)
    np.maximum.at(top, b, h[m])
    ok = np.isfinite(top)
    return lo + step * (np.flatnonzero(ok) + 0.5), top[ok]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snaps", type=Path)
    ap.add_argument("audit", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    audit = json.loads(a.audit.read_text())
    rows = []
    for r in audit["rows"]:
        d = np.load(a.snaps / f"frame_{r['frame']:05d}.npz")
        X, dy, h = d["X"].astype(float), d["dy"], d["h"]
        s = d[f"state_{r['cluster']}"]
        idx = d[f"idx_{r['cluster']}"]
        x0, x1 = float(s[0]), float(s[3])
        dd = dy[idx]
        foot = (X >= x0) & (X <= x1) & (dy >= dd.min()) & (dy <= dd.max()) & (h < FOOT_MAX)
        full_top = max(float(s[7]), float(h[foot].max())) if foot.any() else float(s[7])
        side = 1.0 if float(s[6]) > 0 else -1.0
        out = dict(frame=r["frame"], cluster=r["cluster"], x0=round(x0, 2), x1=round(x1, 2),
                   lateral=round(float(s[6]), 3), width=round(float(dd.max() - dd.min()), 3),
                   capped_top=round(float(s[7]), 3), full_top=round(full_top, 3),
                   original_ref=r["original_ref"], b1_kept=not r["candidate_weak"])
        for name, sd in (("own", side), ("other", -side)):
            band = (np.abs(dy - sd * HALF) <= BAND) & (h > -0.3) & (h < FOOT_MAX)
            if name == "own":
                xb, tb = bins(X[band], h[band], x0 - W, x0 - G)
                xa, ta = bins(X[band], h[band], x1 + G, x1 + W)
                out["before_bins"] = [[round(float(u), 2), round(float(v), 3)] for u, v in zip(xb, tb)]
                out["after_bins"] = [[round(float(u), 2), round(float(v), 3)] for u, v in zip(xa, ta)]
                xf, tf = bins(X[band], h[band], x0 - G, x1 + G)
                out["foot_bins"] = [[round(float(u), 2), round(float(v), 3)] for u, v in zip(xf, tf)]
            else:
                xo, to = bins(X[band], h[band], x0 - W, x1 + W)
                out["other_bins"] = [[round(float(u), 2), round(float(v), 3)] for u, v in zip(xo, to)]
        rows.append(out)
    a.out.write_text(json.dumps(rows, indent=1) + "\n")
    print(len(rows), "rows")


if __name__ == "__main__":
    main()
