#!/usr/bin/env python3
"""Summarize paired reports with v1 physical-label caveats kept separate from old metrics."""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from synthetic_geometry import audit_case
from synthetic_sensitivity import compare_reports, file_hash


def load(path):
    with (gzip.open(path, "rt") if str(path).endswith(".gz") else Path(path).open()) as stream:
        return json.load(stream)


def summarize(report):
    groups = {}
    for encoding in ("float32", "compact16"):
        groups[encoding] = {}
        for group in ("all_registered_positives", "physical_interior", "boundary_only", "physical_outside", "registered_negatives"):
            selected = []
            for case in report["cases"]:
                positive = case["case"]["positive"]
                physical = audit_case(case["case"])
                include = (group == "all_registered_positives" and positive
                           or group == "physical_interior" and positive and physical["classification"] == "interior"
                           or group == "boundary_only" and positive and physical["classification"] == "boundary_only"
                           or group == "physical_outside" and positive and physical["classification"] == "outside"
                           or group == "registered_negatives" and not positive)
                if include:
                    selected.append(case)
            rows = [r for c in selected for r in c["encodings"][encoding]["rows"]]
            metrics = [c["encodings"][encoding]["metrics"] for c in selected]
            groups[encoding][group] = {
                "cases": len(selected), "frames": len(rows),
                "sustained_cases": sum(m["sustained"] for m in metrics),
                "matched_stop_frames": sum(m["matched_stop_frames"] for m in metrics),
                "visible_frames": sum(m["visible_frames"] for m in metrics),
                "stop_frames": sum(m["stop_frames"] for m in metrics),
                "unmatched_stop_frames": sum(m["unmatched_stop_frames"] for m in metrics),
                "stop_episodes": sum(m["stop_episodes"] for m in metrics),
                "clear_overclaim_frames": sum(m["clear_overclaim_frames"] for m in metrics),
                "go_clear_overclaim_frames": sum(r["clear_overclaim"] and r["decision"] == "GO" for r in rows),
                "frames_with_physical_envelope_returns": sum(r["target_returns_in_physical_envelope"] > 0 for r in rows)
                    if rows and all("target_returns_in_physical_envelope" in r for r in rows) else None,
                "never_detected_cases": [c["case"]["name"] for c in selected
                                         if c["case"]["positive"] and c["encodings"][encoding]["metrics"]["matched_stop_frames"] == 0],
            }
    pairs = [(a, b) for case in report["cases"]
             for a, b in zip(case["encodings"]["float32"]["rows"], case["encodings"]["compact16"]["rows"])]
    physical_disagreements = sum(a["target_returns_in_physical_envelope"] != b["target_returns_in_physical_envelope"]
                                 for a, b in pairs) if pairs and all("target_returns_in_physical_envelope" in a
                                 and "target_returns_in_physical_envelope" in b for a, b in pairs) else None
    return {"source": report["source"], "config_sha256": report["config_sha256"],
            "evaluator_sha256": report["evaluator_sha256"],
            "cache_generator_script_sha256": report["cache_generator_script_sha256"],
            "cache_manifest_sha256": report["cache_manifest_sha256"],
            "complete_split": report["complete_split"], "cases": len(report["cases"]),
            "quantization_disagreement_frames": sum(len(c["quantization_disagreement_frames"]) for c in report["cases"]),
            "quantization_physical_envelope_count_disagreement_frames": physical_disagreements,
            "metrics": groups}


def signal_differences(baseline, candidate):
    by_name = {c["case"]["name"]: c for c in baseline["cases"]}
    keys = ("stop", "matched_stop", "unmatched_stop", "matched_ids", "detections", "clear_distance_m", "warning", "decision")
    counts = {encoding: dict.fromkeys(keys, 0) for encoding in ("float32", "compact16")}
    for case in candidate["cases"]:
        old = by_name[case["case"]["name"]]
        for encoding in counts:
            before = old["encodings"][encoding]["rows"]
            after = case["encodings"][encoding]["rows"]
            if len(before) != len(after):
                raise ValueError("cannot compare different per-case frame counts")
            for a, b in zip(before, after):
                if a["frame"] != b["frame"]:
                    raise ValueError("cannot compare different frame indices")
                for key in keys:
                    counts[encoding][key] += a[key] != b[key]
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = load(args.baseline), load(args.candidate)
    report = {"schema": "resense.synthetic_comparison_summary.v1",
              "protocol_sha256": baseline["protocol_sha256"], "split": baseline["split"],
              "summary_script_sha256": file_hash(__file__), "geometry_auditor_sha256": file_hash(Path(__file__).with_name("synthetic_geometry.py")),
              "interpretation": "Original labels and headline metrics are preserved. Physical groups annotate body-interior, boundary-only and outside geometry without relabeling v1. Only v2 has preregistered positive overlap. Synthetic development is not official organizer scoring or real holdout evidence.",
              "baseline_report_file": args.baseline.name, "candidate_report_file": args.candidate.name,
              "baseline_report_sha256": file_hash(args.baseline), "candidate_report_sha256": file_hash(args.candidate),
              "baseline": summarize(baseline), "candidate": summarize(candidate),
              "comparison": compare_reports(baseline, candidate),
              "baseline_candidate_signal_difference_frames": signal_differences(baseline, candidate)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
