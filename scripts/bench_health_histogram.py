#!/usr/bin/env python3
"""Small histogram-only parity/timing probe on one original PointCloud2 message.

Reads the first PointCloud2 in the first db3 file. No detector or ROS replay is run.
Concurrent-machine timings are exploratory and do not establish runtime acceptance.
"""
from __future__ import annotations

import os

for _variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_variable, "1")

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
from pathlib import Path  # noqa: E402
import sqlite3  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts"), str(ROOT / "ros2_ws/src/resense_ros")]

from detector_freeze import source_digest, source_hashes  # noqa: E402
from resense import _native, health  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.frame import axis_matrix  # noqa: E402
from resense.pointcloud import pointcloud2_to_arrays  # noqa: E402
from resense_ros.fastcloud import packed, parse_pointcloud2  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bag", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=12)
    args = parser.parse_args()
    if not 3 <= args.samples <= 30:
        parser.error("samples must be between 3 and 30 for this bounded probe")
    if Path(health.__file__).resolve() != ROOT / "resense/health.py":
        raise ValueError("probe imported health from a different checkout")
    sources = source_hashes(ROOT)
    config = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    databases = sorted(args.bag.glob("*.db3"))
    if not databases:
        raise ValueError("original db3 bag is required")
    with sqlite3.connect(databases[0].resolve().as_uri() + "?mode=ro", uri=True) as connection:
        record = connection.execute(
            "SELECT m.data FROM messages m JOIN topics t ON t.id=m.topic_id "
            "WHERE t.type='sensor_msgs/msg/PointCloud2' ORDER BY m.timestamp LIMIT 1"
        ).fetchone()
    if record is None:
        raise ValueError("first bag split contains no PointCloud2 message")
    raw = record[0]
    msg = packed(parse_pointcloud2(raw))
    xyz, *_ = pointcloud2_to_arrays(msg, config.sensor.min_range, config.sensor.max_range)
    xyz = xyz @ axis_matrix(config.sensor).astype(np.float32).T
    azimuth = np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0]))
    edges = np.arange(-30.0, 30.0 + 1e-6, config.health.sector_deg)
    previous = lambda: np.histogram(azimuth, bins=edges)[0]  # noqa: E731
    candidate = lambda: health._sector_counts(azimuth, edges)  # noqa: E731
    expected = previous()
    actual = candidate()
    np.testing.assert_array_equal(actual, expected)
    assert actual.dtype == expected.dtype
    timings = {"histogram": [], "sector_counts": []}
    calls = [("histogram", previous), ("sector_counts", candidate)]
    for index in range(args.samples + 2):
        for name, function in calls[::1 if index % 2 else -1]:
            start = time.perf_counter()
            result = function()
            elapsed = (time.perf_counter() - start) * 1000
            np.testing.assert_array_equal(result, expected)
            if index >= 2:
                timings[name].append(elapsed)
    if source_hashes(ROOT) != sources:
        raise ValueError("source changed during probe")
    output = {
        "schema": "resense-health-histogram-probe-v1", "exact_counts_equal": True,
        "scope": "First original cloud, configured axis transform only, no detector/calibration/ROS replay.",
        "timing_status": "Exploratory under concurrent gate load; not performance acceptance.",
        "source_sha256": source_digest(sources), "source_files": sources,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "config_sha256": source_digest(config.to_dict()),
        "runtime": {"python": sys.version, "numpy": np.__version__, "health_import": health.__file__,
                    "native_library": _native.LIBRARY, "native_required": False,
                    "reason": "Only NumPy histogram counting is measured."},
        "input": {"database": databases[0].name, "raw_message_sha256": hashlib.sha256(raw).hexdigest(),
                  "raw_slots": msg.width * msg.height, "kept_points": len(xyz),
                  "values_dtype": str(azimuth.dtype), "edges_dtype": str(edges.dtype)},
        "counts": actual.tolist(), "counts_dtype": str(actual.dtype),
        "measurements": {name: {"samples_ms": values, "mean_ms": float(np.mean(values)),
                                  "p95_ms": float(np.percentile(values, 95))}
                         for name, values in timings.items()},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"exact_counts_equal": True, "samples": args.samples,
                      "timing_status": output["timing_status"]}))


if __name__ == "__main__":
    main()
