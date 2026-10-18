#!/usr/bin/env python3
"""Summarize retained real DDS status; pause time is not a throughput benchmark."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np


def quantiles(values):
    return {f"p{q}": float(np.percentile(values, q)) if values else None
            for q in (50, 95, 99, 100)}


def summarize(directory):
    path = directory / "status.jsonl"
    payload = path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.jsonl.gz').read_bytes())
    rows = [json.loads(line) for line in payload.splitlines()]
    frames = [row for row in rows if row.get("snapshot_kind") == "frame"]
    result = {"status_sha256": hashlib.sha256(payload).hexdigest(),
              "snapshots": len(rows), "processed_frame_snapshots": len(frames),
              "scope": "Actual DDS status at requested playback rates; see control report for intentional pauses; not 10 Hz throughput",
              "profiles": {}}
    for name in sorted({row["sensor_profile"] for row in frames}):
        selected = [row for row in frames if row["sensor_profile"] == name]
        result["profiles"][name] = {
            "frames": len(selected),
            "decisions": dict(Counter(row["decision"] for row in selected)),
            "freshness_reasons": dict(Counter(row["freshness"]["reason"] for row in selected)),
            "valid_freshness_frames": sum(row["freshness"]["valid"] for row in selected),
            "node_decode_detect_latency_ms": quantiles([row["node"]["latency_ms"] for row in selected]),
            "complete_detector_call_ms": quantiles([row["timing_ms"]["total"] for row in selected]),
            "source_age_at_publication_s": quantiles([
                row["freshness"]["source_age_s"] for row in selected
                if row["freshness"].get("source_age_s") is not None]),
            "peak_rss_mb": max(row["node"]["rss_peak_mb"] for row in selected),
            "reported_node_cpu_cores": quantiles([row["node"]["cpu_cores"] for row in selected]),
            "maximum_node_dropped_counter": max(row["node"]["dropped_frames"] for row in selected),
            "maximum_catchup_skipped_counter": max(row["node"]["catchup_skipped"] for row in selected),
            "gauge_valid_frames": sum(row["gauge"]["valid"] for row in selected),
            "gauge_solid_range_within_axis": all(
                row["gauge"]["solid_range_m"] <= row["gauge"]["axis_valid_m"] for row in selected),
            "clear_distance_m": quantiles([row["clear_distance"] for row in selected]),
            "monitored_small_null_frames": sum(row["monitored_small"] is None for row in selected),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    report = summarize(args.directory)
    (args.directory / "status_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
