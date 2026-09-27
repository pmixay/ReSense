#!/usr/bin/env python3
"""Compare monitoring costs on exactly the frozen gate's frames.

This supplements regression_gate.py; it does not replace its detection metrics.
Both inputs must contain all six bags, set O and eight ride pieces (.jsonl or .jsonl.gz).
Missing, duplicated, reordered or differently timestamped frames are errors.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.score_clear_distance import decision, overclaim  # noqa: E402
from resense.metrics import load_gt  # noqa: E402

EMPTY = ("doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
REQUIRED = ("doubleT_obstacle", *EMPTY, "cloud_with_fake_obj",
            *(f"new_data_{i}" for i in range(8)))


def read_rows(directory: Path, name: str) -> tuple[list[dict], dict]:
    paths = [p for p in (directory / (name + ".jsonl"), directory / (name + ".jsonl.gz")) if p.is_file()]
    if len(paths) != 1:
        raise ValueError(f"{name}: expected exactly one plain or compressed capture in {directory}")
    path = paths[0]
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if not rows:
        raise ValueError(f"{name}: empty capture")
    keys = []
    for row in rows:
        if "frame" not in row or "frame_id" not in row or "stamp" not in row:
            raise ValueError(f"{name}: missing frame identity")
        keys.append((row["frame"], row["frame_id"]))
        for field in ("stamp", "clear_distance"):
            if field not in row or not math.isfinite(float(row[field])):
                raise ValueError(f"{name}: invalid {field}")
        if float(row["clear_distance"]) < 0:
            raise ValueError(f"{name}: negative monitored estimate")
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name}: duplicate frame identity")
    return rows, {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "frames": len(rows)}


def aligned(reference: list[dict], candidate: list[dict]) -> None:
    if len(reference) != len(candidate):
        raise ValueError("frame count differs")
    for a, b in zip(reference, candidate):
        if (a["frame"], a["frame_id"]) != (b["frame"], b["frame_id"]):
            raise ValueError("frame identity/order differs")
        if abs(float(a["stamp"]) - float(b["stamp"])) > 1e-6:
            raise ValueError("frame timestamp differs")


def monitoring_cost(reference: list[dict], candidate: list[dict], max_extra_pp: float = 5.0,
                    min_range_fraction: float = 0.95) -> dict:
    if not reference or len(reference) != len(candidate):
        raise ValueError("monitoring costs require nonempty paired frames")
    before = Counter(decision(r) for r in reference)
    after = Counter(decision(r) for r in candidate)
    # Count newly uncertain frames without cancelling them against recovered frames elsewhere.
    extra = sum(decision(a) not in ("CAUTION", "FAULT") and decision(b) in ("CAUTION", "FAULT")
                for a, b in zip(reference, candidate))
    pp = 100.0 * extra / len(reference)
    base_range = statistics.median(float(r["clear_distance"]) for r in reference)
    new_range = statistics.median(float(r["clear_distance"]) for r in candidate)
    fraction = new_range / base_range if base_range > 0 else (1.0 if new_range >= 0 else 0.0)
    return {"frames": len(reference), "reference_decisions": dict(before), "candidate_decisions": dict(after),
            "newly_uncertain_frames": extra, "newly_uncertain_percentage_points": pp,
            "reference_clear_median_m": base_range, "candidate_clear_median_m": new_range,
            "clear_median_fraction": fraction,
            "passed": pp <= max_extra_pp + 1e-9 and fraction >= min_range_fraction - 1e-9}


def compare(reference: Path, candidate: Path, labels: Path) -> dict:
    refs, candidates, provenance = {}, {}, {}
    for name in REQUIRED:
        refs[name], rp = read_rows(reference, name)
        candidates[name], cp = read_rows(candidate, name)
        aligned(refs[name], candidates[name])
        provenance[name] = {"reference": rp, "candidate": cp}
    costs = {name: monitoring_cost(refs[name], candidates[name]) for name in EMPTY}
    costs["ride"] = monitoring_cost(
        [r for i in range(8) for r in refs[f"new_data_{i}"]],
        [r for i in range(8) for r in candidates[f"new_data_{i}"]])
    gt = load_gt(str(labels))
    previous = overclaim(refs["cloud_with_fake_obj"], gt)
    current = overclaim(candidates["cloud_with_fake_obj"], gt)
    go_overclaims = current["totals"]["target_by_decision"].get("GO", 0)
    return {"schema": "resense-monitoring-acceptance-v1", "inputs": provenance,
            "labels": {"path": str(labels), "sha256": hashlib.sha256(labels.read_bytes()).hexdigest()},
            "limits": {"max_newly_uncertain_percentage_points": 5.0, "min_clear_median_fraction": 0.95},
            "monitoring_cost": costs, "monitoring_cost_passed": all(r["passed"] for r in costs.values()),
            "set_O_reference": previous, "set_O_candidate": current,
            "zero_GO_overclaim_diagnostic_passed": go_overclaims == 0,
            "note": "Set O envelope labels inherit a prior detector rail fit; this diagnostic is not independently surveyed truth. No overall detector acceptance is asserted here."}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--labels", type=Path, default=Path("labels/cloud_with_fake_obj.json"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    try:
        report = compare(a.reference, a.candidate, a.labels)
    except (ValueError, KeyError) as exc:
        p.error(str(exc))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("monitoring_cost_passed", "zero_GO_overclaim_diagnostic_passed")}))


if __name__ == "__main__":
    main()
