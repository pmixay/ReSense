#!/usr/bin/env python3
"""Latency of the speed paths, interleaved on the same frames in one process.

    taskset -c 3 env OMP_NUM_THREADS=1 python scripts/speed_timing.py --bag roundT_squareT_pressureGate_squareT \\
        --start 100 --limit 150 --ref out/speed --repeat 3

Three detectors with their own state see every frame in rotating order (ABC, BCA, CAB, ...):
``none`` (the shipped path), ``estimated`` (``accumulation.estimate_speed: true``) and ``given``
(the ICP reference speed of ``scripts/speed_reference.py`` handed in, as odometry). Printed per
variant: median and p95 of the total per-frame time, the median of the egomotion and
accumulate stages, and the median per-frame difference to ``none``.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--bag", required=True)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, default=150)
    ap.add_argument("--ref", default="")
    ap.add_argument("--repeat", type=int, default=3)
    a = ap.parse_args()
    from eval_real import nominal_stamps, reference_speeds
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.io import _natural_key, load_cache_stamps
    files = sorted(glob.glob(os.path.join(a.cache, a.bag, "*.npy")), key=_natural_key)
    stamps = nominal_stamps(load_cache_stamps(os.path.join(a.cache, a.bag)))
    spd = reference_speeds(os.path.join(a.ref, f"{a.bag}.jsonl"), len(files)) if a.ref else [None] * len(files)
    sel = list(range(a.start, min(len(files), a.start + a.limit)))
    cfg0 = DetectorConfig()
    frames = [frame_from_compact(np.load(files[i]), cfg0.sensor,
                                 stamp=stamps.get(os.path.splitext(os.path.basename(files[i]))[0], i * 0.1))
              for i in sel]
    names = ["none", "estimated", "given"]
    res = {n: {"total": [], "egomotion": [], "accumulate": [], "cluster": []} for n in names}
    for rep in range(a.repeat):
        dets = {"none": Detector(DetectorConfig()),
                "estimated": Detector(DetectorConfig.from_dict({"accumulation": {"estimate_speed": True}})),
                "given": Detector(DetectorConfig())}
        for k, (i, fr) in enumerate(zip(sel, frames)):
            order = names[k % 3:] + names[:k % 3]
            for n in order:
                r = dets[n].process(fr, ego_speed=spd[i] if n == "given" else None)
                if k >= 5:                      # skip the first frames (calibration seeds, warm-up)
                    for key in res[n]:
                        res[n][key].append(r.timing_ms.get(key, 0.0))
    base = np.array(res["none"]["total"])
    print(f"{a.bag} frames {len(sel)} x {a.repeat}")
    for n in names:
        t = np.array(res[n]["total"])
        print(f"  {n:10s} total median {np.median(t):6.1f} p95 {np.percentile(t, 95):6.1f} ms | egomotion {np.median(res[n]['egomotion']):5.2f} "
              f"accumulate {np.median(res[n]['accumulate']):5.2f} cluster {np.median(res[n]['cluster']):5.2f} ms | "
              f"per-frame diff to none: median {np.median(t - base):+5.1f} ms")


if __name__ == "__main__":
    main()
