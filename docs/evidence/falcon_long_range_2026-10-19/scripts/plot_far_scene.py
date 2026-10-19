#!/usr/bin/env python3
"""Raw far scene of the empty frames 0..1700 (every 4th) in the track reference: top, side, front view."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

EV = Path(__file__).resolve().parents[1]
tr = json.loads((EV / "track_reference.json").read_text())["track"]
P = [np.load(f"/home/user/data/falcon/f_{i:05d}.npz")["xyz"] for i in range(0, 1700, 4)]
xyz = np.vstack(P).astype(np.float64)
x, y, z = xyz.T
lat = y - (tr["a"] + tr["b"] * x)
h = z - (tr["z0"] + tr["c"] * x)
fig, ax = plt.subplots(3, 1, figsize=(14, 13))
m = (x > 150) & (x < 330) & (np.abs(lat) < 8) & (h > -1) & (h < 6)
ax[0].scatter(x[m], lat[m], s=0.5, c=np.clip(h[m], -1, 5), cmap="viridis")
ax[0].set_title("top view in the track reference, 425 empty frames 0-1700, colour = height")
for v in (1.05, -1.05):
    ax[0].axhline(v, c="r", lw=.5)
ax[0].set_ylabel("lateral m")
ax[1].scatter(x[m], h[m], s=0.5, c=np.clip(lat[m], -4, 4), cmap="coolwarm")
ax[1].set_title("side view, colour = lateral")
ax[1].set_ylabel("height above rail reference m")
for v in (0.12, 3.0):
    ax[1].axhline(v, c="r", lw=.5)
m2 = (x > 240) & (x < 265) & (np.abs(lat) < 8) & (h > -1) & (h < 6)
sc = ax[2].scatter(lat[m2], h[m2], s=2, c=x[m2], cmap="plasma")
plt.colorbar(sc, ax=ax[2])
ax[2].set_title("front view 240-265 m, colour = range; red = gauge profile")
ax[2].set_xlabel("lateral m")
ax[2].set_aspect("equal")
ax[2].plot([-1.05, 1.05, 1.05, -1.05, -1.05], [0.12, 0.12, 3, 3, 0.12], "r-", lw=.7)
plt.tight_layout()
plt.savefig(EV / "far_scene_empty_frames.png", dpi=80)
