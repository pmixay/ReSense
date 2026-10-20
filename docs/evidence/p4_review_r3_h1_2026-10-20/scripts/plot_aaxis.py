"""Pictures of the A-axis frames (H1): processed cloud (detector frame, lateral from the axis, height above the rail
head) at k = 300, 310, 322 for H1 on and H1 off, from the hooks' dumps. Grey: all returns in a window around the
injected 2.8 m body; coloured: each matched track's own cluster (red = the run's STOP, orange = CAUTION, blue = other).

    python plot_aaxis.py <aaxis dir> <out.png>
"""
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

D, out = sys.argv[1], sys.argv[2]
ks = (300, 310, 322)
res = {tag: json.load(open(os.path.join(D, f"A-axis-{tag}-dump.json")))["rows"] for tag in ("on", "off")}
hooks = {tag: [json.loads(line) for line in open(os.path.join(D, f"hooks_{tag}_dump.ndjson"))] for tag in ("on", "off")}
fig, axes = plt.subplots(4, len(ks), figsize=(5.4 * len(ks), 13), squeeze=False)
for c, k in enumerate(ks):
    for r, tag in enumerate(("on", "off")):
        row = res[tag][k]
        X = row["X"]
        z = np.load(os.path.join(D, f"dump_{tag}", f"call{k:05d}.npz"))
        xyz, dy, h = z["xyz"], z["dy"], z["h"]
        sel = (xyz[:, 0] > X - 9) & (xyz[:, 0] < X + 9) & (np.abs(dy) < 3.5) & (h > -0.5) & (h < 4.2)
        top, side = axes[2 * r][c], axes[2 * r + 1][c]
        for ax, y in ((top, dy), (side, h)):
            ax.scatter(xyz[sel, 0], y[sel], s=1, c="0.75", lw=0)
        stops = {t["id"] for t in hooks[tag][k]["tracks"] if t["reported"]}
        for key in z.files:
            if not key.startswith("own_"):
                continue
            tid = int(key[4:])
            idx = z[key]
            if idx.size == 0 or abs(float(np.median(xyz[idx, 0])) - X) > 6:
                continue
            col = ("red" if row["hit"] else "orange") if tid in stops else "tab:blue"
            for ax, y in ((top, dy), (side, h)):
                ax.scatter(xyz[idx, 0], y[idx], s=5, c=col, lw=0)
        lab = f"H1 {tag}: k {k}, body at X {X} m: {row['decision']}{' (matched STOP)' if row['hit'] else ''}"
        top.set_title(lab, fontsize=8)
        top.set_ylabel("lateral from the axis (m)")
        side.set_ylabel("height above the rail head (m)")
        side.set_xlabel("X (m)")
        top.axhline(0, c="b", lw=0.5)
        side.axhline(0, c="b", lw=0.5)
fig.tight_layout()
fig.savefig(out, dpi=100)
print("wrote", out)
