#!/usr/bin/env python3
"""Summarize retained oracle diagnostics without re-running geometry or clustering."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path


def summarize(data):
    totals = defaultdict(Counter)
    source_rows, backgrounds, residuals = [], [], []
    history, displacement = [], 0.
    for row in data["rows"]:
        displacement += (row["speed_supplied_mps"] or 0.) * row["dt_s"]
        history.append((row["frame"], row["source_distance_m"], displacement))
        history = history[-5:]
        residuals.append({"frame": row["frame"], "residuals_m": [
            {"source_frame": frame, "x_residual_m": x - (displacement - shift) - row["source_distance_m"]}
            for frame, x, shift in history]})
        for v in row["variants"]:
            key = f"{v['mode']}:window{v['window']}:bounded{int(v['bounded'])}"
            total = totals[key]
            total["frames"] += 1
            total["source_strict_support_at_scaled_bar"] += v["source_strict_voxels"] >= v["effective_gauge_min"]
            source_gauge = []
            for c in v["cluster_records"]:
                if c["result"] is not None and c["result"]["zone"] == "gauge":
                    total["gauge_candidates"] += 1
                    record = {"frame": row["frame"], "source_distance_m": row["source_distance_m"],
                              "variant": key, **c}
                    if c["source_raw"]:
                        source_gauge.append(c)
                        source_rows.append(record)
                    elif "background" in v["mode"]:
                        backgrounds.append(record)
                if c["source_raw"] and c["result"] is None:
                    total["source_rejected:" + str(c["return_condition"])] += 1
                elif c["source_raw"] and c["result"]["reason"]:
                    total["source_advisory:" + c["result"]["reason"]] += 1
            total["source_gauge_frames"] += bool(source_gauge)
            for threshold in (70, 100):
                if row["source_distance_m"] <= threshold:
                    continue
                total[f"visible_above_{threshold}m"] += 1
                total[f"source_gauge_frames_above_{threshold}m"] += bool(source_gauge)
                total[f"pure_source_gauge_frames_above_{threshold}m"] += any(
                    c["source_raw"] == c["raw"] for c in source_gauge)
                total[f"three_source_frame_gauge_above_{threshold}m"] += any(
                    len(c["source_frames"]) >= 3 for c in source_gauge)
    return {"mode": data["mode"], "production_changed": False, "STOP_gain_measured": False,
            "totals": {k: dict(v) for k, v in sorted(totals.items())},
            "source_gauge_records": source_rows, "paired_background_gauge_records": backgrounds,
            "oracle_x_alignment_residuals": residuals}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    with gzip.open(args.input, "rt") as f:
        result = summarize(json.load(f))
    result["input_sha256"] = hashlib.sha256(Path(args.input).read_bytes()).hexdigest()
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
