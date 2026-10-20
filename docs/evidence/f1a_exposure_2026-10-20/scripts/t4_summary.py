"""T4 summary of t4_trace.py: the low clusters F1a made weak, those whose rail reference is >= --min-ref (0.11 m, the
review's condition: the frame's rail line that far above the model's plane caps a plain low cluster below it whatever
its height), grouped into episodes (same piece, consecutive frames, distance within 3 m of the previous frame's), with
a picture of each episode's first frame: top view coloured by height above the model's rail head and the cross-section
(lateral vs height) of the returns within 1 m along the cluster, its own returns in red, the reference as a line.

    python t4_summary.py <t4 out dir> <png dir> [--min-ref 0.11]
"""
import glob
import json
import os
import sys

import numpy as np

d, png = sys.argv[1], sys.argv[2]
min_ref = float(sys.argv[sys.argv.index("--min-ref") + 1]) if "--min-ref" in sys.argv else 0.11
rows = []
for f in sorted(glob.glob(os.path.join(d, "*.f1a.jsonl"))):
    piece = os.path.basename(f)[:-len(".f1a.jsonl")]
    for line in open(f):
        r = json.loads(line)
        r["piece"] = piece
        r["frame"] = int(r["stem"].rsplit("_", 1)[1]) if piece.startswith("cloud") else r["stem"]
        rows.append(r)
print(f"F1a-weak low clusters: {len(rows)} in all; with reference >= {min_ref} m: "
      f"{sum(1 for r in rows if r['ref'] is not None and r['ref'] >= min_ref)}")
hi = [r for r in rows if r["ref"] is not None and r["ref"] >= min_ref]


def stem_key(r):
    s = r["stem"]
    parts = s.rsplit("_", 1)
    split = parts[0].rsplit("_", 1)[-1] if s.startswith("new_data") else "0"
    return (r["piece"], int(split) if split.isdigit() else 0, int(parts[1]))


hi.sort(key=stem_key)
episodes = []
for r in hi:
    k = stem_key(r)
    if episodes:
        e = episodes[-1]
        pk = stem_key(e[-1])
        if k[0] == pk[0] and (k[1], k[2]) in ((pk[1], pk[2] + 1), (pk[1] + 1, 0)) and abs(r["d"] - e[-1]["d"]) < 3.0:
            e.append(r)
            continue
    episodes.append([r])
print(f"{len(episodes)} episodes")
print(" #  first stem              frames  d (m)        lat     top    ref    size (L,W,H)         n")
os.makedirs(png, exist_ok=True)
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
for n, e in enumerate(episodes):
    r = e[0]
    print(f"{n:2d}  {r['stem']:22s} {len(e):5d}  {e[0]['d']:5.1f}-{e[-1]['d']:5.1f}  {r['lat']:+.2f}  {r['top']:.3f}  "
          f"{r['ref']:.3f}  {r['size']}  {r['n']}")
    npz = os.path.join(d, r["piece"] + "_f1a", f"{r['stem']}_{r['k']}.npz")
    if not os.path.exists(npz):
        continue
    z = np.load(npz)
    xyz, dy, h, own = z["xyz"], z["dy"], z["h"], z["own"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 4.5), gridspec_kw={"width_ratios": [2, 1]})
    sc = a1.scatter(xyz[:, 0], xyz[:, 1], c=np.clip(h, -0.3, 0.6), s=3, cmap="viridis")
    a1.scatter(xyz[own, 0], xyz[own, 1], s=12, facecolors="none", edgecolors="red")
    a1.set_xlabel("X (m)")
    a1.set_ylabel("Y (m)")
    fig.colorbar(sc, ax=a1, label="h above the model's rail head (m)")
    c = r["centroid"]
    m = np.abs(xyz[:, 0] - c[0]) < 1.0
    a2.scatter(dy[m], h[m], s=4, c="0.4")
    a2.scatter(dy[own], h[own], s=14, c="red", label="cluster")
    a2.axhline(r["ref"], color="tab:blue", lw=1, label=f"rail reference {r['ref']:.3f}")
    a2.axhline(0.12, color="tab:orange", lw=0.8, ls="--", label="envelope floor 0.12")
    a2.set_xlabel("dy (m)")
    a2.set_ylabel("h (m)")
    a2.set_ylim(-0.4, 0.8)
    a2.legend(fontsize=7)
    fig.suptitle(f"{r['piece']} {r['stem']}: F1a-weak low cluster at {r['d']:.1f} m, lateral {r['lat']:+.2f} m, "
                 f"top {r['top']:.3f}, ref {r['ref']:.3f}; episode of {len(e)} frames")
    fig.tight_layout()
    fig.savefig(os.path.join(png, f"ep{n:02d}_{r['stem']}.png"), dpi=80)
    plt.close(fig)
