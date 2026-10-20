"""Pictures of gate frames (P4 switch review): replays one gate piece with the gate's own inputs (eval_real's
cache files, piece split and stamps; ``--set`` overrides as regression_gate.py) and, at each requested row, reads
the detector's processed frame (``_frame_xyz``, ``_frame_hd``: lateral from the axis and height above the rail
head) after ``process`` returns and draws, for a window around ``--d`` (or the first detection): top view (X vs
lateral) and side view (X vs height), all returns grey, each reported track's own cluster points coloured and
labelled with id / zone / reason. Read-only: nothing is set on the detector.

    RESENSE_REPO=<tree> python plot_frame.py <cache> <name> <piece> <rows> <out.png> [--set k=v] [--d 40] [--win 12]
    (piece: ride piece 0-7, or -1 for a recording; rows: comma list of rows in the piece)
"""
import argparse
import os
import sys

import numpy as np

ROOT = os.environ["RESENSE_REPO"]
for p in (ROOT, os.path.join(ROOT, "scripts")):
    sys.path.insert(0, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("name")
    ap.add_argument("piece", type=int)
    ap.add_argument("rows")
    ap.add_argument("out")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--d", type=float, default=None)
    ap.add_argument("--win", type=float, default=12.0)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import eval_real
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    cfg = DetectorConfig.from_dict(eval_real.load_cfg_dict(os.path.join(ROOT, "configs", "default.yaml"), a.set))
    d = os.path.join(a.cache, a.name)
    files = cache_files(d)
    stamps = load_cache_stamps(d)
    if a.piece >= 0:
        files = list(np.array_split(np.array(files), 8)[a.piece])
    want = sorted(int(v) for v in a.rows.split(","))
    det = Detector(cfg)
    fig, axes = plt.subplots(2, len(want), figsize=(5.2 * len(want), 7.5), squeeze=False)
    col = 0
    for i, f in enumerate(files[:want[-1] + 1]):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        if i not in want:
            continue
        xyz = det._frame_xyz
        dy, h = (np.asarray(v) for v in det._frame_hd)
        objs = [(o, "STOP") for o in res.detections] + [(o, "CAUTION") for o in res.warnings]
        dc = a.d if a.d is not None else (objs[0][0].distance if objs else 30.0)
        sel = (xyz[:, 0] > dc - a.win) & (xyz[:, 0] < dc + a.win) & (np.abs(dy) < 4) & (h > -0.6) & (h < 4.5)
        top, side = axes[0][col], axes[1][col]
        for ax, y in ((top, dy), (side, h)):
            ax.scatter(xyz[sel, 0], y[sel], s=1, c="0.7", lw=0)
        shown = {o.id: kind for o, kind in objs}
        for t in det.tracker.tracks:
            if t.misses or t.last is None or abs(t.last.distance - dc) > a.win:
                continue
            kind = shown.get(t.id, "track")
            idx = t.last.points_idx
            c = {"STOP": "red", "CAUTION": "orange"}.get(kind, "tab:blue")
            for ax, y in ((top, dy), (side, h)):
                ax.scatter(xyz[idx, 0], y[idx], s=4, c=c, lw=0)
            top.annotate(f"id{t.id} {kind} {t.last.zone}/{t.last.reason or '-'}/{t.last.kind or '-'} hits{t.hits}",
                         (t.last.distance, float(np.median(dy[idx]))), fontsize=7, color=c)
        top.axhline(0.0, c="b", lw=0.5)
        side.axhline(0.0, c="b", lw=0.5)
        top.set_title(f"{stem} row {i}\n{'STOP' if res.obstacle else 'CAUTION' if res.warning else '-'}"
                      f"{' ' + a.title if a.title else ''}", fontsize=8)
        top.set_ylabel("lateral from the axis (m)")
        side.set_ylabel("height above the rail head (m)")
        side.set_xlabel("X (m)")
        col += 1
    fig.tight_layout()
    fig.savefig(a.out, dpi=110)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
