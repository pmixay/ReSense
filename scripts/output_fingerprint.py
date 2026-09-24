#!/usr/bin/env python3
"""Fingerprint every per-frame output of the detector on real frames, to prove that a refactor
changes nothing (how the stage split of ``Detector.process`` / ``find_clusters`` was checked on
23.09: identical on 2 930 frames).

Four runs cover the code paths: the 360-degree obstacle recording; a given train speed (the
multi-frame accumulation); the LiDAR-only speed estimator; 1 600 frames of the ride (stations,
the low-object and straddle stages). Recorded per frame: the decision, every confirmed detection,
every candidate cluster (distance, lateral, voxels, zone, reason, kind, score, heights), the
speed and its source, the mount state, the health report and the corridor size. The latency
messages of the health report depend on the machine and are ignored by ``--compare``.

    python scripts/output_fingerprint.py --cache /data/cache --out before.pkl     # on the old code
    python scripts/output_fingerprint.py --cache /data/cache --out after.pkl      # on the new code
    python scripts/output_fingerprint.py --compare before.pkl after.pkl           # exit 1 if any differ
"""
from __future__ import annotations

import argparse
import os
import pickle
import sys
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RUNS = [("obstacle", "doubleT_obstacle", None, None, False),
        ("given_speed", "roundT_doubleT", None, 8.0, False),
        ("estimator", "squareT_platform_squareT_switch", None, None, True),
        ("ride", "new_data", 1600, None, False)]


def _canon(v):
    if isinstance(v, dict):
        return {k: _canon(x) for k, x in v.items() if "ms" not in k and k not in ("timing", "latency")}
    if isinstance(v, (list, tuple)):
        return [_canon(x) for x in v]
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    return v


def _run(job):
    cache, config, (name, bag, limit, speed, est) = job
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.io import iter_npy_frames
    cfg = DetectorConfig.from_yaml(config)
    if est:
        cfg = replace(cfg, accumulation=replace(cfg.accumulation, estimate_speed=True))
    det = Detector(cfg)
    out = []
    for i, fr in iter_npy_frames(os.path.join(cache, bag), cfg.sensor, limit=limit, index_from_name=True):
        r = det.process(fr, ego_speed=speed)
        out.append(_canon({
            "i": i, "obstacle": r.obstacle, "warning": r.warning, "nearest": r.nearest_distance,
            "clear": r.clear_distance, "dets": [d.to_dict() for d in r.detections + r.warnings],
            "cands": [(c.distance, c.lateral, c.n, c.n_raw, c.zone, c.reason, c.kind, c.score, c.n_gauge,
                       c.height_min, c.height_max, c.points_idx.size) for c in r.candidates],
            "speed": r.ego_speed, "src": r.ego_speed_source, "nacc": r.n_accumulated,
            "est": r.ego_speed_estimate, "mount": r.mount, "health": r.health,
            "corr": int(r.corridor_idx.size), "low_range": det.low_range,
        }))
    return name, out


def _strip(frame):
    f = dict(frame)
    h = dict(f.get("health") or {})
    h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]
    h.pop("level", None)
    f["health"] = h
    return f


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--out", help="write the fingerprint here")
    ap.add_argument("--compare", nargs=2, metavar=("A", "B"), help="compare two fingerprints")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    if a.compare:
        x, y = (pickle.load(open(p, "rb")) for p in a.compare)
        bad = 0
        for k in x:
            d = [i for i, (fa, fb) in enumerate(zip(x[k], y[k])) if _strip(fa) != _strip(fb)]
            n = len(x[k]) if len(x[k]) == len(y[k]) else f"{len(x[k])} vs {len(y[k])}"
            print(f"{k}: {n} frames, {len(d)} differ" + (f" (first {d[:5]})" if d else ""))
            bad += len(d) + (len(x[k]) != len(y[k]))
        print("IDENTICAL" if not bad else "DIFFERENT")
        return 1 if bad else 0
    if not a.out:
        ap.error("--out or --compare")
    with Pool(a.jobs) as p:
        res = dict(p.map(_run, [(a.cache, a.config, r) for r in RUNS]))
    pickle.dump(res, open(a.out, "wb"))
    for k, v in res.items():
        print(k, len(v), "frames,", sum(f["obstacle"] for f in v), "obstacle frames")
    return 0


if __name__ == "__main__":
    sys.exit(main())
