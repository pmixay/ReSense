import json, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
REPO = "/home/user/ReSense"; sys.path.insert(0, REPO); sys.path.insert(0, REPO + "/scripts")
SP = sys.argv[1]
import eval_real
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps

CASES = [("squareT_platform_squareT_switch", 437, "id 217 elongated 82.9 m"),
         ("squareT_platform_squareT_switch", 612, "id 286 5 m long 94 m"),
         ("squareT_platform_squareT_switch", 696, "id 313 compact 145 m"),
         ("doubleT_obstacle", 100, "TRUE object on rail 56 m")]
cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(REPO + "/configs/default.yaml", []))
fig, axes = plt.subplots(len(CASES), 2, figsize=(15, 4.2 * len(CASES)))
for row, (bag, want, title) in enumerate(CASES):
    d = os.path.join(SP, "cache", bag); files = cache_files(d); stamps = load_cache_stamps(d)
    det = Detector(cfg); res = None
    start = max(0, want - 25)           # a warm-up of 25 frames so the tracker state is realistic
    for i, f in enumerate(files):
        stem = cache_file_stem(f); idx = int(stem.rsplit("_", 1)[1])
        if idx < start: continue
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        if idx == want: break
    xyz = np.asarray(res.xyz, float); x, y, z = xyz.T
    dy = y - res.track.center_y(x); h = z - res.track.rail_z(x)
    dets = res.detections or res.warnings
    cx = float(dets[0].center[0]) if dets else 80.0
    for col, (ylim, band) in enumerate([((-8, 8), (-0.6, 3.5)), ((-3, 3), (-0.6, 3.5))]):
        ax = axes[row, col]
        m = (x > cx - 40) & (x < cx + 40) & (h > band[0]) & (h < band[1]) & (np.abs(dy) < 9)
        sc = ax.scatter(x[m], dy[m], c=h[m], s=3, cmap="viridis", vmin=-0.5, vmax=3)
        for dt in res.detections:
            ax.add_patch(plt.Rectangle((dt.center[0] - dt.size[0] / 2, float(dt.lateral) - dt.size[1] / 2), max(dt.size[0], 0.4), dt.size[1], fill=False, ec="red", lw=1.5))
        ax.set_xlim(cx - 40, cx + 40); ax.set_ylim(*ylim); ax.axhline(0, c="k", lw=.4)
        ax.set_title(f"{bag[:30]} frame {want}: {title} (colour = height above rail head)", fontsize=8)
        ax.set_xlabel("x along track, m"); ax.set_ylabel("lateral, m")
plt.tight_layout(); out = os.path.join(SP, "out", "cases.png"); plt.savefig(out, dpi=70); print(out)
