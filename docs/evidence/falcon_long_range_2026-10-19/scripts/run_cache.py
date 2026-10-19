#!/usr/bin/env python3
"""Replay the full-range Falcon cache through the detector as the node does (judge_runner.NodeReplica).

    run_cache.py --cache <dir> --out <prefix> [--profile manual|falcon_ros] [--set sec.key=val ...]
                 [--frames a:b] [--inject <spec.json>]

Decode equivalence: the cache holds the node decode's points out to 600 m; here they are cropped to
``cfg.sensor.max_range`` with the node's float32 range test (``fastcloud.decode``), so with 250 m the
detector receives the node's exact arrays (checked in the cache receipt). ``ring`` is None (no field).
Continuity rules and decision rule as ``judge_runner``. ``--inject`` adds ray-cast targets
(``inject.py``) to each frame in the sensor frame before the crop.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(os.environ.get("RESENSE_REPO", "/home/user/ReSense"))
sys.path.insert(0, str(REPO / "ros2_ws/src/resense_ros"))
sys.path.insert(0, str(REPO / "docs/evidence/judgement_2026-10-13/scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import yaml  # noqa: E402

from judge_runner import CONFIG, record  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense_ros.sensor_profiles import apply_sensor_profile  # noqa: E402


def crop(xyz, lo, hi):
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r2 = x.astype(np.float32) ** 2
    r2 += y * y
    r2 += z * z
    return (r2 >= lo * lo) & (r2 <= hi * hi)


def _apply(cfg, sets):
    for s in sets:
        k, v = s.split("=", 1)
        sec, key = k.split(".", 1)
        setattr(getattr(cfg, sec), key, yaml.safe_load(v))


def build_cfg(profile, sets, pre=()):
    """The node's order: YAML, auto_calibrate, ``pre`` (YAML-level overrides), the sensor profile,
    then ``sets`` (overrides after the profile)."""
    cfg = DetectorConfig.from_yaml(CONFIG)
    cfg.calibration.enabled = True
    _apply(cfg, pre)
    cfg, _ = apply_sensor_profile(cfg, profile)
    for s in sets:
        k, v = s.split("=", 1)
        sec, key = k.split(".", 1)
        setattr(getattr(cfg, sec), key, yaml.safe_load(v))
    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="/home/user/data/falcon")
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default="manual")
    ap.add_argument("--set", action="append", default=[])
    ap.add_argument("--pre", action="append", default=[], help="sec.key=val applied before the profile")
    ap.add_argument("--frames", default="")
    ap.add_argument("--inject", default="")
    a = ap.parse_args()
    cache = Path(a.cache)
    meta = json.loads((cache / "meta.json").read_text())
    lo, hi = (int(v) for v in a.frames.split(":")) if a.frames else (0, len(meta))
    cfg = build_cfg(a.profile, a.set, a.pre)
    det = Detector(cfg)
    R_vs = axis_matrix(cfg.sensor).astype(np.float32)
    injector = None
    if a.inject:
        from inject import Injector
        injector = Injector(json.loads(Path(a.inject).read_text()))
    last, resets, t0 = None, [], time.time()
    with open(a.out + ".jsonl", "w") as fj:
        for i in range(lo, hi):
            m = meta[i]
            stamp = m["stamp"]
            if last is not None:
                gap = stamp - last
                if gap < -0.5 or gap > 30.0:
                    det = Detector(cfg)
                    resets.append((i, "new"))
                elif gap > 1.0:
                    det.reset()
                    resets.append((i, "hole"))
            last = stamp
            d = np.load(cache / f"f_{i:05d}.npz")
            xyz, inten = d["xyz"], d["inten"]
            info = None
            if injector is not None:
                xyz, inten, info = injector.apply(i, d, det)
            k = crop(xyz, cfg.sensor.min_range, cfg.sensor.max_range)
            xyz_v = xyz[k] @ R_vs.T
            frame = Frame(xyz=xyz_v, intensity=inten[k], ring=None, stamp=stamp, frame_id=m["frame_id"],
                          meta={"n_raw": m["n_raw"], "n_near": m["n_near"]})
            t1 = time.perf_counter()
            res = det.process(frame, ego_speed=None)
            r = record(i, m["bag_t"], stamp, res, 0.0, (time.perf_counter() - t1) * 1e3, m["frame_id"], "/iv_points")
            if info is not None:
                r["inj"] = info
            r["mount_rotation"] = np.asarray(det.mount_rotation).tolist()
            r["track_detail"] = res.track.to_dict()
            fj.write(json.dumps(r) + "\n")
    json.dump({"frames": hi - lo, "resets": resets, "wall_s": round(time.time() - t0, 1), "profile": a.profile,
               "set": a.set, "inject": a.inject, "max_range": cfg.sensor.max_range},
              open(a.out + ".meta.json", "w"), indent=1)


if __name__ == "__main__":
    main()
