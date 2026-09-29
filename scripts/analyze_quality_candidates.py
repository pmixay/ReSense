#!/usr/bin/env python3
"""Validate and compare the fixed 8-piece ride + set O local replay, without replaying.

Reuse the existing object, clear-distance, monitoring and timing scorers. This is a
local diagnostic, not the full regression gate. Exit 0 means valid inputs (and,
with --require-parity, identical semantic outputs), not candidate acceptance.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.metrics import load_gt  # noqa: E402
from scripts.analyze_cross_ring_measurement import episodes, quantiles, timing  # noqa: E402
from scripts.quality_acceptance import aligned, monitoring_cost, read_rows  # noqa: E402
from scripts.score_clear_distance import clear_stats, decision, overclaim  # noqa: E402
from scripts.score_fake_objects import score  # noqa: E402

COUNTS = {"new_data": 11271, "cloud_with_fake_obj": 1510}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def finite_tree(value):
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite numeric value")
    if isinstance(value, dict):
        for child in value.values():
            finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            finite_tree(child)


def expected_pieces(audit_dir):
    """Use audited frame identities/stamps; do not silently synthesize timestamps."""
    audit = json.loads((audit_dir / "audit.json").read_text(encoding="utf-8"))
    pieces, provenance = {}, {}
    for bag, count in COUNTS.items():
        path = audit_dir / f"{bag}_cache_manifest.json"
        digest = sha(path)
        if digest != audit[bag]["cache_manifest_sha256"]:
            raise ValueError(f"{bag}: cache manifest hash differs from audit")
        entries = json.loads(path.read_text(encoding="utf-8"))
        finite_tree(entries)
        if len(entries) != count or audit[bag]["frames"] != count:
            raise ValueError(f"{bag}: expected {count} audited frames")
        if [e["name"] for e in entries] != [f"{bag}_{i:04d}.npy" for i in range(count)]:
            raise ValueError(f"{bag}: audited frame order/identity differs")
        if any(b["stamp"] <= a["stamp"] for a, b in zip(entries, entries[1:])):
            raise ValueError(f"{bag}: nonmonotonic audited timestamps")
        n = 8 if bag == "new_data" else 1
        offset = 0
        for k in range(n):
            size = count // n + int(k < count % n)
            name = f"{bag}_{k}" if n > 1 else bag
            pieces[name] = entries[offset:offset + size]
            offset += size
        provenance[bag] = {"manifest": str(path), "sha256": digest, "frames": count}
    return pieces, provenance


def validate_piece(name, rows, expected):
    if len(rows) != len(expected):
        raise ValueError(f"{name}: frame count differs from audit")
    for i, (row, entry) in enumerate(zip(rows, expected)):
        finite_tree(row)
        if row["frame"] != i or row["frame_id"] != Path(entry["name"]).stem:
            raise ValueError(f"{name}: frame identity/order differs from audit at {i}")
        if abs(row["stamp"] - entry["stamp"]) > 1e-6:
            raise ValueError(f"{name}: timestamp differs from audit at {i}")
        if type(row["obstacle"]) is not bool or type(row["warning"]) is not bool:
            raise ValueError(f"{name}: decision flags must be booleans")
        for flag, field in (("obstacle", "detections"), ("warning", "warnings")):
            if not isinstance(row[field], list) or row[flag] != bool(row[field]):
                raise ValueError(f"{name}: {flag}/{field} inconsistent")
            for item in row[field]:
                if type(item["id"]) is not int:
                    raise ValueError(f"{name}: missing integer track ID")
                float(item["distance"])
        h = row["health"]
        if h["level"] not in ("ok", "warn", "error") or h["decision_level"] not in ("ok", "warn", "error"):
            raise ValueError(f"{name}: invalid health level")
        for value in (row["clear_distance"], h["monitored_range"], row["timing_ms"]["total"]):
            if not math.isfinite(float(value)) or float(value) < 0:
                raise ValueError(f"{name}: invalid range/latency")


def event_stats(pieces):
    """A piece boundary resets both identity and STOP-episode state."""
    return {
        "frames": sum(len(rows) for rows in pieces.values()),
        "alarm_frames": sum(episodes(rows)["frames"] for rows in pieces.values()),
        "stop_episodes": sum(episodes(rows)["episodes"] for rows in pieces.values()),
        "alarm_events": sum(len({d["id"] for r in rows if r["obstacle"] for d in r["detections"]})
                            for rows in pieces.values()),
        "track_alarm_frames": sum(len({d["id"] for d in r["detections"]})
                                  for rows in pieces.values() for r in rows),
    }


def load_run(directory, expected):
    names = {p.name.removesuffix(".gz").removesuffix(".jsonl")
             for p in directory.glob("*.jsonl*")
             if p.name.startswith(("new_data", "cloud_with_fake_obj"))}
    if names != set(expected):
        raise ValueError(f"{directory}: unexpected/missing capture names: {names ^ set(expected)}")
    rows, provenance = {}, {}
    for name, entries in expected.items():
        rows[name], provenance[name] = read_rows(directory, name)
        validate_piece(name, rows[name], entries)
    summary_path = directory / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("given_speed") or summary.get("speed_ref") or summary.get("nominal_stamps"):
        raise ValueError("replay must retain the audited receive stamps and default speed input")
    for bag in COUNTS:
        subset = {k: v for k, v in rows.items() if k == bag or k.startswith(bag + "_")}
        stats = event_stats(subset)
        for key in ("frames", "alarm_frames", "alarm_events"):
            if summary["bags"][bag][key] != stats[key]:
                raise ValueError(f"{bag}: summary {key} disagrees with capture")
    provenance["summary"] = {"path": str(summary_path), "sha256": sha(summary_path)}
    provenance["config"] = {"path": str(directory / "config.yaml"), "sha256": sha(directory / "config.yaml")}
    return rows, provenance


def semantic(row):
    """Strict default parity: retain IDs, ages, model, ranges and decision health.

    Exclude only clock-dependent timing fields and latency-only diagnostic text.
    Preserve FAULT and the node decision even when health.level is removed.
    """
    out = {k: v for k, v in row.items() if k not in ("timing_ms", "health")}
    h = row["health"]
    out["health"] = {k: v for k, v in h.items() if k not in ("level", "latency_p95_ms", "messages")}
    out["health"]["messages"] = [m for m in h.get("messages", []) if not m.startswith("latency p95 ")]
    out["health"]["fault"] = h["level"] == "error"
    out["decision"] = decision(row)
    return out


def summarize(pieces, gt):
    out = {}
    for bag in COUNTS:
        subset = {k: v for k, v in pieces.items() if k == bag or k.startswith(bag + "_")}
        rows = [r for part in subset.values() for r in part]
        out[bag] = {
            **event_stats(subset), "pieces": {k: event_stats({k: v}) for k, v in subset.items()},
            "timing_ms": timing(rows), "clear": clear_stats(rows),
            "monitored_range_m": quantiles([r["health"]["monitored_range"] for r in rows]),
            "health_levels": dict(Counter(r["health"]["level"] for r in rows)),
        }
    objects, background = score(pieces["cloud_with_fake_obj"], gt)
    out["set_O"] = {"objects": objects, "background": background,
                    "overclaim": overclaim(pieces["cloud_with_fake_obj"], gt)}
    return out


def analyze(reference, candidate, audit_dir, labels):
    expected, inputs = expected_pieces(audit_dir)
    refs, rp = load_run(reference, expected)
    cands, cp = load_run(candidate, expected)
    changed, decisions, costs = {}, {}, {}
    for name in expected:
        a, b = refs[name], cands[name]
        aligned(a, b)
        changed[name] = [x["frame_id"] for x, y in zip(a, b) if semantic(x) != semantic(y)]
        decisions[name] = [x["frame_id"] for x, y in zip(a, b) if decision(x) != decision(y)]
        costs[name] = monitoring_cost(a, b, max_extra_pp=2.3, min_range_fraction=0.96)
    gt = load_gt(str(labels))
    return {
        "schema": "resense-quality-candidates-local-v1", "input_validation_passed": True,
        "full_acceptance_asserted": False,
        "semantic_parity_passed": not any(changed.values()),
        "semantic_difference_frames": changed, "node_decision_difference_frames": decisions,
        "inputs": inputs, "labels": {"path": str(labels), "sha256": sha(labels)},
        "provenance": {"reference": rp, "candidate": cp},
        "reference": summarize(refs, gt), "candidate": summarize(cands, gt),
        "monitoring_cost_by_piece": costs,
        "note": "Metrics require protocol review; no full gate, cache-byte rehash, holdout or acceptance is implied.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=Path("labels/cloud_with_fake_obj.json"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-parity", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = analyze(args.reference, args.candidate, args.audit_dir, args.labels)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.error(str(exc))
    text = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
        print(json.dumps({"out": str(args.out), "input_validation_passed": True,
                          "semantic_parity_passed": report["semantic_parity_passed"],
                          "full_acceptance_asserted": False}))
    else:
        print(text, end="")
    return int(args.require_parity and not report["semantic_parity_passed"])


if __name__ == "__main__":
    raise SystemExit(main())
