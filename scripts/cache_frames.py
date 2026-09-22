#!/usr/bin/env python3
"""Cache every N-th PointCloud2 frame of a bag as a compact *.npy (sensor frame).

    python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 10
    python scripts/cache_frames.py /data/new_data/new_data_30.db3 cache/new_data --every 10   # one split file
    python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 1 --int16   # 1.5 MB per frame

``--int16`` writes the quantised cache (``resense.pointcloud.COMPACT16_DTYPE``: centimetres as
int16, intensity and ring as uint8; 8 bytes per point instead of 18), which every reader of
the package (``resense run/eval/inject --npy``) loads transparently. ``--stamps`` also writes
``<name>_stamps.json`` with the bag receive time of every cached frame (the cached files carry
none; per-hour rates and the measured frame interval need it).
"""
import argparse
import json
import os

import numpy as np

from resense.io import iter_bag_compact
from resense.pointcloud import compact_to_compact16


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bag")
    p.add_argument("out")
    p.add_argument("--every", type=int, default=10)
    p.add_argument("--topic", default=None)
    p.add_argument("--int16", action="store_true", help="quantised 8-byte-per-point cache")
    p.add_argument("--stamps", action="store_true", help="write <name>_stamps.json (bag time per frame)")
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    name = os.path.basename(os.path.normpath(a.bag))
    if name.endswith(".db3"):        # a single rosbag2 split file (extended dataset): new_data_30.db3 -> new_data_30_0010.npy
        name = name[:-4]
    n = 0
    stamps = {}
    for i, stamp, frame_id, arr in iter_bag_compact(a.bag, topic=a.topic, every=a.every):
        if a.int16:
            arr = compact_to_compact16(arr)
        np.save(os.path.join(a.out, f"{name}_{i:04d}.npy"), arr)
        stamps[f"{i:04d}"] = stamp
        n += 1
    if a.stamps:
        with open(os.path.join(a.out, f"{name}_stamps.json"), "w", encoding="utf-8") as fh:
            json.dump({"bag": name, "frame_id": frame_id if n else "", "stamps": stamps}, fh)
    print(f"cached {n} frames of {name} to {a.out}")


if __name__ == "__main__":
    main()
