#!/usr/bin/env python3
"""Time what the ROS node does per frame, without ROS: decode a PointCloud2 payload in the
organizers' exact layout, crop and rotate it, run the detector - on real frames.

The Docker chain (rclpy receive, publish) needs a machine with Docker; this measures the part
of ``detector_node.on_cloud`` that is ours: ``pointcloud2_to_arrays`` (decode + range crop) →
mount rotation → ``Detector.process``. The payload is
rebuilt from a cached real frame (``scripts/cache_frames.py``) in the recordings' layout
(``point_step`` 26: x y z intensity float32, ring uint16, timestamp float64; the dual-return
slots without an echo as (0, 0, 0), ~10 % of a 360° frame - DATASET.md).

    python scripts/bench_node_path.py --npy /data/cache/doubleT_obstacle [--limit 200]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense.io import iter_npy_frames  # noqa: E402
from resense.pointcloud import pointcloud2_to_arrays  # noqa: E402

POINT_DTYPE = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                        "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"],
                        "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
FIELDS = [SimpleNamespace(name=n, offset=o, datatype=d, count=1)
          for n, o, d in (("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4),
                          ("timestamp", 18, 8))]


def message(xyz_s, intensity, ring, stamp, rng):
    n = xyz_s.shape[0]
    n_empty = n // 10
    pts = np.zeros(n + n_empty, dtype=POINT_DTYPE)
    filled = rng.permutation(n + n_empty)[:n]
    pts["x"][filled], pts["y"][filled], pts["z"][filled] = xyz_s[:, 0], xyz_s[:, 1], xyz_s[:, 2]
    pts["intensity"][filled] = intensity
    pts["ring"][filled] = ring
    pts["timestamp"][:] = stamp
    sec = int(stamp)
    return SimpleNamespace(fields=FIELDS, is_bigendian=False, point_step=26, width=pts.size, height=1,
                           data=pts.tobytes(), header=SimpleNamespace(stamp=SimpleNamespace(
                               sec=sec, nanosec=int((stamp - sec) * 1e9)), frame_id="lidar"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--npy", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--config", default=None)
    a = ap.parse_args()
    cfg = DetectorConfig.from_yaml(a.config) if a.config else DetectorConfig()
    det = Detector(cfg)
    rng = np.random.default_rng(0)
    # the cache holds the vehicle frame; the node receives the sensor frame and rotates it back
    R_vs = axis_matrix(cfg.sensor).astype(np.float32)                # p_vehicle = R_vs @ p_sensor
    dec, tot, n_pts = [], [], []
    for i, fr in iter_npy_frames(a.npy, cfg.sensor, limit=a.limit, index_from_name=True):
        xyz_s = (fr.xyz @ np.asarray(R_vs, np.float32)).astype(np.float32)
        msg = message(xyz_s, fr.intensity, fr.ring if fr.ring is not None else np.zeros(len(xyz_s)), 0.1 * i, rng)
        t0 = time.perf_counter()
        xyz, inten, ring, n_raw, n_near = pointcloud2_to_arrays(msg, cfg.sensor.min_range,   # as detector_node.on_cloud
                                                                cfg.sensor.max_range)
        xyz_v = xyz @ R_vs.T
        frame = Frame(xyz=xyz_v, intensity=inten, ring=ring, stamp=0.1 * i, frame_id="lidar",
                      meta={"n_raw": n_raw, "n_near": n_near})
        t1 = time.perf_counter()
        det.process(frame)
        t2 = time.perf_counter()
        dec.append(1e3 * (t1 - t0))
        tot.append(1e3 * (t2 - t0))
        n_pts.append(msg.width)
    dec, tot = np.array(dec), np.array(tot)
    print(f"{os.path.basename(os.path.normpath(a.npy))}: {len(tot)} frames, {int(np.mean(n_pts))} slots per message")
    print(f"  decode + crop + rotate: mean {dec.mean():.1f} ms, p95 {np.percentile(dec, 95):.1f} ms")
    print(f"  decode + detect:        mean {tot.mean():.1f} ms, p95 {np.percentile(tot, 95):.1f} ms, "
          f"max {tot.max():.1f} ms")


if __name__ == "__main__":
    main()
