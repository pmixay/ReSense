#!/usr/bin/env python3
"""Summarize the local cross-ring ablation replay without changing detector outputs."""
import argparse
import json
import math
from pathlib import Path
from statistics import median


def load_rows(directory, bag):
    exact = directory / f"{bag}.jsonl"
    if exact.is_file():
        with exact.open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    paths = sorted(directory.glob(f"{bag}_*.jsonl"), key=lambda p: int(p.stem.rsplit("_", 1)[1]))
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as fh:
            rows.extend(json.loads(line) for line in fh if line.strip())
    return rows


def clean_detection(item):
    # Track IDs and ages are bookkeeping, not detector decision semantics.
    return {k: v for k, v in item.items() if k not in {"id", "age"}}


def decision(row):
    return {
        "obstacle": row.get("obstacle"),
        "warning": row.get("warning"),
        "nearest_distance": row.get("nearest_distance"),
        "detections": [clean_detection(x) for x in row.get("detections", [])],
        "warnings": [clean_detection(x) for x in row.get("warnings", [])],
    }


def structural(row):
    return {k: row.get(k) for k in ("n_candidates", "n_corridor", "n_accumulated")}


def episodes(rows):
    values = [bool(row.get("obstacle")) for row in rows]
    starts = sum(value and (i == 0 or not values[i - 1]) for i, value in enumerate(values))
    return {"frames": sum(values), "episodes": starts}


def quantiles(values):
    values = sorted(float(x) for x in values)
    if not values:
        return {"median": None, "p95": None, "max": None}
    return {"median": round(median(values), 3), "p95": round(values[min(len(values) - 1, math.ceil(.95 * len(values)) - 1)], 3), "max": round(max(values), 3)}


def timing(rows):
    keys = sorted({key for row in rows for key in row.get("timing_ms", {})})
    return {key: quantiles([row["timing_ms"][key] for row in rows if key in row.get("timing_ms", {})]) for key in keys}


def health(rows):
    levels = {}
    decisions = {}
    for row in rows:
        h = row.get("health", {})
        levels[h.get("level")] = levels.get(h.get("level"), 0) + 1
        decisions[h.get("decision_level")] = decisions.get(h.get("decision_level"), 0) + 1
    return {"level": levels, "decision_level": decisions}


def compare(a, b):
    decision_diff = []
    structure_diff = []
    for i, (left, right) in enumerate(zip(a, b)):
        if decision(left) != decision(right):
            decision_diff.append({"frame": i, "left": decision(left), "right": decision(right)})
        if structural(left) != structural(right):
            structure_diff.append(i)
    return {"frames": min(len(a), len(b)), "decision_differences": decision_diff, "structural_difference_frames": structure_diff,
            "length_a": len(a), "length_b": len(b)}


def score_summary(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"background": data["background"], "objects": {
        name: {key: value for key, value in item.items() if key in {
            "in_gauge", "visible_frames", "alarm_frames", "advisory_only_frames", "first_alarm_m",
            "alarm_held_from_m", "first_advisory_or_alarm_m", "false_alarm_frames", "verdict",
        }} for name, item in data["objects"].items()
    }}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    variants = ("source", "base", "relax", "filter", "combined")
    rows = {variant: {bag: load_rows(args.root / variant, bag) for bag in ("new_data", "cloud_with_fake_obj")} for variant in variants}
    result = {"variants": {}, "source_vs_base": {}, "relative_to_base": {}, "scores": {}}
    for variant in variants:
        result["variants"][variant] = {}
        for bag in ("new_data", "cloud_with_fake_obj"):
            current = rows[variant][bag]
            result["variants"][variant][bag] = {
                "frames": len(current), "episodes": episodes(current), "timing_ms": timing(current), "health": health(current),
                "chunk_alarm_frames": [sum(bool(row.get("obstacle")) for row in load_rows(args.root / variant, f"new_data_{i}")) for i in []],
            }
    # Ride chunk counts are useful for the fixed eight-chunk replay.
    for variant in variants:
        result["variants"][variant]["new_data"]["chunk_alarm_frames"] = []
        for i in range(8):
            chunk = load_rows(args.root / variant, f"new_data_{i}")
            result["variants"][variant]["new_data"]["chunk_alarm_frames"].append({"frames": len(chunk), "alarm_frames": sum(bool(r.get("obstacle")) for r in chunk), "episodes": episodes(chunk)["episodes"]})
    result["source_vs_base"] = {bag: compare(rows["source"][bag], rows["base"][bag]) for bag in ("new_data", "cloud_with_fake_obj")}
    for variant in ("relax", "filter", "combined"):
        result["relative_to_base"][variant] = {bag: compare(rows["base"][bag], rows[variant][bag]) for bag in ("new_data", "cloud_with_fake_obj")}
    for variant in variants:
        score = args.root / f"{variant}_fake_score.json"
        if score.is_file():
            result["scores"][variant] = score_summary(score)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"source_vs_base": {bag: {"decision_differences": value["decision_differences"][:3], "count": len(value["decision_differences"])} for bag, value in result["source_vs_base"].items()}, "out": str(args.out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
