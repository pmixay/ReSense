#!/usr/bin/env python3
"""Check the node's fast input path on real recordings, frame by frame (28.09).

For every ``PointCloud2`` message of each bag: the node's path (``resense_ros.fastcloud``: the
serialized bytes parsed, row padding removed, then ``resense.pointcloud.pointcloud2_to_arrays``)
must give exactly what rclpy's path gives (``deserialize_message``, then the same decode): the
same header, layout and payload, and the same xyz / intensity / ring arrays and counts, byte for
byte. It also times the two readings per frame (median, p95). Runs where ROS 2 is (the image):

    docker run --rm -v <bags>:/data:ro resense python3 /opt/resense/scripts/check_fast_input.py \\
        /data/doubleT_obstacle /data/roundT_doubleT [--json out.json]

Exit 0 when every frame of every bag is identical, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import numpy as np


def _stats(values):
    v = np.asarray(values) * 1e3
    return {"median_ms": round(float(np.median(v)), 2), "p95_ms": round(float(np.percentile(v, 95)), 2),
            "max_ms": round(float(v.max()), 2)}


def check_bag(path: str, min_range: float, max_range: float) -> dict:
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from sensor_msgs.msg import PointCloud2

    from resense.pointcloud import pointcloud2_to_arrays
    from resense_ros import fastcloud

    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=path, storage_id=""), rosbag2_py.ConverterOptions("", ""))
    types = {t.name: t.type for t in reader.get_all_topics_and_types()}
    t_ref_msg, t_fast_msg = [], []
    frames, mismatches, points = 0, [], 0
    while reader.has_next():
        topic, raw, _ = reader.read_next()
        if types.get(topic) != "sensor_msgs/msg/PointCloud2":
            continue
        t = time.perf_counter()
        ref = deserialize_message(raw, PointCloud2)
        t_ref_msg.append(time.perf_counter() - t)
        t = time.perf_counter()
        fast = fastcloud.parse_pointcloud2(raw)
        t_fast_msg.append(time.perf_counter() - t)
        same = ((fast.header.stamp.sec, fast.header.stamp.nanosec, fast.header.frame_id)
                == (ref.header.stamp.sec, ref.header.stamp.nanosec, ref.header.frame_id)
                and (fast.height, fast.width, fast.point_step, fast.row_step, fast.is_bigendian, fast.is_dense)
                == (ref.height, ref.width, ref.point_step, ref.row_step, ref.is_bigendian, ref.is_dense)
                and [(f.name, f.offset, f.datatype, f.count) for f in fast.fields]
                == [(f.name, f.offset, f.datatype, f.count) for f in ref.fields]
                and bytes(fast.data) == bytes(memoryview(ref.data)))
        a = pointcloud2_to_arrays(ref, min_range, max_range)
        b = pointcloud2_to_arrays(fastcloud.packed(fast), min_range, max_range)
        same = same and all(u.dtype == v.dtype and u.shape == v.shape and u.tobytes() == v.tobytes()
                            for u, v in zip(a[:3], b[:3])) and a[3:] == b[3:]
        if not same:
            mismatches.append(frames)
        frames += 1
        points = ref.width * ref.height
    return {"bag": path, "frames": frames, "points_per_frame": points, "identical_frames": frames - len(mismatches),
            "mismatched_frames": mismatches[:20],
            "rclpy_deserialize": _stats(t_ref_msg), "fastcloud_parse": _stats(t_fast_msg)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("bags", nargs="+", help="rosbag2 directories")
    ap.add_argument("--min-range", type=float, default=2.5, help="sensor.min_range of configs/default.yaml")
    ap.add_argument("--max-range", type=float, default=250.0, help="sensor.max_range of configs/default.yaml")
    ap.add_argument("--json", help="also write the result here")
    args = ap.parse_args(argv)
    results = [check_bag(b, args.min_range, args.max_range) for b in args.bags]
    ok = True
    for r in results:
        good = r["frames"] > 0 and not r["mismatched_frames"]
        ok &= good
        print(f"{r['bag']}: {r['identical_frames']} of {r['frames']} frames identical "
              f"({r['points_per_frame']} points per frame) - {'PASS' if good else 'FAIL'}")
        for k in ("rclpy_deserialize", "fastcloud_parse"):
            s = r[k]
            print(f"  {k:18s} median {s['median_ms']:6.2f}  p95 {s['p95_ms']:6.2f}  max {s['max_ms']:6.2f} ms")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump({"results": results, "pass": ok}, fh, indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
