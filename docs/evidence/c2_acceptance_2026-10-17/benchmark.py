#!/usr/bin/env python3
"""Informational C2 output-projection cost on the actual available CPU allocation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.range_reporting import candidate_ranges, small_target_limit  # noqa: E402
from scripts.score_overclaim import read_results  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    args = parser.parse_args()
    rows = sorted(read_results(args.results), key=lambda r: len(json.dumps(r)))
    options = dict(sensor_model="pandar128", cap_small_target=True, profile="conservative_2026_10_17")
    small_target_limit.cache_clear()
    projected = candidate_ranges(rows[0], **options)
    cases = {}
    for name, index in (("median_row", len(rows) // 2), ("p95_row", int(.95 * len(rows))), ("largest_row", -1)):
        row, times = rows[index], []
        for _ in range(2000):
            start = time.perf_counter_ns()
            candidate_ranges(row, **options)
            times.append((time.perf_counter_ns() - start) / 1e6)
        times.sort()
        cases[name] = {"frame": row["frame"], "serialized_bytes": len(json.dumps(row)),
                       "iterations": len(times), "p50_ms": statistics.median(times),
                       "p95_ms": times[int(.95 * len(times))], "max_ms": max(times)}
    output = {"scope": "warm range projection only; excludes decode/detection/ROS and is not a throughput claim",
              "range_profile": options, "range_policy": projected["range_policy"],
              "input_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
              "policy_sha256": hashlib.sha256((ROOT / "ros2_ws/src/resense_ros/resense_ros/decision_policy.py").read_bytes()).hexdigest(),
              "cpu_affinity": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
              "os_cpu_count": os.cpu_count(), "cache": small_target_limit.cache_info()._asdict(), "cases": cases}
    (Path(__file__).parent / "benchmark.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
