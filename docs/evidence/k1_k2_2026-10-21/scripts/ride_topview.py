#!/usr/bin/env python3
"""Top view of ride frames (gate cache, piece split as the gate): returns from the bed to 2 m above the sensor,
the base axis and the curve axis (each to its trusted range), the gauge half-width around each, and the curve clusters
added; replays the piece from its first frame with the tree's YAML ($RESENSE_REPO).

    ride_topview.py <cache root> <piece> <out prefix> <frame> [<frame> ...]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

REPO = os.environ["RESENSE_REPO"]
sys.path[:0] = [REPO, os.path.join(REPO, "scripts")]
import eval_real  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps  # noqa: E402

root, piece, prefix = sys.argv[1], int(sys.argv[2]), sys.argv[3]
want = sorted(int(f) for f in sys.argv[4:])
d = os.path.join(root, "new_data")
files = list(np.array_split(np.array(cache_files(d)), 8)[piece])
stamps = load_cache_stamps(d)
cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(REPO, "configs/default.yaml"), []))
det = Detector(cfg)
for i, f in enumerate(files[:max(want) + 1]):
    stem = cache_file_stem(f)
    fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
    det._curve_added, det._curve_seen = 0, []
    res = det.process(fr)
    if i not in want:
        continue
    xyz = det._frame_xyz
    tr, cv = det.track, det.track.curve
    z0 = float(tr.rail_z(np.array([30.0]))[0])
    m = (xyz[:, 0] > 20) & (xyz[:, 0] < 140) & (xyz[:, 2] > z0 - 0.3) & (xyz[:, 2] < z0 + 3.0)
    fig, ax = plt.subplots(figsize=(14, 5))
    sc = ax.scatter(xyz[m, 0], xyz[m, 1], c=xyz[m, 2] - z0, s=0.3, cmap="viridis", vmin=-0.3, vmax=3.0)
    xs = np.arange(0, 140, 0.5)
    for model, col, name in ((tr, "tab:red", "base axis"), (cv, "tab:blue", "curve axis")):
        if model is None:
            continue
        y = model.center_y(xs)
        v = min(model.axis_valid, 140)
        ax.plot(xs[xs <= v], y[xs <= v], "-", color=col, label=f"{name} (trusted {model.axis_valid:.0f} m)")
        for s in (-1.05, 1.05):
            ax.plot(xs[xs <= v], y[xs <= v] + s, ":", color=col, lw=0.8)
    if cv is not None and hasattr(cv, "curve_from"):
        ax.axvline(cv.curve_from, color="tab:blue", lw=0.5, ls="--", label=f"curve_from {cv.curve_from:.0f} m")
    for dd in res.detections:
        ax.add_patch(plt.Rectangle((dd.center[0] - dd.size[0] / 2, dd.center[1] - dd.size[1] / 2), max(dd.size[0], 0.3),
                                   max(dd.size[1], 0.3), fill=False, color="red", lw=1.5))
    ax.set_xlim(20, 140)
    ax.set_ylim(-12, 8)
    ax.set_title(f"ride piece {piece} frame {i} ({stem}): {'STOP' if res.obstacle else 'no STOP'}; "
                 f"detections {[(round(x.distance, 1), round(x.lateral, 2)) for x in res.detections]}")
    ax.legend(loc="upper left", fontsize=8)
    plt.colorbar(sc, ax=ax, label="height above the rail head at 30 m (m)")
    fig.tight_layout()
    fig.savefig(f"{prefix}_{i}.png", dpi=80)
    plt.close(fig)
    print(f"{prefix}_{i}.png")
