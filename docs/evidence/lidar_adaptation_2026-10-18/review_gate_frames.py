"""Revalidate and compare every serialized ordinary-gate row and Set F scoring row.

This is not a full-precision internal observer capture. Timing-only diagnostics
are excluded from equality; added readiness fields are reported, never hidden.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from scripts import regression_gate as gate  # noqa: E402
from scripts.cache_io import cache_file_stem, cache_files, load_cache_stamps  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def semantic(row):
    result = deepcopy(row)
    result.pop("timing_ms", None)
    health = result.get("health", {})
    health.pop("latency_p95_ms", None)
    health.pop("latency_basis", None)
    health.pop("latency_sample_age_frames", None)
    messages = health.get("messages", [])
    if any(m.startswith("latency p95 ") for m in messages):
        health["messages"] = [m for m in messages if not m.startswith("latency p95 ")]
        if health.get("level") == "warn":
            if health.get("decision_level") not in ("ok", "warn", "error"):
                raise ValueError("latency normalization requires explicit decision health")
            health["level"] = health["decision_level"]
    replay = result.get("mount", {}).get("orientation_replay", {})
    for key in ("replay_ms", "physical_call_ms", "physical_cpu_ms"):
        replay.pop(key, None)
    return result


def changed(left, right, prefix=""):
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left:
                yield path, "added"
            elif key not in right:
                yield path, "removed"
            else:
                yield from changed(left[key], right[key], path)
    elif left != right:
        yield prefix, "changed"


def validate_capture(report, work, cache, source):
    cfg = gate.eval_real.load_cfg(str(work / "config.yaml"), [])
    by_name, files, hashes = {}, {}, {}
    for name in [*gate.SIX, gate.SET_O, gate.RIDE]:
        count = 8 if name == gate.RIDE else 1
        paths = [work / (f"{name}_{i}.jsonl" if count > 1 else f"{name}.jsonl") for i in range(count)]
        inputs = np.array_split(np.array(cache_files(str(cache / name))), count)
        stamps = load_cache_stamps(str(cache / name))
        by_name[name], files[name] = [], paths
        for piece, (path, expected) in enumerate(zip(paths, inputs)):
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            if len(rows) != len(expected):
                raise ValueError(f"incomplete capture: {path}")
            for i, (row, input_path) in enumerate(zip(rows, expected)):
                stem = cache_file_stem(input_path)
                frame = int(stem.rsplit("_", 1)[1]) if name in gate.SIX else i
                if (row["frame_id"] != stem or row["frame"] != frame
                        or row["stamp"] != stamps.get(stem, i * .1)):
                    raise ValueError(f"frame identity/stamp mismatch: {path}:{i}")
            by_name[name].extend((piece, row) for row in rows)
            hashes[path.name] = sha(path)
    for name in gate.SIX:
        label = source / gate.eval_real.LABELS[name] if name in gate.eval_real.LABELS else None
        actual = gate.recording_entry(name, [str(p) for p in files[name]], cfg, str(label) if label else None)
        if actual != report["recordings"][name]:
            raise ValueError(f"recording summary disagrees with raw: {name}")
    actual_o = gate.set_o_entry([str(p) for p in files[gate.SET_O]], str(source / gate.SET_O_LABELS))
    if actual_o != report["set_O"]:
        raise ValueError("Set O summary disagrees with raw")
    actual_ride = gate.recording_entry(gate.RIDE, [str(p) for p in files[gate.RIDE]], cfg)
    actual_ride = {"available": True, "chunks": 8,
                   **{k: v for k, v in actual_ride.items() if k not in ("labelled", "first_alarm_frame")}}
    if actual_ride != report["ride"]:
        raise ValueError("ride summary disagrees with raw")
    return by_name, hashes


def validate_set_f(report, gate_report, cache, source):
    spec = importlib.util.spec_from_file_location("gate_review_far", ROOT / "scripts/far_range_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    parameters = report["parameters"]
    if (parameters["files"] != "46,68,98,140,168,172"
            or parameters["kinds"] != "person,box1.0,box0.5,trolley,cable"
            or parameters["frames"] != 110 or parameters["start_m"] != 220
            or parameters["seed"] != 0 or parameters["placement_mode"] != "legacy"):
        raise ValueError("Set F membership or placement protocol changed")
    speed_path = source / "docs/extended_dataset_intake.json"
    if sha(speed_path) != parameters["speeds_sha256"]:
        raise ValueError("Set F speed input changed")
    speeds = {entry["n"]: (entry.get("speed_tracks") or 0.0) for entry in read(speed_path)["files"]}
    all_files = cache_files(str(cache / gate.RIDE))
    stamps = load_cache_stamps(str(cache / gate.RIDE))
    expected, selected_files = {}, []
    for split in (46, 68, 98, 140, 168, 172):
        start = next(i for i, path in enumerate(all_files) if Path(path).name.startswith(f"new_data_{split}_"))
        paths = module.consecutive_files(all_files, start, 110)
        expected_frames, distance, previous_stamp = [], 220.0, None
        for path in paths:
            stem = cache_file_stem(path)
            stamp = stamps.get(stem)
            if previous_stamp is not None and stamp is not None:
                dt = stamp - previous_stamp
                distance -= speeds.get(int(Path(path).name.split("_")[2]), 0.0) * (dt if 0 < dt < 10 else .1)
            previous_stamp = stamp
            if distance < 8:
                break
            expected_frames.append(stem)
        for kind in parameters["kinds"].split(","):
            expected[(kind, Path(paths[0]).name)] = expected_frames
            selected_files.extend(Path(p).name for p in paths)
    if selected_files != parameters["cache_files"]:
        raise ValueError("Set F selected input files differ")
    selected_stamps = module.selected_stamps_of(selected_files, stamps)
    if hashlib.sha256(json.dumps(selected_stamps, sort_keys=True).encode()).hexdigest() != parameters["selected_stamps_sha256"]:
        raise ValueError("Set F selected input stamps differ")
    by_kind = {}
    seen = set()
    for sequence in report["sequences"]:
        if sequence.get("skipped"):
            raise ValueError("Set F skipped sequence")
        if sequence["d0"] != 220 or sequence["placement_mode"] != "legacy":
            raise ValueError("Set F sequence placement protocol changed")
        rows = sequence["rows"]
        identity = sequence["kind"], sequence["file0"]
        if identity in seen or identity not in expected or not rows:
            raise ValueError("duplicate, unknown or empty Set F sequence")
        seen.add(identity)
        if [row["frame"] for row in rows] != expected[identity]:
            raise ValueError("Set F row identity/consecutive source membership differs")
        first = next((row["gt"]["distance"] for row in rows if row["hit"]), None)
        if first != sequence["first"] or sum(len(row["fp_dets"]) for row in rows) != sequence["fp"]:
            raise ValueError("Set F sequence first hit/false detection summary mismatch")
        by_kind.setdefault(sequence["kind"], []).append(sequence)
    if seen != expected.keys():
        raise ValueError("incomplete Set F membership")
    for kind, sequences in by_kind.items():
        firsts = [s["first"] for s in sequences if s["first"] is not None]
        sustained = [v for s in sequences if (v := module.sustained_range(s["rows"])) is not None]
        bins = {}
        for lo, hi in module.BINS:
            visible = [r for s in sequences for r in s["rows"] if lo <= r["d"] < hi and r["n"] > 0]
            bins[f"{lo}-{hi}"] = [sum(r["hit"] for r in visible), len(visible)]
        actual = {"sequences": len(sequences), "detected": len(firsts),
                  "first_detection_median_m": round(float(np.median(firsts)), 1) if firsts else None,
                  "sustained_median_m": round(float(np.median(sustained)), 1) if sustained else None,
                  "false_detections": sum(s["fp"] for s in sequences), "recall_by_bin": bins}
        if actual != gate_report["set_F_straight"]["kinds"][kind]:
            raise ValueError(f"Set F gate summary disagrees with rows: {kind}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("reference", "candidate", "reference-work", "candidate-work",
                 "reference-source", "candidate-source", "cache", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    old, new = read(args.reference), read(args.candidate)
    for report in (old, new):
        if report["run"]["nominal_stamps"] is not False or report["ride"]["chunks"] != 8:
            raise ValueError("Expected original receive stamps and eight ride pieces")
        if report["native"]["path"] != "native":
            raise ValueError("Expected identical native runtime path")
    a, ah = validate_capture(old, args.reference_work, args.cache, args.reference_source)
    b, bh = validate_capture(new, args.candidate_work, args.cache, args.candidate_source)
    cases = {}
    for name in a:
        if len(a[name]) != len(b[name]):
            raise ValueError(f"capture length differs: {name}")
        fields, lost_stop, lost_dets, added_stop, guard_violations = {}, [], [], [], []
        for (pi, left), (pj, right) in zip(a[name], b[name]):
            identity = [pi, left["frame"], left["frame_id"]]
            if pi != pj or any(left[k] != right[k] for k in ("stamp", "frame", "frame_id")):
                raise ValueError(f"row identity differs: {name}")
            for field, kind in changed(semantic(left), semantic(right)):
                fields.setdefault(f"{kind}:{field}", []).append(identity)
            if left["obstacle"] and not right["obstacle"]:
                lost_stop.append(identity)
            if right["obstacle"] and not left["obstacle"]:
                added_stop.append(identity)
            old_dets = Counter(json.dumps(v, sort_keys=True) for v in left["detections"])
            new_dets = Counter(json.dumps(v, sort_keys=True) for v in right["detections"])
            if old_dets - new_dets:
                lost_dets.append(identity)
            if right.get("mount", {}).get("orientation_confirmed") is False:
                health = right.get("health", {})
                if right.get("clear_distance") != 0 or health.get("decision_level") not in ("warn", "error"):
                    guard_violations.append(identity)
        cases[name] = {"frames": len(a[name]), "changed_fields": fields,
                       "lost_stop_frames": lost_stop, "added_stop_frames": added_stop,
                       "frames_with_changed_or_missing_old_detection_payload": lost_dets,
                       "unconfirmed_orientation_guard_violations": guard_violations}
    af, bf = (read(work / "setF_straight.json") for work in (args.reference_work, args.candidate_work))
    validate_set_f(af, old, args.cache, args.reference_source)
    validate_set_f(bf, new, args.cache, args.candidate_source)
    parameter_changes = list(changed(af["parameters"], bf["parameters"]))
    if any(field != "config_sha256" for field, _ in parameter_changes):
        raise ValueError(f"Set F input parameters differ: {parameter_changes}")
    if len(af["sequences"]) != len(bf["sequences"]) or len(af["sequences"]) != 30:
        raise ValueError("Set F sequence count mismatch")
    set_f = []
    for left, right in zip(af["sequences"], bf["sequences"]):
        if any(left[k] != right[k] for k in ("kind", "file0", "d0", "lateral", "refl")):
            raise ValueError("Set F sequence identity mismatch")
        if len(left["rows"]) != len(right["rows"]):
            raise ValueError("Set F row count mismatch")
        fields, lost_hits, added_hits = {}, [], []
        for lr, rr in zip(left["rows"], right["rows"]):
            if lr["frame"] != rr["frame"]:
                raise ValueError("Set F row identity mismatch")
            for field, kind in changed(lr, rr):
                fields.setdefault(f"{kind}:{field}", []).append(lr["frame"])
            if lr["hit"] and not rr["hit"]:
                lost_hits.append(lr["frame"])
            if rr["hit"] and not lr["hit"]:
                added_hits.append(lr["frame"])
        set_f.append({"kind": left["kind"], "file0": left["file0"], "rows": len(left["rows"]),
                      "changed_fields": fields, "lost_hits": lost_hits, "added_hits": added_hits})
    comparison = gate.compare(old, new, [])
    output = {"status": "SERIALIZED_EVIDENCE_REVALIDATED", "ordinary": cases, "set_F": set_f,
              "ordinary_rows": sum(v["frames"] for v in cases.values()),
              "set_F_rows": sum(v["rows"] for v in set_f),
              "gate_metrics": comparison,
              "reference_raw_hashes": ah, "candidate_raw_hashes": bh,
              "set_F_parameter_changes": parameter_changes,
              "scope": "All serialized ordinary-gate fields plus Set F scoring and placement rows. No full-precision internal observer was used.",
              "set_F_limit": "Recomputes aggregate counters from stored hit/fp scoring rows and validates all input identities/placements. The sealed Set F rows omit complete detections, so hit/fp assignment cannot be independently rebuilt from these artifacts.",
              "exclusions": "Timing values and latency-only health messages/promotion; new readiness fields remain explicit differences.",
              "input_sha256": {str(p): sha(p) for p in (
                  args.reference, args.candidate, args.reference_work / "setF_straight.json",
                  args.candidate_work / "setF_straight.json", Path(__file__))}}
    if output["ordinary_rows"] != 15269 or output["set_F_rows"] != 3060:
        raise ValueError("Full expected gate membership is not present")
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: output[k] for k in ("status", "ordinary_rows", "set_F_rows")}))


if __name__ == "__main__":
    main()
