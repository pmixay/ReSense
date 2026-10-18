"""Compare corrected history accounting with original replay and ordinary controls."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
FIELDS = ("decision", "dets", "warns", "nearest", "clear", "monitored", "n_points")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def semantic(row):
    result = deepcopy(row)
    for key in ("decode_ms", "detect_ms", "total_ms"):
        result.pop(key, None)
    messages = result["msgs"]
    if any(m.startswith("latency p95 ") for m in messages):
        result["msgs"] = [m for m in messages if not m.startswith("latency p95 ")]
        if result["level"] == "warn":
            result["level"] = result["dlevel"]
    event = result["mount_detail"].get("orientation_replay", {})
    for key in ("replay_ms", "physical_call_ms", "physical_cpu_ms", "bytes"):
        event.pop(key, None)
    return result


def compare(left, right):
    if len(left) != 201 or len(right) != 201:
        raise ValueError("incomplete real recording")
    fields = {}
    for a, b in zip(left, right):
        if a["i"] != b["i"] or a["stamp"] != b["stamp"]:
            raise ValueError("frame identity mismatch")
        aa, bb = semantic(a), semantic(b)
        for key in aa.keys() | bb.keys():
            if aa.get(key) != bb.get(key):
                fields.setdefault(key, []).append(a["i"])
    return fields


def main():
    current = HERE / "orientation_bound_fix"
    previous = HERE / "orientation_replay_candidate"
    current_summary = json.loads((current / "summary.json").read_text())
    previous_summary = json.loads((previous / "summary.json").read_text())
    prior_cases = {c["name"]: c for c in previous_summary["cases"]}
    results = {}
    for case in current_summary["cases"]:
        name = case["name"]
        a_path, b_path = previous / f"{name}.jsonl", current / f"{name}.jsonl"
        if sha(a_path) != prior_cases[name]["output_sha256"] or sha(b_path) != case["output_sha256"]:
            raise ValueError("capture hash differs")
        a, b = rows(a_path), rows(b_path)
        differences = compare(a, b)
        safety = {key: [left["i"] for left, right in zip(a, b) if left[key] != right[key]] for key in FIELDS}
        if any(safety.values()):
            raise ValueError(f"corrected source changed safety outputs: {name}: {safety}")
        unexpected = set(differences) - {"curv", "track_detail", "mount_rotation"}
        if unexpected:
            raise ValueError(f"unreviewed output differences: {name}: {unexpected}")
        numeric = {}
        for key in a[0]["track_detail"]:
            if any(left["track_detail"][key] != right["track_detail"][key] for left, right in zip(a, b)):
                numeric["track_detail." + key] = max(
                    float(np.max(np.abs(np.asarray(left["track_detail"][key]) - np.asarray(right["track_detail"][key]))))
                    for left, right in zip(a, b))
        numeric["mount_rotation"] = max(
            float(np.max(np.abs(np.asarray(left["mount_rotation"]) - np.asarray(right["mount_rotation"]))))
            for left, right in zip(a, b))
        events = [{"frame": row["i"], **row["mount_detail"]["orientation_replay"]}
                  for row in b if "orientation_replay" in row["mount_detail"]]
        results[name] = {"frames": len(b), "non_timing_differences": differences,
                         "safety_field_changes": safety, "max_absolute_unrounded_differences": numeric,
                         "old_raw_sha256": sha(a_path), "corrected_raw_sha256": sha(b_path),
                         "corrected_replay_events": events}
    ordinary_path = HERE / "orientation_obstacle/baseline.jsonl"
    old, new = rows(ordinary_path), rows(current / "baseline.jsonl")
    ordinary_changes = compare(old, new)
    safety_changes = {k: [a["i"] for a, b in zip(old, new) if a[k] != b[k]] for k in FIELDS}
    if any(safety_changes.values()):
        raise ValueError("ordinary baseline safety output changed")
    output = {
        "status": "SAFETY_FIELDS_IDENTICAL_UNROUNDED_DIFFERENCES_RECORDED", "cases": results,
        "rows_compared_against_previous_replay": 1809,
        "ordinary_baseline": {"source_commit": "9b92df5", "frames": 201,
                              "raw_sha256": sha(ordinary_path), "safety_field_changes": safety_changes,
                              "all_field_differences": ordinary_changes,
                              "added_readiness_field": "mount_detail.orientation_confirmed=true"},
        "excluded_from_corrected_vs_previous": [
            "decode/detect/total timing and latency-only health warning text/promotion",
            "replay physical/replay timing and conservative bytes charge (reported as full events separately)",
        ],
        "source_hashes": current_summary["source_hashes"],
        "source_commit": "7b7b02c9b535d2b03d053df1b309301b619269ad",
        "script_sha256": sha(Path(__file__)),
        "timing_note": "One CPU under concurrent jobs and explicit isolated-window pause; not a throughput benchmark",
        "floating_point_note": "Unrounded coefficient/rotation differences are retained with exact maxima; no exact geometry equality or cause attribution is claimed across the earlier and corrected executions.",
    }
    (current / "previous_and_ordinary_comparison.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "corrected_vs_previous_rows": 1809,
                      "ordinary_safety_changes": safety_changes, "ordinary_all_field_changes": ordinary_changes}))


if __name__ == "__main__":
    main()
