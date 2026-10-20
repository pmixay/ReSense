#!/usr/bin/env python3
"""Reviewer script (own): draw the raw returns of archived flipped-cluster snapshots.

Per snapshot a panel of the returns in the cluster's own lateral band [dy_min, dy_max] (the band the new rule reads),
x = along-track relative to the cluster's start, y = height h above the model's rail-head plane:
  red = the cluster's own points, orange = other points inside its footprint, blue = low-free points (what the new
  rule may use), grey = returns excluded by the low-free mask.
Lines: dashed red = capped top (height_max), solid red = uncapped footprint top, dashed green = original median
reference, blue solid = the head surface the candidate reads, blue dotted = surface + rail_start_margin (0.05).
The decisions come from the replays (snap_pad_*.json).

    python plot_snap.py <trace_fix dir> <replay cand json> <replay parent json> <out png> <stem:k> [<stem:k> ...]
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

snap, fcand, fpar, outp = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
args = []
for a in sys.argv[5:]:
    args += Path(a).read_text().split() if a.endswith(".txt") else [a]
want = [tuple(a.split(":")) for a in args]
cand = {(r["stem"], r["k"]): r for r in json.load(open(fcand))["rows"]}
par = {(r["stem"], r["k"]): r for r in json.load(open(fpar))["rows"]}
n = len(want)
cols = min(4, n)
rows_n = int(np.ceil(n / cols))
fig, axes = plt.subplots(rows_n, cols, figsize=(4.6 * cols, 3.2 * rows_n), squeeze=False)
for ax in axes.ravel():
    ax.axis("off")
for ax, (stem, ks) in zip(axes.ravel(), want):
    ax.axis("on")
    k = int(ks)
    piece = None
    for p in snap.glob("*.fix.ndjson"):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r["stem"] == stem and r["k"] == k:
                piece, row = p.name.removesuffix(".fix.ndjson"), r
    with np.load(snap / f"{piece}_fix" / f"{stem}_{k}.npz") as z:
        X, dy, h, own, fp, free = (z[q] for q in ("X", "dy", "h", "own", "fp", "free"))
    X, dy, h = X.astype(float), dy.astype(float), h.astype(float)
    d0, d1 = dy[own].min(), dy[own].max()
    x0 = row["bbox"][0][0]
    band = (dy >= d0) & (dy <= d1) & (h > -0.3) & (h < 0.6)
    for sel, col, lab in ((band & ~free & ~fp, "lightgrey", "excluded (low footprints)"),
                          (band & free, "tab:blue", "low-free"),
                          (band & fp & ~own, "tab:orange", "footprint"),
                          (band & own, "tab:red", "cluster")):
        ax.scatter(X[sel] - x0, h[sel], s=7, c=col, label=lab, zorder=3 if col != "lightgrey" else 1)
    c = cand[(stem, k)]
    ax.axhline(row["top_old"], color="tab:red", ls="--", lw=0.8)
    ax.axhline(row["top_new"], color="tab:red", lw=1.0)
    if row["ref_orig"] is not None:
        ax.axhline(row["ref_orig"], color="tab:green", ls="--", lw=0.8)
    if c["surface"] is not None:
        ax.axhline(c["surface"], color="tab:blue", lw=1.0)
        ax.axhline(c["surface"] + 0.05, color="tab:blue", ls=":", lw=1.0)
    ax.set_xlim(-5.5, 7.5)
    ax.set_ylim(-0.32, 0.40)
    ax.set_title(f"{stem}:{k} d={row['d']} lat={row['lat']} w={row['size'][1]}\n"
                 f"cand rej={c['rejected']} parent rej={par[(stem, k)]['rejected']} "
                 f"top={row['top_new']} S={None if c['surface'] is None else round(c['surface'], 3)}", fontsize=7)
    ax.tick_params(labelsize=6)
axes.ravel()[0].legend(fontsize=5, loc="lower right")
fig.tight_layout()
fig.savefig(outp, dpi=110)
print("wrote", outp)
