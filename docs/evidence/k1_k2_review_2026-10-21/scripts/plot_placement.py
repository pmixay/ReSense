#!/usr/bin/env python3
"""Top view of one frame: control's and the candidate's published axes (object-free baselines of the range harness,
which place the judge's objects) against the driven path (B6 poses). plot_placement.py <out.png>"""
import json, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, "/home/user/ReSense/scripts")
import gauge_stability as g
R = "/data/acc/range"
fig, axs = plt.subplots(1, 2, figsize=(13, 4.8))
for ax, (bag, k, xmax) in zip(axs, [("squareT_platform_squareT_switch", 400, 130), ("roundT_doubleT", 150, 130)]):
    poses = json.load(open(f"/data/b6/poses_{bag}.json"))["rows"]; ps = g.driven_path(poses)
    xs = np.linspace(0, xmax, 200)
    for tag, col in (("ctl", "tab:red"), ("cand", "tab:blue")):
        b = json.load(open(f"{R}/cache_{tag}/{bag}_baseline.json"))[k]
        y = b["center"] + np.tan(b["yaw"]) * xs + 0.5 * b["curv"] * xs ** 2
        if "curv_step" in b:
            y += 0.5 * b["curv_step"] * np.maximum(xs - b["curv_knot"], 0) ** 2
        lab = "control (v1.2.0) axis" if tag == "ctl" else "candidate published axis (curve)"
        ax.plot(xs, y, color=col, label=f"{lab}, trusted to {b['axis_valid']:.0f} m")
        ax.fill_between(xs, y - 1.05, y + 1.05, color=col, alpha=0.08)
    seg, Pk = ps[k]; Rk = np.array(json.load(open(f"{R}/cache_ctl/{bag}_baseline.json"))[k]["R"]); c0 = json.load(open(f"{R}/cache_ctl/{bag}_baseline.json"))[k]["center"]
    pts = [Rk @ (np.linalg.inv(Pk) @ ps[j][1])[:3, 3] for j in range(k + 1, len(ps)) if ps[j][0] == seg]
    pts = np.array(pts)
    if len(pts):
        m = pts[:, 0] <= xmax
        ax.plot(pts[m, 0], c0 + pts[m, 1], "k--", lw=2, label="driven path (truth, B6 ICP)")
    ax.set_title(f"{bag} frame {k}"); ax.set_xlabel("X ahead (m)"); ax.set_ylabel("Y (m, + left)"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
plt.tight_layout(); plt.savefig(sys.argv[1], dpi=110)
