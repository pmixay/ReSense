"""Pictures for the F1a fix acceptance: the clusters the old rule made weak and the fix lets through (flips) that a
track of the candidate run was matched with, from f1a_fix_trace.py's records and dumps.

One figure per (piece, track id, last row): up to --max of the track's flipped hits up to that row (the last ones),
one row of two panels each. Left: top view (along-track X vs corridor lateral dy) of the dumped returns coloured by
height above the model's rail head (h), the cluster's own returns ringed red, the other returns of its footprint
(the box the new top is read from) marked black. Right: side view (X vs h) of the returns within the cluster's lateral
range +- 0.3 m, the same marks, and the levels: old reference (blue), independent reference (green dashed), old top
(red dotted), new top (black dotted).

    python f1a_fix_plot.py <trace dir> <png> <piece> <track id> <row> [--max 4]
"""
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

tr, png, piece, tid, row = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 4
tracks = [json.loads(line) for line in open(os.path.join(tr, piece + ".tracks.ndjson"))]
recs = {}
for line in open(os.path.join(tr, piece + ".fix.ndjson")):
    r = json.loads(line)
    recs[(r["stem"], r["k"])] = r
hits = [(j, t) for j in range(row + 1) for t in tracks[j]["tracks"] if t[0] == tid and t[7] and t[7][3]]
hits = hits[-mx:]
if not hits:
    sys.exit(f"track {tid} has no flipped hit up to row {row}")
fig, axes = plt.subplots(len(hits), 2, figsize=(13, 3.6 * len(hits)), squeeze=False)
for (j, t), (a0, a1) in zip(hits, axes):
    stem, k = tracks[j]["stem"], t[7][0]
    r = recs[(stem, k)]
    z = np.load(os.path.join(tr, piece + "_fix", f"{stem}_{k}.npz"))
    X, dy, h, own, fp = z["X"], z["dy"], z["h"], z["own"], z["fp"]
    (x0, y0, _), (x1, y1, _) = r["bbox"]
    sc = a0.scatter(X, dy, c=np.clip(h, -0.1, 0.4), s=3, cmap="viridis", vmin=-0.1, vmax=0.4)
    a0.scatter(X[fp & ~own], dy[fp & ~own], s=14, marker="x", c="k", lw=0.8, label="footprint, not in cluster")
    a0.scatter(X[own], dy[own], s=30, facecolors="none", edgecolors="r", lw=1.0, label="cluster")
    a0.set_xlabel("X (m)")
    a0.set_ylabel("corridor lateral dy (m)")
    a0.set_ylim(-1.6, 1.6)
    for s in (-0.76, 0.76):
        a0.axhline(s, color="0.6", lw=0.5, ls=":")
    a0.set_title(f"{piece} row {j} {stem}: track {tid}, cluster {k} at {r['d']} m, lat {r['lat']:+.2f}, "
                 f"cause {r['cause']}", fontsize=8)
    a0.legend(fontsize=6, loc="upper right")
    fig.colorbar(sc, ax=a0, label="h (m)")
    d = dy[own]
    m = (dy >= d.min() - 0.3) & (dy <= d.max() + 0.3)
    a1.scatter(X[m], h[m], s=3, c="0.5")
    a1.scatter(X[m & fp & ~own], h[m & fp & ~own], s=14, marker="x", c="k", lw=0.8)
    a1.scatter(X[own], h[own], s=30, facecolors="none", edgecolors="r", lw=1.0)
    for v, c, ls, lab in ((r["ref_orig"], "b", "-", "old reference"), (r["ref_ind"], "g", "--", "independent ref."),
                          (r["top_old"], "r", ":", "old top"), (r["top_new"], "k", ":", "new top")):
        if v is not None:
            a1.axhline(v, color=c, ls=ls, lw=1.0, label=f"{lab} {v:.3f}")
    a1.axvspan(x0, x1, color="orange", alpha=0.15)
    a1.set_ylim(-0.15, 0.45)
    a1.set_xlabel("X (m)")
    a1.set_ylabel("h (m)")
    a1.legend(fontsize=6, loc="upper right")
    a1.set_title(f"returns within the cluster's lateral range +- 0.3 m; footprint X {x0:.2f}-{x1:.2f} shaded", fontsize=8)
fig.tight_layout()
fig.savefig(png, dpi=90)
print(png, [(j, tracks[j]["stem"], t[7][0]) for j, t in hits])
