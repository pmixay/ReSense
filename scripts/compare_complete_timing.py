#!/usr/bin/env python3
"""Strict parity for the registered complete-process timing correction."""
from __future__ import annotations

import argparse
import gzip
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.compare_health_gate import (REQUIRED, capture, effective_config, load,  # noqa: E402
                                        normalized_health, sha, validate_setf)
from scripts.detector_freeze import source_digest, source_hashes  # noqa: E402

STAGES = ("track", "corridor", "egomotion", "accumulate", "cluster", "tracking")
METADATA = ("latency_basis", "latency_sample_age_frames")


def percentile95(values):
    if not values:
        return 0.0
    values = sorted(values)
    rank = 0.95 * (len(values) - 1)
    lower = int(rank)
    return values[lower] + (values[min(lower + 1, len(values) - 1)] - values[lower]) * (rank - lower)


def numeric(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0


def normalized_frame(rows, index, config, *, complete, reset_indices):
    """Validate timing first, then remove only its declared fields and derived effects.

    Every gate capture starts a new detector and has no internal reset. Reset indices are
    registered explicitly; a null sample age elsewhere must never waive a missing sample.
    Capture totals round to 0.01 ms; health p95 rounds to 0.1 ms. The p95 error bound is
    therefore 0.005 + 0.05 ms. Stage-sum bounds count each independently rounded operand.
    """
    if reset_indices != [0]:
        raise ValueError("this gate requires a fresh detector at index 0 and no internal reset")
    row = rows[index]
    timing, health = row["timing_ms"], row["health"]
    keys = set(STAGES) | {"total"} | ({"stages", "health", "result"} if complete else set())
    if set(timing) != keys or not all(numeric(value) for value in timing.values()):
        raise ValueError("unknown, missing or invalid timing fields")
    stage_total = timing["stages"] if complete else timing["total"]
    if abs(sum(timing[key] for key in STAGES) - stage_total) > 0.035000001:
        raise ValueError("six stage intervals do not equal the historical stage total")
    if complete:
        if abs(sum(timing[key] for key in ("stages", "health", "result")) - timing["total"]) > 0.020000001:
            raise ValueError("stages plus health plus result do not equal total")
        if health.get("latency_basis") != "previous_complete_process":
            raise ValueError("invalid or missing latency basis")
        age = health.get("latency_sample_age_frames", "missing")
        if (index == 0 and age is not None) or (index > 0 and (type(age) is not int or age != 1)):
            raise ValueError("invalid or missing latency sample age")
    elif any(key in health for key in METADATA):
        raise ValueError("reference unexpectedly carries complete-process latency metadata")
    end = index if complete else index + 1
    window = max(1, int(config["latency_window"]))
    values = [entry["timing_ms"]["total"] for entry in rows[max(0, end - window):end]]
    if not all(numeric(value) for value in values):
        raise ValueError("invalid timing sample in history")
    p95 = health["latency_p95_ms"]
    if not values and p95 != 0.0:
        raise ValueError("empty latency history must report zero p95")
    if not numeric(p95) or abs(p95 - percentile95(values)) > 0.055000001:
        raise ValueError("health p95 disagrees with the declared captured timing history")
    result = dict(row)
    result.pop("timing_ms")
    # Historical helper validates message grammar, rounding, threshold and derived level.
    # Its index counts supplied samples; complete timing has one fewer sample this frame.
    result["health"] = normalized_health(health, config, index - int(complete))
    if complete:
        for key in METADATA:
            result["health"].pop(key)
    return result


def validate_identity(reference, candidate, registration, identity, source_root):
    baseline_gate, candidate_gate = load(reference / "gate.json"), load(candidate / "gate.json")
    completion = load(candidate / "completion.json")
    if sha(reference / "gate.json") != registration["baseline_gate"]["sha256"]:
        raise ValueError("baseline gate differs from registration")
    if baseline_gate["code"]["commit"] != registration["baseline_gate"]["measured_commit"]:
        raise ValueError("baseline measured commit differs")
    if candidate_gate["code"]["commit"] != identity["commit"] or candidate_gate["code"]["uncommitted_detector_changes"]:
        raise ValueError("candidate is not the frozen clean commit")
    if source_digest(identity["files"]) != identity["source_sha256"] or identity["source_sha256"] != registration["candidate_source_sha256"]:
        raise ValueError("candidate source identity differs from registration")
    if source_hashes(source_root) != identity["files"]:
        raise ValueError("current production source differs from the frozen candidate")
    if completion["source_unchanged"] is not True or completion["exit_code"] != 0:
        raise ValueError("full gate failed or source changed")
    if identity["native_sha256"] != registration["native_sha256"] or completion["native_sha256"] != identity["native_sha256"]:
        raise ValueError("native binary changed")
    if candidate_gate["gate"]["baseline_commit"] != baseline_gate["code"]["commit"]:
        raise ValueError("candidate gate used a different baseline")
    for gate in (baseline_gate, candidate_gate):
        if gate["config"]["sha256"] != registration["effective_config_sha256"] or gate["config"]["set"]:
            raise ValueError("effective configuration differs")
        if gate["config"]["file_sha256"] != registration["config_file_sha256"]:
            raise ValueError("configuration file differs")
        if gate["native"]["path"] != "native" or gate["gate"]["passed"] is not True:
            raise ValueError("require passing native gates")
        if any(gate["gate"][key] for key in ("allow", "worse_gated", "missing_gated", "worse_allowed", "missing_allowed")):
            raise ValueError("gate contains waivers, regressions or missing metrics")
    from scripts.regression_gate import metrics
    before_metrics, after_metrics = metrics(baseline_gate), metrics(candidate_gate)
    for values in (before_metrics, after_metrics):
        counts = {"all": len(values), "non_latency": sum(not key.startswith("latency_ms.") for key in values),
                  "gated": sum(value[2] for value in values.values())}
        if counts != registration["metric_counts"]:
            raise ValueError("full gate metric coverage differs")
    def semantic_metrics(values):
        return {key: value for key, value in values.items() if not key.startswith("latency_ms.")}

    if semantic_metrics(before_metrics) != semantic_metrics(after_metrics):
        raise ValueError("non-latency gate metrics changed")
    if sha(reference / "artifact_manifest.json") != registration["reference_manifest_sha256"]:
        raise ValueError("baseline artifact manifest differs")
    manifest = load(reference / "artifact_manifest.json")["files"]
    for name, metadata in manifest.items():
        if sha(reference / name) != metadata["sha256"]:
            raise ValueError(f"baseline artifact changed: {name}")
    config_path = reference / "captures/config.yaml"
    if config_path.read_bytes() != (candidate / "captures/config.yaml").read_bytes():
        raise ValueError("captured effective configs differ")
    config, digest = effective_config(source_root, identity["files"]["resense/config.py"], config_path)
    if digest != registration["effective_config_sha256"]:
        raise ValueError("captured config resolves differently")
    if config["health"]["latency_affects_decision"] is not False:
        raise ValueError("parity requires latency_affects_decision=false")
    return config["health"]


def compare(reference, candidate, protocol, freeze, out, source_root):
    registration, identity = load(protocol), load(freeze)
    config = validate_identity(reference, candidate, registration, identity, source_root)
    if registration["reset_indices"] != {name: [0] for name in REQUIRED}:
        raise ValueError("unexpected registered reset policy")
    out.mkdir(parents=True, exist_ok=True)
    payload_path = out / "payload_differences.jsonl.gz"
    health_path = out / "health_timing_differences.jsonl.gz"
    failures_path = out / "contract_failures.jsonl.gz"
    cases = {}
    with gzip.open(payload_path, "wt") as differences, gzip.open(health_path, "wt") as health_differences, gzip.open(failures_path, "wt") as failures:
        for name in REQUIRED:
            before, bp = capture(reference / "captures", name)
            after, ap = capture(candidate / "captures", name)
            fields = ("frame", "frame_id", "stamp")
            if len(before) != len(after) or any(tuple(a[k] for k in fields) != tuple(b[k] for k in fields) for a, b in zip(before, after)):
                raise ValueError(f"{name}: frame identities/order/timestamps differ")
            changed = timed = level_changes = invalid = 0
            for index, (a, b) in enumerate(zip(before, after)):
                key = {"recording": name, **{field: b[field] for field in fields}}
                errors, normalized = [], []
                for rows, complete, side in ((before, False, "reference"), (after, True, "candidate")):
                    try:
                        normalized.append(normalized_frame(rows, index, config, complete=complete,
                                                           reset_indices=registration["reset_indices"][name]))
                    except (ValueError, KeyError, TypeError) as exc:
                        errors.append({"side": side, "error": str(exc)})
                if errors:
                    invalid += 1
                    failures.write(json.dumps({**key, "errors": errors, "reference": a, "candidate": b}) + "\n")
                equal = not errors and normalized[0] == normalized[1]
                if not equal:
                    changed += 1
                    differences.write(json.dumps({**key, "reference": a, "candidate": b}) + "\n")
                if a["health"] != b["health"]:
                    timed += 1
                    health_differences.write(json.dumps({**key, "reference": a["health"], "candidate": b["health"], "normalized_equal": equal}) + "\n")
                level_changes += a["health"]["level"] != b["health"]["level"]
            cases[name] = {"reference": bp, "candidate": ap, "changed_non_timing_frames": changed,
                           "health_timing_changed_frames": timed, "health_level_changed_frames": level_changes,
                           "invalid_timing_contract_frames": invalid, "passed": changed == invalid == 0}
    setf_before = reference / "captures/setF_straight.json.gz"
    candidates = [p for p in (candidate / "captures/setF_straight.json", candidate / "captures/setF_straight.json.gz") if p.is_file()]
    if len(candidates) != 1:
        raise ValueError("require exactly one candidate set F capture")
    setf_after = candidates[0]
    a, b = load(setf_before), load(setf_after)
    validate_setf(a)
    validate_setf(b, a)
    elapsed = {"reference": a["summary"].pop("wall_s"), "candidate": b["summary"].pop("wall_s")}
    if not all(numeric(value) for value in elapsed.values()):
        raise ValueError("invalid set F wall timing")
    rows = sum(len(sequence["rows"]) for sequence in a["sequences"])
    setf = {"reference_sha256": sha(setf_before), "candidate_sha256": sha(setf_after),
            "sequences": len(a["sequences"]), "rows": rows, "wall_s": elapsed,
            "exact_equal_except_wall_s": a == b and rows == 3060}
    report = {"schema": "resense-complete-timing-parity-v1",
              "passed": all(case["passed"] for case in cases.values()) and setf["exact_equal_except_wall_s"],
              "protocol_sha256": sha(protocol), "freeze_sha256": sha(freeze), "comparator_sha256": sha(__file__),
              "candidate_commit": identity["commit"], "candidate_source_sha256": identity["source_sha256"],
              "effective_config_sha256": registration["effective_config_sha256"], "cases": cases, "set_F": setf,
              "artifacts": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in (payload_path, health_path, failures_path)},
              "timing_note": "Timing contract correction only. Shared-load times establish no performance gain or ROS runtime acceptance."}
    (out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("reference", "candidate", "protocol", "freeze", "out", "source-root"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(**vars(args))
    except Exception as exc:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "failure.json").write_text(json.dumps({"passed": False, "error": repr(exc)}, indent=2) + "\n")
        raise
    print(json.dumps({"passed": result["passed"], "frames": sum(case["reference"]["frames"] for case in result["cases"].values()),
                      "changed_non_timing_frames": sum(case["changed_non_timing_frames"] for case in result["cases"].values()),
                      "set_F": result["set_F"]}))
    raise SystemExit(0 if result["passed"] else 1)
