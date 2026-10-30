#!/usr/bin/env python3
"""Pictures of clusters the bounded branch rejected (trace_piece.py TRACE_DUMP=1 dumps): for each dump, a side view
(X vs height above the model plane) of the returns in the cluster's own rail band (|dy - rail line| <= 0.10) and of
the other rail's band, with the cluster's own points, its footprint returns and its bbox; and a top view (X vs dy).
    python plot_rejections.py <dump dir> <out dir> [max pictures]"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HALF = 0.795
src, dst = sys.argv[1], sys.argv[2]
cap = int(sys.argv[3]) if len(sys.argv) > 3 else 40
os.makedirs(dst, exist_ok=True)
for f in sorted(glob.glob(os.path.join(src, "*.npz")))[:cap]:
    d = np.load(f)
    X, dy, h, own, free, bb = d["X"], d["dy"], d["h"], d["own"], d["free"], d["bbox"]
    s = 1.0 if (bb[1] + bb[4]) > 0 else -1.0
    foot = (X >= bb[0]) & (X <= bb[3]) & (dy >= bb[1]) & (dy <= bb[4]) & (h < 0.35)
    fig, ax = plt.subplots(3, 1, figsize=(9, 9))
    for a, line, title in ((ax[0], s * HALF, "own rail band"), (ax[1], -s * HALF, "other rail band")):
        band = np.abs(dy - line) <= 0.10
        a.scatter(X[band & free], h[band & free], s=6, c="tab:blue", label="free returns")
        a.scatter(X[band & ~free], h[band & ~free], s=6, c="tab:gray", label="in a low footprint")
        if title.startswith("own"):
            a.scatter(X[foot], h[foot], s=18, facecolors="none", edgecolors="tab:red", label="cluster footprint")
            a.scatter(X[own], h[own], s=10, c="tab:red", label="cluster points")
            a.axvspan(bb[0] - 0.3, bb[3] + 0.3, color="tab:red", alpha=0.08)
        a.set_title(f"{title} (line {line:+.3f}); h above the model rail-head plane")
        a.set_xlim(bb[0] - 6, bb[3] + 6)
        a.set_ylim(-0.35, 0.45)
        a.grid(alpha=0.3)
        a.legend(fontsize=7, loc="upper right")
    ax[2].scatter(X, dy, s=3, c=np.clip(h, -0.3, 0.4), cmap="viridis")
    ax[2].scatter(X[own], dy[own], s=10, c="tab:red")
    ax[2].set_xlim(bb[0] - 6, bb[3] + 6)
    ax[2].set_ylabel("dy (m)")
    ax[2].set_xlabel("X along the track (m)")
    ax[2].set_title("top view, colour = height")
    fig.suptitle(os.path.basename(f))
    fig.tight_layout()
    fig.savefig(os.path.join(dst, os.path.basename(f).replace(".npz", ".png")), dpi=80)
    plt.close(fig)
print("pictures in", dst)
