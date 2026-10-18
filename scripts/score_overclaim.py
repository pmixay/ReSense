#!/usr/bin/env python3
"""Audit clear-distance overclaims against original and approved C2 profiles.

  python scripts/score_overclaim.py set_O.jsonl --gt labels/cloud_with_fake_obj.json
  python scripts/score_overclaim.py set_O.jsonl --apply-advisory-cap \
    --sensor-model pandar128 --empty doubleT_platform=empty.jsonl --out report.json

Inputs may be full FrameResult JSONL or judge_runner.record JSONL, optionally gzipped.
The exact legacy score_clear_distance definition is retained: visible, plausible,
organizer-intended in-gauge object-frames; the target subset also has >=1 measured
rail-envelope return. Excess must exceed --tol (default 0.5 m). Counts are OBJECT
FRAMES, not unique scan frames. Intended-outside objects are a separate diagnostic.

--require-c2 exits 1 unless every numerical screen target passes on complete Set O
and all five complete empty recordings. A numerical pass alone is not deployment
acceptance: the full gate, node integration and independent review remain separate.
The default original profile retains 90% median clear. The explicitly approved
conservative_2026_10_17 profile records a 65% floor with the qualified Pandar cap.
No detector, node or configuration defaults are changed by this tool.
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from resense.metrics import load_gt  # noqa: E402
from scripts.range_reporting import POLICY, candidate_ranges  # noqa: E402
from scripts.rescore_decisions import normalize_row  # noqa: E402
from scripts.score_clear_distance import clear_stats, overclaim  # noqa: E402

# Full organizer recordings in the published 1.1.0 J1 intake (not arbitrary samples).
EMPTY_FRAMES = {"doubleT_platform": 345, "roundT_doubleT": 252,
                "roundT_pressureGate_roundT": 268,
                "roundT_squareT_pressureGate_squareT": 545,
                "squareT_platform_squareT_switch": 877}
ACCEPTANCE_PROFILES = {"original": .9, "conservative_2026_10_17": .65}


def _finite_nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


def read_results(path):
    """Validate alignment and numeric evidence; never fill absent clear ranges with 0."""
    path = Path(path)
    rows, seen = [], set()
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: expected result mapping")
            if row.get("snapshot_kind", "frame") != "frame":
                continue
            if not all(isinstance(row.get(key), bool) for key in ("obstacle", "warning")):
                raise ValueError(f"{path}:{line_number}: missing/invalid decision flags")
            if "health" not in row and "level" not in row:
                raise ValueError(f"{path}:{line_number}: missing health evidence")
            row = normalize_row(row)
            if "clear_distance" not in row and "clear" in row:
                row = {**row, "clear_distance": row["clear"], "health": {
                    **row["health"], "monitored_range": row.get("monitored"),
                    "clear_distance": row["clear"]}}
            index = row.get("frame")
            if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index in seen:
                raise ValueError(f"{path}:{line_number}: missing/duplicate/invalid frame index")
            if rows and index <= rows[-1]["frame"]:
                raise ValueError(f"{path}:{line_number}: frames must be in increasing order")
            _finite_nonnegative(row.get("clear_distance"), "clear_distance")
            if not isinstance(row.get("health"), dict):
                raise ValueError(f"{path}:{line_number}: missing health mapping")
            if "level" not in row["health"]:
                raise ValueError(f"{path}:{line_number}: missing health level")
            for key in ("level", "decision_level"):
                if row["health"].get(key, "ok") not in ("ok", "warn", "error"):
                    raise ValueError(f"{path}:{line_number}: invalid health {key}")
            _finite_nonnegative(row["health"].get("monitored_range"), "monitored_range")
            seen.add(index)
            rows.append(row)
    if not rows:
        raise ValueError(f"{path}: no frame results")
    return rows


def score_rows(rows, gt, tol=0.5):
    """Legacy score plus complete residuals and the intended-outside diagnostic."""
    _finite_nonnegative(tol, "tol")
    result = overclaim(rows, gt, tol)
    residuals, all_measured = [], Counter()
    measured_count = 0
    for row in rows:
        frame = row["frame"]
        for label in gt.get(f"{frame:05d}", []):
            if label.get("n_points", 1) <= 0 or not label.get("plausible", True):
                continue
            distance = _finite_nonnegative(label.get("distance"), "label distance")
            measured = label.get("n_in_envelope", 1) > 0
            if measured:
                measured_count += 1
            if row["clear_distance"] <= distance + tol:
                continue
            word = POLICY.decision(row)
            if measured:
                all_measured[word] += 1
            if label.get("in_gauge") and measured:
                residuals.append({"frame": frame, "label": label["label"], "decision": word,
                                  "distance_m": distance, "clear_distance_m": row["clear_distance"],
                                  "excess_m": round(row["clear_distance"] - distance, 3),
                                  "active_advisory_distance_m": POLICY.caution_advisory_distance(row)})
    result["residual_target_object_frames"] = residuals
    result["all_measured_diagnostic"] = {
        "includes_intended_outside": True, "object_frames": measured_count,
        "overclaims_by_decision": dict(sorted(all_measured.items())),
    }
    return result


def reconstructed_judge_score(rows, gt):
    """Explicit reconstruction matching 13.10's 148/694 on the v1.0 capture.

    The original scorer is absent. Matching the published counts establishes a
    compatible definition, not proof that this was the original implementation.
    """
    eligible_frames, object_frames, counts = 0, 0, Counter()
    for row in rows:
        labels = [g for g in gt.get(f"{row['frame']:05d}", [])
                  if g.get("in_gauge") and g.get("n_points", 1) > 0 and g.get("plausible", True)]
        eligible_frames += bool(labels)
        object_frames += len(labels)
        if any(row["clear_distance"] > float(g["distance"]) + 2.0 for g in labels):
            counts[POLICY.decision(row)] += 1
    return {"unit": "unique scan frame", "eligible_scan_frames": eligible_frames,
            "eligible_object_frames": object_frames, "tolerance_m": 2.0,
            "definition": "any visible plausible organizer-intended in-gauge object exceeded by more than 2 m",
            "overclaim_frames": sum(counts.values()), "overclaim_frames_by_decision": dict(sorted(counts.items())),
            "provenance": "reconstructed count-compatible definition; original 13.10 scorer unavailable"}


def compare_rows(rows, *, apply_cap=False, sensor_model="unknown", min_points_far=3, cap_small_target=False,
                 acceptance_profile="original"):
    after = ([candidate_ranges(row, sensor_model=sensor_model, min_points_far=min_points_far,
                               cap_small_target=cap_small_target,
                               profile="conservative_2026_10_17" if acceptance_profile != "original" else "candidate")
              for row in rows] if apply_cap else rows)
    stats = clear_stats(after, rows)
    before_median = statistics.median(row["clear_distance"] for row in rows)
    after_median = statistics.median(row["clear_distance"] for row in after)
    stats["median_retention_ratio_exact"] = after_median / before_median if before_median > 0 else None
    stats["median_before_m_exact"] = before_median
    stats["median_after_m_exact"] = after_median
    stats["decision_rows_unchanged"] = all(POLICY.decision(a) == POLICY.decision(b)
                                          for a, b in zip(rows, after))
    stats["detections_and_warnings_unchanged"] = all(
        all(a.get(key) == b.get(key) for key in ("obstacle", "warning", "detections", "warnings",
                                               "dets", "warns", "nearest", "nearest_distance"))
        for a, b in zip(rows, after))
    return after, stats


def build_report(objects, gt, empty, *, apply_cap=False, sensor_model="unknown", min_points_far=3,
                 cap_small_target=False, tol=0.5, acceptance_profile="original"):
    if acceptance_profile not in ACCEPTANCE_PROFILES:
        raise ValueError(f"unknown acceptance profile: {acceptance_profile}")
    retention_floor = ACCEPTANCE_PROFILES[acceptance_profile]
    retention_check = f"empty_median_clear_retained_ge_{round(retention_floor * 100)}pct"
    options = dict(apply_cap=apply_cap, sensor_model=sensor_model, min_points_far=min_points_far,
                   cap_small_target=cap_small_target, acceptance_profile=acceptance_profile)
    after, object_stats = compare_rows(objects, **options)
    before_score, after_score = score_rows(objects, gt, tol), score_rows(after, gt, tol)
    observed = {row["frame"] for row in objects}
    labelled = {int(key) for key in gt}
    canonical_labels = load_gt(ROOT / "labels/cloud_with_fake_obj.json")
    labels_match = gt == canonical_labels
    complete = observed == labelled == set(range(1510)) and labels_match
    per_empty = {}
    for name, rows in empty.items():
        _, stats = compare_rows(rows, **options)
        stats["complete_recording"] = ([r["frame"] for r in rows] == list(range(EMPTY_FRAMES[name])))
        per_empty[name] = stats
    by_decision = after_score["totals"]["target_by_decision"]
    targets = {
        "original_tolerance_0_5m": "pass" if tol == .5 else "fail",
        "canonical_set_O_labels": "pass" if labels_match else "fail",
        "complete_set_O": "pass" if complete else "fail",
        "caution_target_overclaims_eq_0": ("not_measured" if not complete else
                                           "pass" if not by_decision.get("CAUTION", 0) else "fail"),
        "go_target_overclaims_le_5": ("not_measured" if not complete else
                                     "pass" if by_decision.get("GO", 0) <= 5 else "fail"),
        "complete_five_empty_recordings": "pass" if set(per_empty) == set(EMPTY_FRAMES) and all(
            r["complete_recording"] for r in per_empty.values()) else "not_measured",
        retention_check: "not_measured",
        "observed_decision_rows_unchanged": "pass" if object_stats["decision_rows_unchanged"] and all(
            r["decision_rows_unchanged"] for r in per_empty.values()) else "fail",
        "observed_detection_and_warning_rows_unchanged": "pass" if (
            object_stats["detections_and_warnings_unchanged"] and all(
                r["detections_and_warnings_unchanged"] for r in per_empty.values())) else "fail",
    }
    if acceptance_profile != "original":
        targets["qualified_pandar_cap_with_measured_threshold"] = "pass" if (
            apply_cap and cap_small_target and sensor_model == "pandar128" and min_points_far == 3) else "fail"
    if targets["complete_five_empty_recordings"] == "pass":
        targets[retention_check] = "pass" if all(
            r["median_retention_ratio_exact"] is not None and r["median_retention_ratio_exact"] >= retention_floor
            for r in per_empty.values()) else "fail"
    return {
        "schema": "resense.overclaim.c2_screen.v1",
        "definition": {
            "unit": "object-frame", "tolerance_m": tol,
            "eligible": "n_points > 0, plausible, organizer in_gauge intent",
            "target": "eligible and n_in_envelope > 0 (rail-envelope labels)",
            "overclaim": "clear_distance > object nearest X + tolerance_m",
            "legacy_scorer": "scripts/score_clear_distance.py:overclaim (unchanged)",
            "missing_legacy_visibility_fields": "legacy defaults: visible/plausible/in-envelope",
        },
        "range_candidate_applied": apply_cap,
        "acceptance_profile": acceptance_profile,
        "minimum_empty_median_retention": retention_floor,
        "small_target_cap_applied": cap_small_target,
        "decision_policy": "v1",
        "sensor_model": sensor_model,
        "set_O": {"before": before_score, "after": after_score, "stats": object_stats,
                  "missing_frames": sorted(labelled - observed), "extra_frames": sorted(observed - labelled)},
        "reconstructed_judge_definition": {"before": reconstructed_judge_score(objects, gt),
                                            "after": reconstructed_judge_score(after, gt)},
        "empty_recordings": per_empty, "checks": targets,
        "numerical_screen": "pass" if all(value == "pass" for value in targets.values()) else "fail",
        "acceptance": "numerical screen only; detector integrity, node validation, review and release are separate",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("objects", type=Path)
    parser.add_argument("--gt", type=Path, default=ROOT / "labels/cloud_with_fake_obj.json")
    parser.add_argument("--empty", action="append", default=[], metavar="BAG=JSONL")
    parser.add_argument("--tol", type=float, default=0.5)
    parser.add_argument("--apply-advisory-cap", action="store_true")
    parser.add_argument("--cap-small-target", action="store_true",
                        help="also cap clear to monitored_small (size-qualified range; select acceptance profile)")
    parser.add_argument("--sensor-model", choices=("pandar128", "falcon_prime", "unknown"), default="unknown")
    parser.add_argument("--min-points-far", type=int, default=3)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--write-candidate", type=Path,
                        help="write projected Set O JSONL, usable by score_clear_distance.py")
    parser.add_argument("--require-c2", action="store_true")
    parser.add_argument("--acceptance-profile", choices=tuple(ACCEPTANCE_PROFILES), default="original")
    args = parser.parse_args(argv)
    if args.cap_small_target and not args.apply_advisory_cap:
        parser.error("--cap-small-target requires --apply-advisory-cap")
    if args.require_c2 and args.tol != .5:
        parser.error("--require-c2 fixes the published tolerance at 0.5 m")
    if args.write_candidate and not args.apply_advisory_cap:
        parser.error("--write-candidate requires --apply-advisory-cap")
    try:
        paths, empty = {}, {}
        for value in args.empty:
            name, path = value.split("=", 1)
            if name not in EMPTY_FRAMES or name in empty:
                raise ValueError(f"unknown or duplicated empty recording: {name}")
            paths[name] = Path(path)
            empty[name] = read_results(path)
        inputs = {path.resolve() for path in (args.objects, args.gt, *paths.values())}
        outputs = [path.resolve() for path in (args.out, args.write_candidate) if path is not None]
        if len(set(outputs)) != len(outputs) or any(path in inputs for path in outputs):
            raise ValueError("output paths must be distinct from each other and from input evidence")
        objects = read_results(args.objects)
        report = build_report(objects, load_gt(args.gt), empty,
                              apply_cap=args.apply_advisory_cap, sensor_model=args.sensor_model,
                              min_points_far=args.min_points_far, cap_small_target=args.cap_small_target,
                              tol=args.tol, acceptance_profile=args.acceptance_profile)
        sources = {"objects": args.objects, "labels": args.gt, **paths,
                   "scorer": Path(__file__), "range_reporting": Path(__file__).with_name("range_reporting.py"),
                   "decision_policy": Path(sys.modules[POLICY.__name__].__file__)}
        if args.acceptance_profile != "original":
            sources["acceptance_authorization"] = ROOT / "docs/evidence/c2_acceptance_2026-10-17/ACCEPTANCE_PROFILE.json"
        report["sources"] = {name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                             for name, path in sources.items()}
        output = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(output, encoding="utf-8")
        if args.write_candidate:
            args.write_candidate.parent.mkdir(parents=True, exist_ok=True)
            with args.write_candidate.open("w", encoding="utf-8") as target:
                for row in objects:
                    projected = candidate_ranges(row, sensor_model=args.sensor_model,
                                                 min_points_far=args.min_points_far,
                                                 cap_small_target=args.cap_small_target,
                                                 profile=("conservative_2026_10_17" if args.acceptance_profile != "original"
                                                          else "candidate"))
                    target.write(json.dumps(projected, allow_nan=False) + "\n")
        print(output, end="")
        return int(args.require_c2 and report["numerical_screen"] != "pass")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"invalid evidence: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
