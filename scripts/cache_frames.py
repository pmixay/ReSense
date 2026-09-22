#!/usr/bin/env python3
"""Cache every N-th PointCloud2 frame of a bag as a compact *.npy (sensor frame).

    python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 10
    python scripts/cache_frames.py /data/new_data/new_data_30.db3 cache/new_data --every 10   # one split file
"""
import argparse
import os

import numpy as np

from resense.io import iter_bag_compact


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bag")
    p.add_argument("out")
    p.add_argument("--every", type=int, default=10)
    p.add_argument("--topic", default=None)
    a = p.parse_args()
    os.makedirs(a.out, exist_ok=True)
    name = os.path.basename(os.path.normpath(a.bag))
    if name.endswith(".db3"):        # a single rosbag2 split file (extended dataset): new_data_30.db3 -> new_data_30_0010.npy
        name = name[:-4]
    n = 0
    for i, stamp, frame_id, arr in iter_bag_compact(a.bag, topic=a.topic, every=a.every):
        np.save(os.path.join(a.out, f"{name}_{i:04d}.npy"), arr)
        n += 1
    print(f"cached {n} frames of {name} to {a.out}")


if __name__ == "__main__":
    main()
