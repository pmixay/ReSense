#!/usr/bin/env python3
"""Replay cached real bags at 10/5 Hz or with a known sensor re-mount.

The rotation is applied to the vehicle-frame cloud before the detector, as in
calib_check.py. The original cache and parameters are never changed. A fresh
detector is used for each bag, and the original frame indices and timestamps
are retained. Keep the set-O holdout out of these runs until parameters freeze.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

# this checkout's resense and scripts/, not an installed copy (26.09: run from a checkout without
# PYTHONPATH it imported the main checkout's package), as scripts/regression_gate.py does
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from eval_real import SIX, summarize  # noqa: E402  (scripts/)

from resense.calibration import rot_x, rot_y  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, frame_from_compact  # noqa: E402
from resense.io import _natural_key, load_cache_stamps  # noqa: E402


def run_bag(job):
    bag, files, stamps, cfg_dict, every, mount, output = job
    detector = Detector(DetectorConfig.from_dict(cfg_dict))
    rotation = {"as_recorded": np.eye(3), "roll_3": rot_x(np.radians(3)),
                "pitch_3": rot_y(np.radians(3))}[mount]
    events = {}
    stop_episodes = 0
    previous_stop = False
    mount_status = {}
    with open(output, "w", encoding="utf-8") as target:
        for position, path in enumerate(files[::every]):
            stem = os.path.splitext(os.path.basename(path))[0]
            index = int(stem.rsplit("_", 1)[1])
            frame = frame_from_compact(np.load(path), detector.cfg.sensor,
                                       stamp=stamps.get(stem, index * .1), frame_id=stem)
            if mount != "as_recorded":
                frame = Frame(xyz=(frame.xyz @ rotation.T).astype(np.float32),
                              intensity=frame.intensity, ring=frame.ring,
                              stamp=frame.stamp, frame_id=frame.frame_id, meta=frame.meta)
            result = detector.process(frame).to_dict()
            result["frame"] = index
            target.write(json.dumps(result) + "\n")
            if result["obstacle"] and not previous_stop:
                stop_episodes += 1
            previous_stop = result["obstacle"]
            for detection in result["detections"]:
                event = events.setdefault(str(detection["id"]), {"first": index, "last": index,
                                                                 "frames": 0, "distance": detection["distance"]})
                event["last"] = index
                event["frames"] += 1
            status = (result.get("mount") or {}).get("status", "unknown")
            mount_status[status] = mount_status.get(status, 0) + 1
    label = "labels/doubleT_obstacle.json" if bag == "doubleT_obstacle" else None
    cfg = detector.cfg
    stats = summarize(bag, [output], label,
                      confirm_hits=cfg.tracking.frames_to_confirm(), frame_dt=cfg.tracking.frame_dt,
                      min_hits=cfg.tracking.confirm_hits, confirm_time_s=cfg.tracking.confirm_time_s,
                      stamp_dt_range=tuple(cfg.accumulation.stamp_dt_range))
    stats.update(stop_episodes=stop_episodes, events=events, mount_status=mount_status)
    return bag, stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--bags", default=",".join(SIX))
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--every", type=int, choices=(1, 2), default=1)
    parser.add_argument("--mount", choices=("as_recorded", "roll_3", "pitch_3"),
                        default="as_recorded")
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)
    cfg = DetectorConfig.from_yaml(args.config)
    with open(args.config, "rb") as source:
        config_sha = hashlib.sha256(source.read()).hexdigest()
    jobs = []
    for bag in args.bags.split(","):
        cache = os.path.join(args.cache, bag)
        files = sorted(glob.glob(os.path.join(cache, "*.npy")), key=_natural_key)
        if not files:
            parser.error(f"no cached frames for {bag}: {cache}")
        jobs.append((bag, files, load_cache_stamps(cache), cfg.to_dict(), args.every,
                     args.mount, os.path.join(args.out, f"{bag}.jsonl")))
    with ProcessPoolExecutor(max_workers=args.jobs) as executor:
        recordings = dict(executor.map(run_bag, jobs))
    report = {"config_sha256": config_sha, "every": args.every, "mount": args.mount,
              "recordings": recordings}
    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as target:
        json.dump(report, target, indent=2)
    for bag, row in recordings.items():
        print(f"{bag:42s} {row['frames']:4d} frames  {row['alarm_frames']:3d} alarms  "
              f"{row['alarm_events']:2d} events  {row['stop_episodes']:2d} STOP episodes  "
              f"mount {row['mount_status']}")


if __name__ == "__main__":
    main()
