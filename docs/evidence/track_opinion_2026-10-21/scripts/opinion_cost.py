#!/usr/bin/env python3
"""Per-frame cost of the track opinion: ``Tracker._doubt`` and ``Detector.process`` wall time (perf_counter) on
consecutive ride frames, for a list of configs; the decisions of the timed run are compared with an untimed run
of the same config (the wrapper must not change a result).

    opinion_cost.py --cache /data/cache/new_data --first 1409 --frames 600 --set-a "" --set-b "tracking.doubt_model=..."
"""
import argparse
import json
import os
import sys
import time

import numpy as np

ROOT = os.environ.get("RESENSE_REPO", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))
sys.path[:0] = [ROOT, os.path.join(ROOT, "scripts")]
import eval_real  # noqa: E402
from cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps  # noqa: E402

from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.tracking import Tracker  # noqa: E402


def run(files, stamps, sets, timed):
    cfg = eval_real.load_cfg(os.path.join(ROOT, "configs/default.yaml"), sets)
    det = Detector(cfg)
    spent, proc, dec = [0.0], [], []
    orig = Tracker._doubt
    if timed:
        def wrapped(self):
            t0 = time.perf_counter()
            orig(self)
            spent[0] += time.perf_counter() - t0
        Tracker._doubt = wrapped
    try:
        per = []
        for i, f in enumerate(files):
            fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(cache_file_stem(f), i * 0.1),
                                    frame_id=cache_file_stem(f))
            s0, t0 = spent[0], time.perf_counter()
            res = det.process(fr)
            proc.append((time.perf_counter() - t0) * 1e3)
            per.append((spent[0] - s0) * 1e3)
            dec.append([(round(d.distance, 3), d.zone, d.reason) for d in res.detections + res.warnings])
    finally:
        Tracker._doubt = orig
    return np.array(per), np.array(proc), dec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/data/cache/new_data")
    ap.add_argument("--first", type=int, default=1409)
    ap.add_argument("--frames", type=int, default=600)
    ap.add_argument("--config", action="append", required=True, help="name=set1;set2 (empty = defaults)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    files = cache_files(a.cache)[a.first:a.first + a.frames]
    stamps = load_cache_stamps(a.cache)
    res = {"frames": len(files), "first": a.first, "configs": {}}
    for spec in a.config:
        name, sets = spec.split("=", 1)
        sets = [s for s in sets.split(";") if s]
        per, proc, dec = run(files, stamps, sets, True)
        _, _, dec0 = run(files, stamps, sets, False)
        res["configs"][name] = {"set": sets, "doubt_ms_mean": round(float(per.mean()), 4),
                                "doubt_ms_p95": round(float(np.quantile(per, 0.95)), 4),
                                "doubt_ms_max": round(float(per.max()), 3),
                                "process_ms_mean": round(float(proc.mean()), 2),
                                "process_ms_p95": round(float(np.quantile(proc, 0.95)), 2),
                                "timed_equals_untimed": dec == dec0}
        print(name, res["configs"][name], flush=True)
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
