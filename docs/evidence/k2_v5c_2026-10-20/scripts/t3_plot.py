"""Top views of t3_trace.py dumps: the cloud (detector frame; grey = bed level, black = above 0.3 m over the rail head),
the boundary bins estimate_axis_from_walls gave (circles; filled = used by the joint fit, colour per segment), the rail
slab midpoints, variant B's output axis (joint shape), its base axis, the K2-off axis, the strict-gauge edges
(1.05 m - 0.15 m per 100 m) around B's and the K2-off axis, the marker box (red) and the axis the cube implies
(box centre + the cube's offset from the rails' midpoint, black x; --offset, measured by t3_rails.py).

    python t3_plot.py <B.t3dump.pkl> <B.t3.jsonl> <off.t3dump.pkl> <off.t3.jsonl> <png dir> --offset -1.165 <frame> ...
"""
import json
import os
import pickle
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

DB, JB, DA, JA, out = sys.argv[1:6]
assert sys.argv[6] == "--offset"
off = float(sys.argv[7])
frames = [int(v) for v in sys.argv[8:]]
DB, DA = pickle.load(open(DB, "rb")), pickle.load(open(DA, "rb"))
JB = {r["i"]: r for r in map(json.loads, open(JB))}
JA = {r["i"]: r for r in map(json.loads, open(JA))}
os.makedirs(out, exist_ok=True)
X = np.linspace(0, 120, 241)
for i in frames:
    d, a, r = DB[i], DA[i], JB[i]
    fig, ax = plt.subplots(figsize=(15, 6))
    xyz, h = d["xyz"], d["h"]
    lo = h < 0.3
    ax.scatter(xyz[lo, 0], xyz[lo, 1], s=0.3, c="0.75", lw=0)
    ax.scatter(xyz[~lo, 0], xyz[~lo, 1], s=0.5, c="k", lw=0)
    if d["bounds"]:
        for name, (bx, by) in d["bounds"].items():
            ax.plot(bx, by, "o", mfc="none", mec="tab:gray", ms=5)
    s = d["stash"]
    if s is not None:
        cols = plt.cm.tab10(np.arange(10))
        for g, (name, sx, sy) in enumerate(s["segs"]):
            m = s["masks"].get(g)
            c = cols[g % 10]
            ax.plot(sx, sy, "o", mfc="none", mec=c, ms=7)
            if m is not None and m.any():
                ax.plot(sx[m], sy[m], "o", color=c, ms=5, label=f"{name} seg {g}: {int(m.sum())} used")
        ax.plot(s["rails_x"], s["rails_y"], "s", color="tab:green", ms=7, label="rail slab midpoints")
    mo, mb, ma = d["model"]["out"], d["model"]["base"], a["model"]["out"]
    hw = 1.05 - 0.15 * X / 100
    for m_, c, lab in ((mo, "tab:blue", "B output (joint shape)"), (ma, "tab:orange", "K2 off")):
        y = m_.center_y(X)
        ax.plot(X, y, color=c, lw=1.5, label=lab)
        ax.plot(X, y + hw, color=c, lw=0.7, ls="--")
        ax.plot(X, y - hw, color=c, lw=0.7, ls="--")
    if mb is not None:
        ax.plot(X, mb.center_y(X), color="tab:purple", lw=1, ls=":", label="B base")
    if "box" in r:
        b = r["box"]
        ax.add_patch(plt.Rectangle((b["near"], b["y_min"]), 0.5, b["y_max"] - b["y_min"], fill=False, ec="red", lw=1.5))
        ax.plot([b["near"]], [b["y_c"] - off], "kx", ms=10, mew=2, label=f"true axis at the cube (rails: cube centre {off:+.3f} m)")
    jr = r["joint_reach"]
    if jr:
        ax.axvline(jr, color="tab:blue", lw=0.8, ls="-.")
    ax.set_xlim(0, 120)
    ax.set_ylim(-6, 6)
    ax.set_xlabel("X (m, detector frame)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"synthetic_tunnels frame {i}: variant B vs K2 off; cube near face {r.get('box', {}).get('near', float('nan')):.1f} m; "
                 f"B reach cap {jr:.0f} m")
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(out, f"tunnels_f{i}.png"), dpi=90)
    plt.close(fig)
print("wrote", len(frames), "frames to", out)
