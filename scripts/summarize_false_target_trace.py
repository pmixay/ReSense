#!/usr/bin/env python3
"""Summarize replayed ride STOP identities by current point support and LiDAR channels.

    python scripts/summarize_false_target_trace.py --trace TRACE/trace.json \
        --inventory SCENES/inventory.json --out ANALYSIS/false_alarm_analysis.json

The organizers confirmed that new_data has no obstacles. A track may still STOP after a miss;
its last cluster and ring_count then describe an earlier frame, not a new observation.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from statistics import median


def describe(event):
    alarm = set(event["alarm_frame_indices"])
    records = [r for r in event["timeline"] if r["piece_frame"] in alarm]
    assert len(records) == len(alarm) and all(r["alarm"] for r in records)
    fresh = [r for r in records if r["misses"] == 0]
    strict = [r for r in fresh if r["cluster"]["kind"] != "low" and r["cluster"]["n_gauge"] > 0]
    low = [r for r in fresh if r["cluster"]["kind"] == "low"]
    off_gauge = [r for r in fresh if r["cluster"]["kind"] != "low" and r["cluster"]["n_gauge"] == 0]
    rings = [r["cluster"]["ring_count"] for r in strict]
    if rings and min(rings) >= 2:
        ring_class = "all_multi"
    elif rings and max(rings) == 1:
        ring_class = "all_single"
    elif rings:
        ring_class = "mixed"
    else:
        ring_class = "no_fresh_strict_corridor_support"
    distances = [r["cluster"]["distance"] for r in records]
    onset = records[0]
    first = onset["cluster"]
    return {
        "key": event["key"], "first_alarm_frame": onset["frame_id"],
        "alarm_track_frames": len(records), "range_m": [round(min(distances), 1), round(max(distances), 1)],
        "first_alarm_ring_count": (first["ring_count"] if onset["misses"] == 0
                                   and first["kind"] != "low" and first["n_gauge"] > 0 else None),
        "fresh_strict_ring_class": ring_class,
        "fresh_strict_rings_min_median_max": ([min(rings), median(rings), max(rings)] if rings else None),
        "fresh_strict_frames": len(strict), "fresh_low_frames": len(low),
        "fresh_low_observed_channel_counts": [len(r["observed_ring_ids"]) for r in low],
        "fresh_off_gauge_frames": len(off_gauge), "missed_track_frames": len(records) - len(fresh),
        "any_low_object_support": bool(low), "any_thin_support_at_stop": any(r["cluster"]["thin"] for r in records),
    }


def summarize(trace, inventory):
    assert trace["frames"] == inventory["frames"] == 11271
    assert not trace["detection_mismatch_frames"]
    assert len(trace["events"]) == inventory["alarm_events"]
    detail = [describe(event) for event in trace["events"]]
    assert {d["key"] for d in detail} == {e["key"] for e in inventory["events"]}
    counts = Counter()
    for row in detail:
        far = row["range_m"][1] >= 60
        counts["events"] += 1
        counts["alarm_track_frames"] += row["alarm_track_frames"]
        counts["fresh_strict_frames"] += row["fresh_strict_frames"]
        counts["fresh_low_frames"] += row["fresh_low_frames"]
        counts["fresh_off_gauge_frames"] += row["fresh_off_gauge_frames"]
        counts["missed_track_frames"] += row["missed_track_frames"]
        counts["near_events" if not far else "far_events"] += 1
        if not far and row["any_low_object_support"]:
            counts["near_with_low"] += 1
        if far:
            counts["far_ring_" + row["fresh_strict_ring_class"]] += 1
        counts["far_onset_multi"] += int(far and row["first_alarm_ring_count"] is not None
                                            and row["first_alarm_ring_count"] >= 2)
        counts["far_onset_single"] += int(far and row["first_alarm_ring_count"] == 1)
        counts["far_onset_no_strict_support"] += int(far and row["first_alarm_ring_count"] is None)
        counts["far_80m_or_more"] += int(row["range_m"][1] >= 80)
        counts["low_events_with_2plus_observed_channels"] += int(any(x >= 2 for x in row["fresh_low_observed_channel_counts"]))
        counts["events_with_thin_at_stop"] += int(row["any_thin_support_at_stop"])
    assert counts["alarm_track_frames"] == sum(row["alarm_frames"] for row in inventory["events"])
    return {"method": "Full replay matches the source JSONL on every frame; strict-gauge ring_count is current-frame corridor-only. Missing tracks and low clusters are counted separately.",
            "frames": inventory["frames"], "alarm_frames": inventory["alarm_frames"],
            "alarm_events": inventory["alarm_events"], "stop_episodes": inventory["stop_episodes"],
            "counts": dict(counts), "events": detail,
            "limits": ["Events are track identities per independent replay chunk; several identities may STOP in the same frame.",
                       "Scene plots show geometry, not surveyed identities of individual surfaces.",
                       "Low-object ring_count is a placeholder: observed raw channel counts include all points, not just strict-gauge points."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    data = summarize(json.loads(args.trace.read_text(encoding="utf-8")),
                     json.loads(args.inventory.read_text(encoding="utf-8")))
    data["trace_sha256"] = hashlib.sha256(args.trace.read_bytes()).hexdigest()
    data["inventory_sha256"] = hashlib.sha256(args.inventory.read_bytes()).hexdigest()
    args.out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(data["counts"], indent=2))


if __name__ == "__main__":
    main()
