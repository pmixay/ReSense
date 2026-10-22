#!/usr/bin/env python3
"""Weaker check (PROTOCOL §3): the learned far axis on the Falcon recording (a standing long-range sensor, no future
labels), against the straight far track of docs/evidence/falcon_long_range_2026-10-19/track_reference.json.

    falcon_axis.py --cache /data/falcon --profile falcon_ros|manual --out out.json [--every 1]

Frames are built as ``falcon_far_range_review_2026-10-21/scripts/scene_run.py --plain`` builds them (crop, axis matrix,
detector reset on stamp gaps). The detector runs with its defaults under the profile (the learned switch is off; the
model is applied offline to each frame's profile and state). Truth at X: the reference line (raw sensor frame,
lateral a + b x, height z0 + c x) rotated by the detector's mount rotation of the frame. Reported per band: base, K2,
the far line (base + far offset) and the model's middle, and the band's coverage, over the frames at --every.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))
import yaml  # noqa: E402

from resense import far_axis as fa  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense_ros.sensor_profiles import apply_sensor_profile  # noqa: E402

TRACK = json.loads((ROOT / "docs/evidence/falcon_long_range_2026-10-19/track_reference.json").read_text())["track"]
BANDS = [(60, 100), (100, 150), (150, 200), (200, 250)]


def build_cfg(profile):
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    cfg.calibration.enabled = True
    cfg, _ = apply_sensor_profile(cfg, profile)
    return cfg


def crop(xyz, lo, hi):
    r2 = xyz[:, 0].astype(np.float32) ** 2
    r2 += xyz[:, 1] * xyz[:, 1]
    r2 += xyz[:, 2] * xyz[:, 2]
    return (r2 >= lo * lo) & (r2 <= hi * hi)


def truth_y(R, R_vs, xq):
    x = np.arange(20.0, 300.0, 1.0)
    p_raw = np.stack([x, TRACK["a"] + TRACK["b"] * x, TRACK["z0"] + TRACK["c"] * x], 1)
    p = (R @ (R_vs @ p_raw.T)).T
    return np.interp(xq, p[:, 0], p[:, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/data/falcon")
    ap.add_argument("--profile", default="falcon_ros")
    ap.add_argument("--out", required=True)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    cache = Path(a.cache)
    meta = json.loads((cache / "meta.json").read_text())
    cfg = build_cfg(a.profile)
    det = Detector(cfg)
    R_vs = axis_matrix(cfg.sensor).astype(np.float64)
    M = fa.FarAxisModel.load(str(ROOT / "resense/models/far_axis_1.3.json"))
    xq = M.query_x
    rows = []
    last = None
    t0 = time.time()
    tl = []
    for i in range(len(meta)):
        m = meta[i]
        stamp = m["stamp"]
        if last is not None:
            gap = stamp - last
            if gap < -0.5 or gap > 30.0:
                det = Detector(cfg)
            elif gap > 1.0:
                det.reset()
        last = stamp
        d = np.load(cache / f"f_{i:05d}.npz")
        xyz, inten = d["xyz"], d["inten"]
        k = crop(xyz, cfg.sensor.min_range, cfg.sensor.max_range)
        det.process(Frame(xyz=xyz[k] @ R_vs.T.astype(np.float32), intensity=inten[k], ring=None, stamp=stamp,
                          frame_id=m["frame_id"], meta={"n_raw": m["n_raw"], "n_near": m["n_near"]}))
        if i % a.every or det.track is None:
            continue
        t1 = time.perf_counter()
        st = fa.model_state(det.track, det.track.curve if cfg.track.axis_joint_union else None, det._far_axis)
        prof = fa.profile(det._frame_xyz, det.track)
        Q = M.predict(fa.query_features(prof, st, xq))
        tl.append((time.perf_counter() - t1) * 1e3)
        b = fa.base_y(st, xq)
        rows.append({"i": i, "truth": truth_y(np.asarray(det.mount_rotation, float), R_vs, xq), "base": b,
                     "k2": b + fa.curve_offset(st, xq), "far": b + fa.far_offset(st, xq),
                     "lo": b + Q[:, 0], "mid": b + Q[:, 1], "hi": b + Q[:, 2], "axis_valid": st["axis_valid"]})
    out = {"profile": a.profile, "frames": len(rows), "wall_s": round(time.time() - t0, 1),
           "learned_ms_p50_p95": [round(float(np.percentile(tl, 50)), 1), round(float(np.percentile(tl, 95)), 1)],
           "bands": {}}
    T = np.array([r["truth"] for r in rows])
    for lo, hi in BANDS:
        c = (xq >= lo) & ((xq < hi) | ((hi == 250) & (xq == 250)))
        e = {k: np.abs(np.array([r[k] for r in rows])[:, c] - T[:, c]).ravel() for k in ("base", "k2", "far", "mid")}
        ins = ((T[:, c] >= np.array([r["lo"] for r in rows])[:, c]) & (T[:, c] <= np.array([r["hi"] for r in rows])[:, c]))
        width = (np.array([r["hi"] for r in rows]) - np.array([r["lo"] for r in rows]))[:, c]
        out["bands"][f"{lo}-{hi}"] = {k: [round(float(np.percentile(v, 50)), 3), round(float(np.percentile(v, 90)), 3)]
                                      for k, v in e.items()}
        out["bands"][f"{lo}-{hi}"].update(coverage=round(float(ins.mean()), 3), band_p50=round(float(np.median(width)), 3),
                                          share_band_le_0_5=round(float((width <= 0.5).mean()), 3))
    json.dump(out, open(a.out, "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
