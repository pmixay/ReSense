#!/usr/bin/env python3
"""Top view of roundT_doubleT frames: the driven path (B6 ICP poses, later sensor positions in the frame's vehicle frame)
against the v1.2.0 axis and the candidate's published axis, each drawn to its trusted range (dashed beyond).

    plot_curve.py <track_control.json> <track_cand.json> <poses.json> <out.png> <frame> [<frame> ...]
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, __file__.rsplit("/docs/", 1)[0] + "/scripts")
import gauge_stability as g  # noqa: E402

tc, tk = (json.load(open(p))["rows"] for p in sys.argv[1:3])
ps = g.driven_path(json.load(open(sys.argv[3]))["rows"])
frames = [int(f) for f in sys.argv[5:]]
fig, axs = plt.subplots(len(frames), 1, figsize=(10, 3.2 * len(frames)))
for ax, k in zip(np.atleast_1d(axs), frames):
    seg, Pk = ps[k]
    Rk = np.array(tc[k]["R"])
    pts = []
    for j in range(k + 1, len(ps)):
        if ps[j][0] != seg:
            break
        pts.append(Rk @ (np.linalg.inv(Pk) @ ps[j][1])[:3, 3])
    pts = np.array(pts)
    ax.plot(pts[:, 0], pts[:, 1], "k.", ms=3, label="driven path (ICP)")
    xs = np.arange(0, 200, 1.0)
    for r, c, name in ((tc[k], "tab:red", "v1.2.0 axis"), (tk[k], "tab:blue", "candidate published axis")):
        y = np.array([g.lateral(r, x) - r["center"] for x in xs])
        v = min(r["axis_valid"], 200)
        ax.plot(xs[xs <= v], y[xs <= v], "-", color=c, label=f"{name} (trusted {v:.0f} m)")
        ax.plot(xs[xs > v], y[xs > v], "--", color=c, lw=0.8)
    ax.set_title(f"roundT_doubleT frame {k}")
    ax.set_xlabel("X ahead (m)")
    ax.set_ylabel("Y (m)")
    ax.set_ylim(-25, 5)
    ax.legend(loc="lower left", fontsize=8)
fig.tight_layout()
fig.savefig(sys.argv[4], dpi=90)
