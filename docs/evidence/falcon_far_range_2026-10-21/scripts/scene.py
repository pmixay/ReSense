#!/usr/bin/env python3
"""Raw static far scene in the track reference (falcon_long_range_2026-10-19/track_reference.json):
top / side / front views over a frame range. Raw points only, no detector output.

    scene.py --frames 3800:4440:8 --out figs/scene_late.png [--cache /data/falcon] [--xr 40:330]
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

LR = Path(__file__).resolve().parents[2] / "falcon_long_range_2026-10-19"
TR = json.loads((LR / "track_reference.json").read_text())["track"]


def load(cache, frames):
    P = [np.load(f"{cache}/f_{i:05d}.npz")["xyz"] for i in frames]
    xyz = np.vstack(P).astype(np.float64)
    x, y, z = xyz.T
    return x, y - (TR["a"] + TR["b"] * x), z - (TR["z0"] + TR["c"] * x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/data/falcon")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--xr", default="40:330")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    lo, hi, st = (int(v) for v in a.frames.split(":"))
    x0, x1 = (float(v) for v in a.xr.split(":"))
    x, lat, h = load(a.cache, range(lo, hi, st))
    fig, ax = plt.subplots(3, 1, figsize=(16, 14))
    m = (x > x0) & (x < x1) & (np.abs(lat) < 8) & (h > -1) & (h < 6)
    ax[0].scatter(x[m], lat[m], s=0.3, c=np.clip(h[m], -1, 5), cmap="viridis")
    ax[0].set_title(f"top view, track reference, frames {a.frames}, colour = height (-1..5 m)")
    for v in (1.05, -1.05, 1.2, -1.2, 4.0, -4.0):
        ax[0].axhline(v, c="r", lw=.4)
    ax[0].set_ylabel("lateral m (+ left)")
    ax[0].set_xticks(np.arange(x0, x1 + 1, 10))
    ax[0].grid(alpha=.3)
    mb = m & (h > 1.0) & (h < 2.8)
    ax[1].scatter(x[mb], lat[mb], s=0.3, c=h[mb], cmap="viridis")
    ax[1].set_title("top view, only the far-axis boundary band 1.0-2.8 m above the rail head")
    for v in (1.2, -1.2, 4.0, -4.0):
        ax[1].axhline(v, c="r", lw=.4)
    ax[1].set_xticks(np.arange(x0, x1 + 1, 10))
    ax[1].grid(alpha=.3)
    ax[2].scatter(x[m], h[m], s=0.3, c=np.clip(lat[m], -4, 4), cmap="coolwarm")
    ax[2].set_title("side view, colour = lateral")
    ax[2].set_xticks(np.arange(x0, x1 + 1, 10))
    ax[2].grid(alpha=.3)
    plt.tight_layout()
    plt.savefig(a.out, dpi=70)


if __name__ == "__main__":
    main()
