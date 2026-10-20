"""Pictures of the organizer dust frames with the final source's detections and warnings.

For every frame that has a dust box (marker box with extent < 0.1 m): top view (forward x lateral) and side view
(forward x up) of the cloud near the sensor (0-14 m, lateral +-4 m) with the dust boxes (red, grown by --margin for the
point count), and an overview (0-160 m) with every detection (blue) and warning (orange) of the run and the non-dust
marker boxes (green). The point count inside each dust box (box grown by --margin) is printed and written to
<out>_boxes.json.

    python dust_frames.py <bag dir> <markers.jsonl> <run.jsonl> <out prefix> [--margin 0.05]
"""
import argparse
import glob
import importlib.util
import json
import os

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("marker_frames", os.path.join(HERE, "../../synth_markers_2026-10-19/scripts/marker_frames.py"))
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("markers")
ap.add_argument("run")
ap.add_argument("out")
ap.add_argument("--margin", type=float, default=0.05)
ap.add_argument("--frames", help="comma list; default: every dust frame")
a = ap.parse_args()
rows = {r["i"]: r for r in map(json.loads, open(a.markers))}
run = {r["i"]: r for r in map(json.loads, open(a.run))}


def boxes(i):
    out = []
    for m in rows[i]["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            out.append((m["id"], lo, hi, bool((hi - lo).max() < 0.1)))
    return out


want = [int(f) for f in a.frames.split(",")] if a.frames else sorted(i for i in rows if any(b[3] for b in boxes(i)))
db3 = sorted(glob.glob(os.path.join(a.bag, "*.db3")))[0]
report = []
for i, xyz in mf.clouds(db3, set(want)):
    fwd, lat, up = -xyz[:, 1], xyz[:, 0], xyz[:, 2]
    r = run[i]
    fig, axs = plt.subplots(3, 1, figsize=(10, 10))
    ax1, ax2, ax3 = axs
    sel = (fwd > 0) & (fwd < 14) & (np.abs(lat) < 4) & (up > -3) & (up < 3)
    ax1.scatter(fwd[sel], lat[sel], s=1, c="k")
    ax2.scatter(fwd[sel], up[sel], s=1, c="k")
    for ax in (ax1, ax2):
        ax.set_xlim(0, 14)
    ax1.set_ylim(-4, 4)
    ax2.set_ylim(-3, 3)
    for bid, lo, hi, dust in boxes(i):
        if not dust:
            continue
        inside = int(((xyz >= lo - a.margin) & (xyz <= hi + a.margin)).all(1).sum())
        c = (lo + hi) / 2
        rec = {"frame": i, "id": bid, "fwd": round(float(-c[1]), 2), "lat": round(float(c[0]), 2), "up": round(float(c[2]), 2),
               "pts_in_box": inside, "pts_within_0.3m": int((np.linalg.norm(xyz - c, axis=1) <= 0.3).sum())}
        report.append(rec)
        print(json.dumps(rec))
        for ax, (u0, u1, v0, v1) in ((ax1, (-hi[1], -lo[1], lo[0], hi[0])), (ax2, (-hi[1], -lo[1], lo[2], hi[2]))):
            ax.add_patch(plt.Rectangle((u0 - 0.1, v0 - 0.1), u1 - u0 + 0.2, v1 - v0 + 0.2, fill=False, ec="red", lw=1.5))
        ax1.annotate(f"dust {bid} ({inside} pts)", (-hi[1], hi[0] + 0.15), fontsize=8, color="red")
    ax3.set_xlim(0, 160)
    ax3.set_ylim(-14, 14)
    sel3 = (fwd > 0) & (fwd < 160) & (np.abs(lat) < 14) & (up > -3) & (up < 4)
    ax3.scatter(fwd[sel3][::4], lat[sel3][::4], s=0.2, c="0.6")
    for bid, lo, hi, dust in boxes(i):
        if not dust:
            ax3.add_patch(plt.Rectangle((-hi[1], lo[0]), max(-lo[1] + hi[1], 0.4), max(hi[0] - lo[0], 0.4), fill=False, ec="green", lw=1.2))
            ax3.annotate(f"obj {bid}", (-hi[1], hi[0]), fontsize=7, color="green")
    for kind, lst, col in (("det", r["dets"], "blue"), ("warn", r["warns"], "orange")):
        for d in lst:
            c, sz = d["c"], d["size"]
            for ax in (ax1, ax3) if d["d"] < 14 else (ax3,):
                ax.add_patch(plt.Rectangle((c[0] - sz[0] / 2, c[1] - sz[1] / 2), max(sz[0], 0.3 if ax is ax3 else 0.05),
                                           max(sz[1], 0.3 if ax is ax3 else 0.05), fill=False, ec=col, lw=1.5))
            ax3.annotate(f"{kind} {d['d']} m {d.get('reason') or ''}", (c[0], c[1] + 0.8), fontsize=7, color=col)
            if d["d"] < 14:
                ax2.add_patch(plt.Rectangle((c[0] - sz[0] / 2, c[2] - sz[2] / 2), max(sz[0], 0.05), max(sz[2], 0.05), fill=False, ec=col, lw=1.5))
    ax1.set_ylabel("lateral (m, left +)")
    ax2.set_ylabel("up (m, sensor frame)")
    ax2.set_xlabel("forward (m)")
    ax3.set_ylabel("lateral (m)")
    ax3.set_xlabel("forward (m): every 4th return of the frame (grey), non-dust marker boxes (green)")
    ax1.set_title(f"{os.path.basename(a.bag.rstrip('/'))} frame {i}: {r['decision']}, clear {r['clear']} m; dust boxes red; "
                  f"{len(r['dets'])} detections (blue), {len(r['warns'])} warnings (orange)", fontsize=9)
    fig.tight_layout()
    fig.savefig(f"{a.out}_{i:04d}.png", dpi=75)
    plt.close(fig)
json.dump(report, open(a.out + "_boxes.json", "w"), indent=1)
