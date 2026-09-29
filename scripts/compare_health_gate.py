#!/usr/bin/env python3
"""Compare a frozen histogram candidate's full gate outputs against its registered baseline."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics
import sys

REQUIRED = ("doubleT_obstacle", "doubleT_platform", "roundT_doubleT",
            "roundT_pressureGate_roundT", "roundT_squareT_pressureGate_squareT",
            "squareT_platform_squareT_switch", "cloud_with_fake_obj",
            *(f"new_data_{i}" for i in range(8)))
LEVELS = ("ok", "warn", "error")
LATENCY = re.compile(r"latency p95 ([0-9]+) ms over the ([0-9]+) ms budget\Z")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as stream:
        return json.load(stream)


def capture(directory, name):
    paths = [p for p in (directory / f"{name}.jsonl", directory / f"{name}.jsonl.gz") if p.is_file()]
    if len(paths) != 1:
        raise ValueError(f"{name}: require exactly one capture")
    path = paths[0]
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    keys = [(r["frame"], r["frame_id"], r["stamp"]) for r in rows]
    if not rows or len(set(keys)) != len(keys) or not all(math.isfinite(k[2]) for k in keys):
        raise ValueError(f"{name}: empty, duplicate or invalid frame identities")
    return rows, {"path": str(path), "sha256": sha(path), "frames": len(rows)}


def normalized_health(health, config, index):
    """Remove only verified effects of measured stage latency; retain every other field."""
    if config.get("latency_affects_decision") is not False:
        raise ValueError("latency normalization requires explicit latency_affects_decision=false")
    if health["level"] not in LEVELS or health["decision_level"] not in LEVELS:
        raise ValueError("unknown health level")
    value = health["latency_p95_ms"]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid reported latency")
    budget = config["latency_budget_ms"]
    normal, timed = [], []
    for message in health["messages"]:
        match = LATENCY.fullmatch(message)
        if match:
            if match[2] != f"{budget:.0f}" or abs(int(match[1]) - value) > 0.550000001:
                raise ValueError("latency message disagrees with budget or rounded p95")
            timed.append(message)
        elif message.startswith("latency p95"):
            raise ValueError("malformed latency message")
        else:
            normal.append(message)
    if len(timed) > 1:
        raise ValueError("duplicate latency message")
    eligible = min(index + 1, config["latency_window"]) >= 10
    if timed and (not eligible or value < budget - 0.050000001):
        raise ValueError("latency warning contradicts count or numeric threshold")
    if eligible and value > budget + 0.050000001 and not timed:
        raise ValueError("missing latency warning")
    expected = LEVELS[max(LEVELS.index(health["decision_level"]), int(bool(timed)))]
    if health["level"] != expected:
        raise ValueError("health level has an unexplained difference from decision level")
    result = dict(health)
    result.pop("latency_p95_ms")
    result["messages"] = normal
    result["level"] = result["decision_level"]
    return result


def normalized(row, config, index):
    result = dict(row)
    result.pop("timing_ms")
    result["health"] = normalized_health(row["health"], config, index)
    return result


def timing_summary(values):
    ordered = sorted(values)
    k = 0.95 * (len(ordered) - 1)
    p95 = ordered[int(k)] + (ordered[min(int(k) + 1, len(ordered) - 1)] - ordered[int(k)]) * (k % 1)
    return {"mean": statistics.mean(values), "p95": p95, "min": min(values), "max": max(values)}


def validate_setf(data, reference=None):
    parameters = data["parameters"]
    expected_cases = {(kind, f"new_data_{file}_0000.npy.zst")
                      for kind in parameters["kinds"].split(",")
                      for file in parameters["files"].split(",")}
    sequences = {(s["kind"], s["file0"]): s for s in data["sequences"]}
    if len(data["sequences"]) != 30 or len(sequences) != 30 or set(sequences) != expected_cases:
        raise ValueError("set F requires all 30 unique registered cases")
    if parameters["frames"] != 110 or any(s.get("skipped") or not 0 < len(s["rows"]) <= 110 for s in sequences.values()):
        raise ValueError("set F contains skipped, empty or invalid-length sequences")
    if reference is not None:
        original = {(s["kind"], s["file0"]): [r["frame"] for r in s["rows"]] for s in reference["sequences"]}
        current = {key: [r["frame"] for r in s["rows"]] for key, s in sequences.items()}
        if current != original:
            raise ValueError("set F ordered frame identities or lengths differ from frozen baseline")


def effective_config(source_root, expected_config_source_sha256, capture_path):
    path = source_root.resolve() / "resense/config.py"
    if sha(path) != expected_config_source_sha256:
        raise ValueError("configuration loader differs from frozen source")
    spec = importlib.util.spec_from_file_location("_frozen_health_gate_config", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    config = module.DetectorConfig.from_yaml(str(capture_path)).to_dict()
    return config, hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compare(reference, candidate, protocol, freeze, out, source_root=None, reference_manifest_sha256=None):
    registration = load(protocol)
    identity = load(freeze)
    baseline_gate, candidate_gate = load(reference / "gate.json"), load(candidate / "gate.json")
    completion = load(candidate / "completion.json")
    if sha(reference / "gate.json") != registration["baseline_gate"]["sha256"]:
        raise ValueError("baseline gate differs from registered evidence")
    if baseline_gate["code"]["commit"] != registration["baseline_gate"]["measured_commit"]:
        raise ValueError("baseline measured source differs")
    if candidate_gate["code"]["commit"] != identity["commit"] or candidate_gate["code"]["uncommitted_detector_changes"]:
        raise ValueError("candidate gate source is not the frozen clean commit")
    digest = hashlib.sha256(json.dumps(identity["files"], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != identity["source_sha256"] or digest != registration["candidate_source_sha256"]:
        raise ValueError("candidate production source differs from registration")
    if completion["source_unchanged"] is not True or completion["exit_code"] != 0:
        raise ValueError("candidate full gate failed or source changed during evaluation")
    for gate in (baseline_gate, candidate_gate):
        if gate["config"]["sha256"] != registration["effective_config_sha256"] or gate["config"]["set"]:
            raise ValueError("gate effective configuration differs from registration")
        if gate["config"]["file_sha256"] != registration["config_file_sha256"]:
            raise ValueError("gate config file differs from registration")
        if gate["native"]["path"] != "native" or gate["gate"]["passed"] is not True:
            raise ValueError("require passing native gates")
        if any(gate["gate"][key] for key in ("allow", "worse_gated", "missing_gated", "worse_allowed", "missing_allowed")):
            raise ValueError("gate contains waivers, regressions or missing metrics")
    if identity["native_sha256"] != registration["native_sha256"]:
        raise ValueError("candidate native binary differs")
    if sha(reference / "artifact_manifest.json") != reference_manifest_sha256:
        raise ValueError("reference artifact manifest differs from expected frozen hash")
    manifest = load(reference / "artifact_manifest.json")["files"]
    if sha(reference / "config.yaml") != manifest["config.yaml"]["sha256"]:
        raise ValueError("reference effective config capture changed")
    if (reference / "config.yaml").read_bytes() != (candidate / "captures/config.yaml").read_bytes():
        raise ValueError("effective config captures differ")
    resolved_config, resolved_digest = effective_config(source_root, identity["files"]["resense/config.py"], reference / "config.yaml")
    if resolved_digest != registration["effective_config_sha256"]:
        raise ValueError("captured configuration resolves differently from registered effective config")
    health_config = resolved_config["health"]
    if health_config.get("latency_affects_decision") is not False:
        raise ValueError("latency affects decision; this comparator cannot normalize health")
    out.mkdir(parents=True, exist_ok=True)
    differences_path, timing_path = out / "payload_differences.jsonl.gz", out / "health_timing_differences.jsonl.gz"
    cases = {}
    with gzip.open(differences_path, "wt") as differences, gzip.open(timing_path, "wt") as timing:
        for name in REQUIRED:
            before, bp = capture(reference / "captures", name)
            after, ap = capture(candidate / "captures", name)
            if bp["sha256"] != manifest[f"captures/{Path(bp['path']).name}"]["sha256"]:
                raise ValueError(f"{name}: baseline capture differs from archived manifest")
            if len(before) != len(after) or any(tuple(a[k] for k in ("frame", "frame_id", "stamp")) != tuple(b[k] for k in ("frame", "frame_id", "stamp")) for a, b in zip(before, after)):
                raise ValueError(f"{name}: frame identity/order/timestamp mismatch")
            changed, timed, level_changes, new_alarms, removed_alarms = 0, 0, 0, 0, 0
            for index, (a, b) in enumerate(zip(before, after)):
                key = {"recording": name, **{k: b[k] for k in ("frame", "frame_id", "stamp")}}
                if normalized(a, health_config, index) != normalized(b, health_config, index):
                    changed += 1
                    differences.write(json.dumps({**key, "reference": a, "candidate": b}) + "\n")
                if a["health"] != b["health"]:
                    timed += 1
                    timing.write(json.dumps({**key, "reference": a["health"], "candidate": b["health"], "normalized_equal": normalized_health(a["health"], health_config, index) == normalized_health(b["health"], health_config, index)}) + "\n")
                level_changes += a["health"]["level"] != b["health"]["level"]
                new_alarms += bool(b["obstacle"]) and not bool(a["obstacle"])
                removed_alarms += bool(a["obstacle"]) and not bool(b["obstacle"])
            cases[name] = {"reference": bp, "candidate": ap, "changed_non_timing_frames": changed,
                           "health_timing_changed_frames": timed, "health_level_changed_frames": level_changes,
                           "new_alarm_frames": new_alarms, "removed_alarm_frames": removed_alarms,
                           "reference_health_latency_p95_ms": timing_summary([r["health"]["latency_p95_ms"] for r in before]),
                           "candidate_health_latency_p95_ms": timing_summary([r["health"]["latency_p95_ms"] for r in after]),
                           "passed": changed == 0}
    setf_before = reference / "setF_straight.json.gz"
    setf_candidates = [p for p in (candidate / "captures/setF_straight.json",
                                   candidate / "captures/setF_straight.json.gz") if p.is_file()]
    if len(setf_candidates) != 1:
        raise ValueError("require exactly one plain or compressed candidate set F output")
    setf_after = setf_candidates[0]
    if sha(setf_before) != manifest["setF_straight.json.gz"]["sha256"]:
        raise ValueError("set F reference differs from archived manifest")
    a, b = load(setf_before), load(setf_after)
    validate_setf(a)
    validate_setf(b, a)
    elapsed = {"reference": a["summary"]["wall_s"], "candidate": b["summary"]["wall_s"]}
    if any(not isinstance(v, float) or not math.isfinite(v) or v < 0 for v in elapsed.values()):
        raise ValueError("invalid set F wall timing")
    a["summary"].pop("wall_s")
    b["summary"].pop("wall_s")
    setf = {"reference_sha256": sha(setf_before), "candidate_sha256": sha(setf_after),
            "sequences": 30, "rows": sum(len(s["rows"]) for s in a["sequences"]),
            "wall_s": elapsed, "exact_equal_except_wall_s": a == b}
    report = {"schema": "resense-health-gate-parity-v1", "passed": all(c["passed"] for c in cases.values()) and setf["exact_equal_except_wall_s"],
              "protocol_sha256": sha(protocol), "freeze_sha256": sha(freeze), "comparator_sha256": sha(__file__),
              "reference_manifest_sha256": reference_manifest_sha256,
              "reference_gate_sha256": sha(reference / "gate.json"), "candidate_gate_sha256": sha(candidate / "gate.json"),
              "candidate_commit": identity["commit"], "candidate_source_sha256": digest,
              "effective_config_sha256": registration["effective_config_sha256"], "cases": cases, "set_F": setf,
              "differences": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in (differences_path, timing_path)},
              "timing_note": "All source outputs are retained. Only stage timings and validated latency health effects are excluded from exact semantic comparison; all health changes are recorded. Shared-load timings are not runtime acceptance."}
    (out / "comparison.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("reference", "candidate", "protocol", "freeze", "out"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--reference-manifest-sha256", required=True)
    args = parser.parse_args()
    result = compare(**vars(args))
    print(json.dumps({"passed": result["passed"], "frames": sum(c["reference"]["frames"] for c in result["cases"].values()), "changed_non_timing_frames": sum(c["changed_non_timing_frames"] for c in result["cases"].values()), "set_F": result["set_F"]}))
    raise SystemExit(0 if result["passed"] else 1)
