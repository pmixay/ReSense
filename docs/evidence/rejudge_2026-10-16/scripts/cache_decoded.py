#!/usr/bin/env python3
"""Cache the node-decoded clouds of a bag (sensor frame, after fastcloud.decode's range filter) so the
range / robustness experiments can replay them without the multi-GB bag:
  <out>/f_<idx>.npz : xyz (float32, sensor frame), inten (float32), ring (uint16)
  <out>/meta.json   : per frame header stamp, bag time, frame_id, has_ring, n_raw, n_near
  cache_decoded.py <bag_dir> <out_dir> [--start N] [--end M]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_runner import db3_files, iter_raw  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

p = argparse.ArgumentParser()
p.add_argument("bag")
p.add_argument("out")
p.add_argument("--start", type=int, default=0)
p.add_argument("--end", type=int, default=10 ** 9)
a = p.parse_args()
os.makedirs(a.out, exist_ok=True)
meta = []
i = 0
for db3 in db3_files(a.bag):
    for ts, topic, raw in iter_raw(db3):
        if a.start <= i < a.end:
            msg = fastcloud.parse_pointcloud2(raw)
            xyz, inten, ring, n_raw, n_near = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
            np.savez_compressed(os.path.join(a.out, f"f_{i:05d}.npz"), xyz=xyz, inten=inten, ring=ring)
            meta.append({"i": i, "stamp": msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                         "bag_t": ts / 1e9, "frame_id": msg.header.frame_id, "topic": topic,
                         "has_ring": fastcloud.has_field(msg, "ring"), "n_raw": n_raw, "n_near": n_near})
        i += 1
json.dump(meta, open(os.path.join(a.out, "meta.json"), "w"))
print(a.bag, "->", a.out, len(meta), "frames")
