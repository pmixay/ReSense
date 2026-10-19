#!/usr/bin/env python3
"""Replay a gate cache through ONE detector in order, as ``scripts/eval_real.py run_piece`` does for one
piece (same frame construction, stamps and ``Detector.process`` call), and record per frame the result
(``FrameResult.to_dict()``, as the gate's JSONL) plus an ``x`` block for the F1 analysis:

* ``decision`` by the node's rule (STOP > FAULT > CAUTION > GO; ``judge_runner.node_decision``);
* track-model state: rail slabs, rail score, the low stage's observed bed range;
* for every reported low-kind detection (``--trace``): the reporting cluster's top (``height_max``,
  above the model's rail-head plane), lateral extent, ``rail_line`` flag, and a dump of the frame's
  points around it (X +- 6 m, |dy| < 1.7 m, -0.6 < h < 0.6, rail coordinate) with the cluster's own
  points flagged, written to ``<out>_low/<frame>_<track>.npz`` for the offline local-reference study.

The trace only reads detector state after ``process`` returns (``_frame_xyz``, ``_frame_hd``,
``_dy_rail``, ``tracker.tracks``); a traced run is checked against a plain run before use.

    replay.py --cache /data/cache --bag new_data --out OUT [--set lowobj.x=1] [--trace]
              [--start N --end M]  (frame positions in the cache's natural order; the detector
                                    still processes every frame from 0 so its state is the real one)
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
for p in (ROOT, ROOT / "scripts", Path(__file__).resolve().parent):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402


def node_decision(res) -> str:
    h = res.health or {}
    level = h.get("level", "ok")
    if res.obstacle:
        return "STOP"
    if level == "error":
        return "FAULT"
    if res.warning or h.get("decision_level", level) == "warn":
        return "CAUTION"
    return "GO"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--bag", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--config", default=str(ROOT / "configs/default.yaml"))
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--trace", action="store_true")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=10 ** 9)
    ap.add_argument("--full", action="store_true", help="write the whole to_dict() (else a compact record)")
    ap.add_argument("--lowref", action="store_true", help="record every low cluster's top against the rail lines (lowref.py)")
    ap.add_argument("--tracks", action="store_true", help="record every matched track's own cluster (traced attribution)")
    a = ap.parse_args()

    import eval_real
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps

    cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
    cfg = DetectorConfig.from_dict(cfg_dict)
    d = os.path.join(a.cache, a.bag)
    files = cache_files(d)
    stamps = load_cache_stamps(d)
    det = Detector(cfg)
    low_dir = a.out + "_low"
    if a.trace:
        os.makedirs(low_dir, exist_ok=True)
    t0 = time.time()
    n_low = 0
    with open(a.out + ".jsonl", "w", encoding="utf-8") as fh:
        for i, f in enumerate(files):
            if i >= a.end:
                break
            stem = cache_file_stem(f)
            fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
            res = det.process(fr)
            if i < a.start:
                continue
            tr = res.track
            rec = res.to_dict() if a.full else {
                "obstacle": res.obstacle, "warning": res.warning,
                "nearest_distance": None if res.nearest_distance is None else round(float(res.nearest_distance), 2),
                "detections": [x.to_dict() for x in res.detections],
                "warnings": [x.to_dict() for x in res.warnings],
                "health": {k: (res.health or {}).get(k) for k in ("level", "decision_level", "monitored_range",
                                                                    "rail_lock", "clear_distance")},
                "clear_distance": round(float(res.clear_distance), 1)}
            rec["frame"] = i
            rec["frame_id"] = stem
            tracks = {t.id: t for t in det.tracker.tracks}
            x = {"decision": node_decision(res), "rail_slabs": int(tr.rail_slabs),
                 "rail_score": round(float(tr.rail_score), 3), "low_range": round(float(det.low_range), 1),
                 "ego": None if res.ego_speed_estimate is None else round(float(res.ego_speed_estimate), 2)}
            lows = []
            for dd in res.detections + res.warnings:
                t = tracks.get(dd.id)
                if t is None or t.last is None or t.last.kind != "low":
                    continue
                c = t.last
                info = {"id": dd.id, "zone": dd.zone, "reason": dd.reason, "d": round(float(c.distance), 2),
                        "top": round(float(c.height_max), 3), "hmin": round(float(c.height_min), 3),
                        "lat": round(float(c.lateral), 3), "size": [round(float(v), 3) for v in c.size],
                        "n": int(c.n), "rail_line": bool(c.rail_line), "misses": int(t.misses),
                        "weak": bool(c.low_height_weak)}
                if a.trace and dd.zone == "gauge" and t.misses == 0 and c.points_idx.size:
                    xyz = det._frame_xyz
                    dy_all, h_all = det._frame_hd
                    dyr = det._dy_rail
                    X = xyz[:, 0]
                    x0, x1 = float(c.bbox_min[0]), float(c.bbox_max[0])
                    sel = np.flatnonzero((X > x0 - 6.0) & (X < x1 + 6.0) & (np.abs(dyr) < 1.7)
                                         & (h_all > -0.6) & (h_all < 0.6))
                    own = np.isin(sel, c.points_idx)
                    np.savez_compressed(os.path.join(low_dir, f"{i:05d}_{dd.id}.npz"), X=X[sel].astype(np.float32),
                                        dy=dyr[sel].astype(np.float32), h=h_all[sel].astype(np.float32),
                                        own=own, own_idx=c.points_idx, bbox_min=c.bbox_min, bbox_max=c.bbox_max,
                                        rails_spacing=cfg.track.rails_spacing)
                    info["dump"] = True
                    n_low += 1
                lows.append(info)
            if lows:
                x["low"] = lows
            if a.tracks:
                x["tracks"] = [[t.id, round(float(t.last.distance), 2), round(float(t.last.lateral), 3), t.last.kind,
                                t.last.zone, t.last.reason, bool(t.last.low_height_weak)]
                               for t in det.tracker.tracks if t.misses == 0 and t.last is not None]
            if a.lowref:
                import lowref
                lc = lowref.frame_info(det, res)
                if lc:
                    x["lowc"] = lc
            rec["x"] = x
            fh.write(json.dumps(rec) + "\n")
    meta = {"bag": a.bag, "frames": len(files), "written_from": a.start, "set": a.set, "trace": a.trace,
            "low_dumps": n_low, "wall_s": round(time.time() - t0, 1), "repo": str(ROOT)}
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
