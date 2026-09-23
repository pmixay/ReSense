#!/usr/bin/env python3
"""How stable is the per-frame mount measurement along a recording? (EXPERIMENTS.md section 6)

Runs the detector over cached frames with the calibration off and measures, every
``--every`` frames, the roll and pitch the calibrator would see (``observe_mount``) together
with the track curvature. Then asks: how far is the median of ``n`` observations, taken every
``k`` frames from a random start, from the median of the whole recording - the error a fresh
calibration would freeze.

    python scripts/mount_survey.py --npy /data/cache/new_data --pieces 8 --out out/mount_survey.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np


def piece(job):
    files, every, config = job
    sys.path.insert(0, os.getcwd())
    from resense.calibration import observe_mount
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    cfg = DetectorConfig.from_yaml(config)
    cfg.calibration.enabled = False
    det = Detector(cfg)
    out = []
    for i, f in enumerate(files):
        stem = os.path.splitext(os.path.basename(f))[0]
        fr = frame_from_compact(np.load(f), cfg.sensor, frame_id=stem)
        det.process(fr)
        if i % every == 0 and i > 10:
            ob = observe_mount(fr.xyz, cfg.track, det.track, cfg.calibration.min_rail_score)
            out.append([stem, bool(ob.ok), float(np.degrees(ob.roll)) if ob.ok else None,
                        float(np.degrees(ob.pitch)) if ob.ok else None, float(det.track.curvature)])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npy", required=True)
    ap.add_argument("--pieces", type=int, default=1, help="parallel pieces (a fresh detector each)")
    ap.add_argument("--every", type=int, default=5)
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    from resense.io import _natural_key
    files = sorted(glob.glob(os.path.join(a.npy, "*.npy")), key=_natural_key)
    parts = [(list(p), a.every, a.config) for p in np.array_split(np.array(files), a.pieces)]
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = [r for part in ex.map(piece, parts) for r in part]
    roll = np.array([r[2] if r[1] else np.nan for r in rows])
    ok = np.isfinite(roll)
    k = np.abs(np.array([r[4] for r in rows]))
    ref = float(np.nanmedian(roll))
    summary = {"observations": int(ok.sum()), "roll_median": round(ref, 2),
               "roll_p10_p90": [round(float(v), 2) for v in np.nanpercentile(roll, [10, 90])], "by_curvature": {}, "windows": {}}
    for lo, hi in [(0, 2e-4), (2e-4, 1e-3), (1e-3, 1.0)]:
        m = ok & (k >= lo) & (k < hi)
        if m.any():
            summary["by_curvature"][f"{lo:g}-{hi:g}"] = [int(m.sum()), round(float(np.median(roll[m])), 2),
                                                        *[round(float(v), 2) for v in np.percentile(roll[m], [10, 90])]]
    for n_obs, spacing in [(5, 1), (20, 2), (20, 4), (40, 2)]:     # spacing in survey samples (x --every frames)
        errs = []
        for s in range(0, len(roll) - n_obs * spacing, 3):
            w = roll[s:s + n_obs * spacing:spacing]
            w = w[np.isfinite(w)]
            if len(w) >= 0.7 * n_obs:
                errs.append(abs(float(np.median(w)) - ref))
        e = np.array(errs)
        summary["windows"][f"{n_obs} obs every {spacing * a.every} frames"] = {
            "p50": round(float(np.median(e)), 2), "p90": round(float(np.percentile(e, 90)), 2), "max": round(float(e.max()), 2)}
    print(json.dumps(summary, indent=1))
    if a.out:
        json.dump({"summary": summary, "rows": rows}, open(a.out, "w"))


if __name__ == "__main__":
    main()
