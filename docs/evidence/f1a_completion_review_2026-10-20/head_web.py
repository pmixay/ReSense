#!/usr/bin/env python3
"""Reviewer script (own): what do the raw rail-band returns of P4's 98 flipped-cluster snapshots show?

For each snapshot: the rail line nearest the cluster (|dy -+ 0.795| <= 0.10, the model axis), returns within 5 m along
the track, outside the cluster's own extent +-0.3 m; heights h are above the model's rail-head plane.  Prints, per
snapshot and pooled: p10 / p50 / p90 / max of h, the per-bin (0.5 m) maximum (what the F1a median line is built from),
the number of distinct returns, and a pooled histogram (2 cm bins) to see the claimed bimodality (web 0.05-0.11,
head top 0.18-0.23) and how far the model plane is below the head top.

    python head_web.py <extracted trace_fix dir> <out txt>
"""
import json
import sys
from pathlib import Path

import numpy as np

snap, outp = Path(sys.argv[1]), Path(sys.argv[2])
HALF = 0.795
rows, pooled, pooled_max, bins_all = [], [], [], []
for path in sorted(snap.glob("*.fix.ndjson")):
    piece = path.name.removesuffix(".fix.ndjson")
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if not r["A"] or r["D"]:
            continue
        with np.load(snap / f"{piece}_fix" / f"{r['stem']}_{r['k']}.npz") as z:
            X, dy, h = (z[k].astype(float) for k in ("X", "dy", "h"))
        x0, x1 = r["bbox"][0][0], r["bbox"][1][0]
        s = 1.0 if r["lat"] > 0 else -1.0
        m = (np.abs(dy - s * HALF) <= 0.10) & (X > x0 - 5) & (X < x1 + 5) & ((X < x0 - 0.3) | (X > x1 + 0.3))
        m &= (h > -0.3) & (h < 0.6)
        if m.sum() < 3:
            continue
        # distinct returns
        key = {(round(a, 3), round(b, 3)): c for a, b, c in zip(X[m], dy[m], h[m])}
        hv = np.array(list(key.values()))
        xs = np.array([k[0] for k in key])
        b = np.floor((xs - (x0 - 5)) / 0.5).astype(int)
        binmax = np.array([hv[b == q].max() for q in np.unique(b)])
        rows.append((r["stem"], r["k"], r["d"], r["lat"], len(hv), np.percentile(hv, 10), np.median(hv),
                     np.percentile(hv, 90), hv.max(), np.median(binmax), r["ref_orig"], r["top_new"]))
        pooled.extend(hv.tolist())
        pooled_max.append(hv.max())
        bins_all.extend(binmax.tolist())
lines = ["stem k dist lat n_distinct p10 p50 p90 max median_of_bin_max ref_orig(record) top_new(record)"]
for q in rows:
    lines.append("%s %d %5.1f %+5.2f %3d  %+.3f %+.3f %+.3f %+.3f  %+.3f  %s  %.3f" % q)
pooled = np.array(pooled)
lines.append("")
lines.append(f"snapshots {len(rows)}; pooled distinct rail-band returns {pooled.size}")
lines.append("pooled percentiles p5/p25/p50/p75/p95/max: " + " ".join(f"{np.percentile(pooled, p):+.3f}" for p in (5, 25, 50, 75, 95, 100)))
lines.append("per-snapshot max (the 'head top' reading): p10/p50/p90 = " +
             " ".join(f"{np.percentile(pooled_max, p):+.3f}" for p in (10, 50, 90)))
lines.append("per-bin max pooled (F1a line input): p10/p50/p90 = " +
             " ".join(f"{np.percentile(bins_all, p):+.3f}" for p in (10, 50, 90)))
edges = np.arange(-0.30, 0.42, 0.02)
hist, _ = np.histogram(pooled, edges)
lines.append("pooled histogram of h (2 cm bins):")
for lo, c in zip(edges[:-1], hist):
    lines.append(f"  {lo:+.2f}..{lo + 0.02:+.2f} {c:5d} " + "#" * int(60 * c / max(hist.max(), 1)))
outp.write_text("\n".join(lines) + "\n")
print("\n".join(lines[-40:]))
