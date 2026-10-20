"""Pictures of the clusters F1a marks weak (trace_f1a.py output): the cloud around the cluster (forward window
+-6 m, lateral +-3 m, height around the cluster), top view and side view, the weak cluster's box in magenta, the run's
detections (blue) and warnings (orange), the non-dust marker boxes (green).

    python f1a_frames.py <bag dir> <markers.jsonl> <run.jsonl> <f1a.json> <out prefix>
"""
import glob
import importlib.util
import json
import os
import sys

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("marker_frames", os.path.join(HERE, "../../synth_markers_2026-10-19/scripts/marker_frames.py"))
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)
bag, markers, runp, f1a, out = sys.argv[1:6]
rows = {r["i"]: r for r in map(json.loads, open(markers))}
run = {r["i"]: r for r in map(json.loads, open(runp))}
weak = {w["i"]: w["weak"] for w in json.load(open(f1a))["weak_frames"]}
db3 = sorted(glob.glob(os.path.join(bag, "*.db3")))[0]
for i, xyz in mf.clouds(db3, set(weak)):
    fwd, lat, up = -xyz[:, 1], xyz[:, 0], xyz[:, 2]
    r = run[i]
    for k, w in enumerate(weak[i]):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
        x0, x1 = w["bbox_x"]
        sel = (fwd > x0 - 6) & (fwd < x1 + 6) & (np.abs(lat) < 3.5) & (up > -3.5) & (up < 1.5)
        ax1.scatter(fwd[sel], lat[sel], s=2, c="k")
        ax2.scatter(fwd[sel], up[sel], s=2, c="k")
        # the weak cluster's returns: returns inside its x range near the lateral of the cluster; drawn as the cluster centre box only
        for ax, v in ((ax1, 1), (ax2, 2)):
            ax.set_xlim(x0 - 6, x1 + 6)
        for kind, lst, col in (("det", r["dets"], "blue"), ("warn", r["warns"], "orange")):
            for d in lst:
                c, sz = d["c"], d["size"]
                ax1.add_patch(plt.Rectangle((c[0] - sz[0] / 2, c[1] - sz[1] / 2), max(sz[0], 0.1), max(sz[1], 0.1), fill=False, ec=col, lw=1.5))
        for m in rows[i]["markers"]:
            if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
                lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
                ax1.add_patch(plt.Rectangle((-hi[1], lo[0]), hi[1] - lo[1], hi[0] - lo[0], fill=False, ec="green", lw=1.2))
                ax2.add_patch(plt.Rectangle((-hi[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], fill=False, ec="green", lw=1.2))
        ax1.axvspan(x0, max(x1, x0 + 0.05), color="magenta", alpha=0.35)
        ax2.axvspan(x0, max(x1, x0 + 0.05), color="magenta", alpha=0.35)
        ax1.set_ylabel("lateral (m, left +)")
        ax2.set_ylabel("up (m, sensor frame)")
        ax2.set_xlabel("forward (m); magenta band = x range of the weak low cluster (%d returns, top %.3f m above the rail head)" % (w["n"], w["hmax"]))
        ax1.set_title(f"{os.path.basename(bag.rstrip('/'))} frame {i}: {r['decision']}, clear {r['clear']} m, "
                      f"F1a weak low cluster at {w['d']} m, size {w['size']}", fontsize=9)
        fig.tight_layout()
        fig.savefig(f"{out}_{i:04d}_{k}.png", dpi=75)
        plt.close(fig)
