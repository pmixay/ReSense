#!/usr/bin/env python3
"""Raw points around a reported low cluster (replay.py --trace dump): side view (X, height above the model's
rail-head plane) and top view (X, lateral from the rail axis); the cluster's own points red, the rail laterals
dashed. ``plot_low.py DUMP.npz OUT.png [title]``"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main():
    z = np.load(sys.argv[1])
    X, dy, h, own = z["X"], z["dy"], z["h"], z["own"]
    half = 0.5 * float(z["rails_spacing"])
    x0, x1 = float(z["bbox_min"][0]), float(z["bbox_max"][0])
    fig, ax = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)
    band = np.abs(np.abs(dy) - half) <= 0.10
    ax[0].scatter(X[~own & ~band], h[~own & ~band], s=2, c="0.65", label="other returns")
    ax[0].scatter(X[~own & band], h[~own & band], s=4, c="tab:blue", label="rail bands (|dy| = rails +- 0.1 m)")
    ax[0].scatter(X[own], h[own], s=10, c="red", label="the cluster")
    ax[0].axhline(0.0, color="k", lw=0.6)
    ax[0].axvspan(x0 - 0.3, x1 + 0.3, color="orange", alpha=0.15)
    ax[0].set_ylabel("height above model rail head (m)")
    ax[0].set_ylim(-0.6, 0.6)
    ax[0].legend(loc="upper right", fontsize=7)
    ax[1].scatter(X[~own], dy[~own], s=2, c="0.65")
    ax[1].scatter(X[own], dy[own], s=10, c="red")
    for s in (-half, half):
        ax[1].axhline(s, color="tab:blue", ls="--", lw=0.8)
    ax[1].set_ylabel("lateral from rail axis (m)")
    ax[1].set_xlabel("X along the track (m)")
    fig.suptitle(sys.argv[3] if len(sys.argv) > 3 else sys.argv[1], fontsize=9)
    fig.tight_layout()
    fig.savefig(sys.argv[2], dpi=90)


if __name__ == "__main__":
    main()
