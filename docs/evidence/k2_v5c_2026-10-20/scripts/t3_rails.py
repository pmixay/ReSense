"""T3: the true track axis at the tunnels cube (marker 19) from the rails, independent of either detector axis.

For each frame whose cube is 9-27 m ahead, the rail-head returns (|h| < 0.06 m from the K2-off run's model) in front
of the cube (4 m .. near face - 0.5 m, unoccluded) are split into the left and the right rail by their lateral from
the K2-off axis (0.45-1.15 m; selection only), each rail is fitted as a robust line in absolute Y, and the two lines'
midpoint at the cube's near face is the true axis there. The cube's centre (marker box mapped into the detector frame)
minus that midpoint is the cube's offset from the track: the cube is static, so the offset holds at every distance.
Accepted frames: fitted rail gauge within 0.06 m of 1.52 m (rail-head centres read slightly wider). Then for every
frame 254-279: each axis' error at the cube against box centre - offset, and the cube's inner face from each axis
against the strict limit 1.05 - 0.15 d / 100 m. Optional: a zoomed picture of one frame.

    python t3_rails.py <off.t3dump.pkl> <off.t3.jsonl> <B.t3.jsonl> [<png> <frame>]
"""
import json
import pickle
import sys

import numpy as np

DA = pickle.load(open(sys.argv[1], "rb"))
JA = {r["i"]: r for r in map(json.loads, open(sys.argv[2]))}
JB = {r["i"]: r for r in map(json.loads, open(sys.argv[3]))}


def rails(i):
    d, r = DA[i], JB[i]
    xyz, h, m_ = d["xyz"], d["h"], d["model"]["out"]
    X = r["box"]["near"]
    x0, x1 = max(4.0, X - 14.0), X - 0.5
    if x1 - x0 < 4:
        return None
    m = (xyz[:, 0] > x0) & (xyz[:, 0] < x1) & (h > -0.06) & (h < 0.06)
    xs, ya = xyz[m, 0].astype(float), xyz[m, 1].astype(float)
    rel = ya - m_.center_y(xs)
    sides = {"L": (rel > 0.45) & (rel < 1.15), "R": (rel < -0.45) & (rel > -1.15)}
    if min(s.sum() for s in sides.values()) < 5:
        return None
    fits = {}
    for k, s in sides.items():
        p = np.polyfit(xs[s], ya[s], 1)
        for _ in range(3):
            res = ya[s] - np.polyval(p, xs[s])
            keep = np.abs(res) < max(0.05, 2.5 * np.median(np.abs(res)))
            p = np.polyfit(xs[s][keep], ya[s][keep], 1)
        fits[k] = p
    xm = 0.5 * (x0 + x1)
    gauge = float(np.polyval(fits["L"], xm) - np.polyval(fits["R"], xm))
    mid = 0.5 * float(np.polyval(fits["L"], X) + np.polyval(fits["R"], X))
    return {"X": X, "window": (x0, x1), "n": {k: int(s.sum()) for k, s in sides.items()}, "gauge": gauge, "mid": mid,
            "fits": fits, "pts": (xs, ya, sides)}


print(" i     X   window      nL  nR  gauge   mid@X   cube-mid  B-mid   A-mid  accepted")
offs = []
for i in sorted(JB):
    if "box" not in JB[i] or not 9.0 <= JB[i]["box"]["near"] <= 27.0:
        continue
    f = rails(i)
    if f is None:
        continue
    yc = JB[i]["box"]["y_c"]
    ok = abs(f["gauge"] - 1.52) < 0.06
    if ok:
        offs.append(yc - f["mid"])
    print(f"{i} {f['X']:5.1f} {f['window'][0]:4.1f}-{f['window'][1]:4.1f} {f['n']['L']:4d} {f['n']['R']:3d}  {f['gauge']:.3f} "
          f"{f['mid']:+.3f}   {yc - f['mid']:+.3f}  {JB[i]['axis_at_box']['out'][1] - f['mid']:+.3f}  "
          f"{JA[i]['axis_at_box']['out'][1] - f['mid']:+.3f}  {'yes' if ok else 'no'}")
off = float(np.median(offs))
print(f"cube centre from the rails' midpoint: median {off:+.3f} m, range {min(offs):+.3f}..{max(offs):+.3f}, "
      f"IQR {np.percentile(offs, 25):+.3f}..{np.percentile(offs, 75):+.3f}, {len(offs)} frames")
print("\n i  near | errA  errB (m; + = left of the true axis, away from the cube) | inner face from: truth  A     B  | "
      "strict limit")
eA, eB = [], []
for i in range(254, 280):
    b = JB[i]
    t = b["box"]["y_c"] - off
    X, ymax = b["box"]["near"], b["box"]["y_max"]
    a_, b_ = JA[i]["axis_at_box"]["out"][1], b["axis_at_box"]["out"][1]
    if 259 <= i <= 273:
        eA.append(a_ - t)
        eB.append(b_ - t)
    print(f"{i} {X:5.1f} | {a_ - t:+.2f} {b_ - t:+.2f} | {t - ymax:.2f} {a_ - ymax:.2f} {b_ - ymax:.2f} | "
          f"{1.05 - 0.15 * X / 100:.2f}")
print(f"frames 259-273 (B's lost STOPs): errA median {np.median(eA):+.2f} ({min(eA):+.2f}..{max(eA):+.2f}), "
      f"errB median {np.median(eB):+.2f} ({min(eB):+.2f}..{max(eB):+.2f}); median |err| A {np.median(np.abs(eA)):.2f}, "
      f"B {np.median(np.abs(eB)):.2f}")
if len(sys.argv) > 5:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    png, i = sys.argv[4], int(sys.argv[5])
    f, d, b = rails(i), DA[i], JB[i]
    xyz, h = d["xyz"], d["h"]
    fig, ax = plt.subplots(figsize=(14, 5))
    m = (xyz[:, 0] < 35) & (np.abs(xyz[:, 1]) < 3.5)
    ax.scatter(xyz[m, 0], xyz[m, 1], s=0.5, c="0.8", lw=0)
    xs, ya, sides = f["pts"]
    for k, c in (("L", "tab:green"), ("R", "tab:olive")):
        ax.scatter(xs[sides[k]], ya[sides[k]], s=4, c=c, label=f"rail-head returns {k}")
        xx = np.array([0, b["box"]["near"] + 2])
        ax.plot(xx, np.polyval(f["fits"][k], xx), c=c, lw=1)
    X = np.linspace(0, 35, 71)
    ax.plot(X, JA[i]["axis_at_box"] and DA[i]["model"]["out"].center_y(X), c="tab:orange", label="K2-off axis")
    bx = b["box"]
    ax.add_patch(plt.Rectangle((bx["near"], bx["y_min"]), 0.5, bx["y_max"] - bx["y_min"], fill=False, ec="red", lw=1.5))
    ax.plot([bx["near"]], [f["mid"]], "kx", ms=10, mew=2, label="rails' midpoint at the cube")
    ax.set_xlim(0, 35)
    ax.set_ylim(-3, 3)
    ax.set_title(f"synthetic_tunnels frame {i}: rails in front of the cube (window {f['window'][0]:.0f}-{f['window'][1]:.0f} m), "
                 f"gauge {f['gauge']:.3f} m, cube centre {bx['y_c'] - f['mid']:+.3f} m from the rails' midpoint")
    ax.legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    fig.savefig(png, dpi=90)
