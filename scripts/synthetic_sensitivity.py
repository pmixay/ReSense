#!/usr/bin/env python3
"""Generate and score the registered synthetic persistence/range protocol.

Point clouds belong in ignored/local storage. Reports contain compact per-frame evidence.
The reserved evaluation split requires a candidate-freeze JSON, and must remain unused
until the candidate is fixed. These scenes are synthetic, not real holdout validation.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from resense.config import DetectorConfig  # noqa: E402
from resense import _native  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import axis_matrix, frame_from_compact  # noqa: E402
from resense.pointcloud import COMPACT_DTYPE, compact_to_compact16  # noqa: E402
from resense.sensor import RING_ELEVATION_DEG  # noqa: E402

PROTOCOL = ROOT / "docs/evidence/cycle_2026-09-28/evaluation/protocol.json"
FIXTURE = ROOT / "tests/fixtures/synthetic_lidar_v1"


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_identity(source_commit=None):
    files = sorted((ROOT / "resense").glob("*.py")) + sorted((ROOT / "native").glob("*.cpp"))
    files += sorted((ROOT / "resense/models").glob("*.json"))
    hashes = {str(p.relative_to(ROOT)): file_hash(p) for p in files}
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    commit = result.stdout.strip() if result.returncode == 0 else source_commit
    if not commit:
        raise ValueError("Git metadata unavailable in this mount; pass --source-commit from the host checkout")
    return {"commit": commit, "commit_origin": "git" if result.returncode == 0 else "supplied by caller",
            "detector_source_sha256": json_hash(hashes), "files": hashes}


def sequence_cases(protocol, split):
    """Expand all cases in the registered order, before applying a CLI case filter."""
    settings = protocol["splits"][split]
    cases = []
    for shape in protocol["shapes"]:
        for distance in settings["distances_m"]:
            for side, lateral in enumerate(shape["laterals_m"]):
                cases.append({"name": f"{shape['name']}_{distance:g}m_{side}", "positive": True,
                              "kind": shape["kind"], "size_m": [v * settings["size_scale"] for v in shape["size_m"]],
                              "distance_m": distance, "lateral_m": lateral,
                              "yaw_deg": settings["yaw_degrees"][side]})
    for control in protocol["negative_controls"]:
        cases.append({**control, "positive": False, "yaw_deg": 0.0})
    for index, case in enumerate(cases):
        case["index"] = index
        case["seed"] = settings["seed"] + index * 100
        case["floor_z"] = settings["geometry"]["floor_z"]
        case["axis_y"] = settings["geometry"]["axis_y"]
    return cases


def raw_compact(frame, sensor):
    """Keep float coordinates/intensity; the paired cache quantization happens later."""
    raw = np.zeros(frame.n, dtype=COMPACT_DTYPE)
    xyz = frame.xyz @ axis_matrix(sensor).astype(np.float32)
    raw["x"], raw["y"], raw["z"] = xyz.T
    raw["intensity"] = frame.intensity
    elevations = np.degrees(np.arctan2(frame.xyz[:, 2], np.hypot(frame.xyz[:, 0], frame.xyz[:, 1])))
    order = np.argsort(RING_ELEVATION_DEG)
    grid = RING_ELEVATION_DEG[order]
    right = np.clip(np.searchsorted(grid, elevations), 1, len(grid) - 1)
    nearest = np.where(abs(elevations - grid[right - 1]) <= abs(elevations - grid[right]), right - 1, right)
    raw["ring"] = order[nearest]
    return raw


def candidate_freeze(path, split):
    if split != "evaluation":
        return None
    if path is None:
        raise ValueError("reserved evaluation requires --candidate-freeze JSON after candidate selection")
    frozen = json.loads(Path(path).read_text())
    for role in ("baseline", "candidate"):
        identity = frozen.get(role, {})
        for key, length in (("commit", 40), ("detector_source_sha256", 64), ("config_sha256", 64)):
            if not isinstance(identity.get(key), str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", identity[key]):
                raise ValueError(f"candidate freeze lacks valid {role}.{key}")
    return {"file_sha256": file_hash(path), **frozen}


def frozen_role(frozen, source, config_sha256):
    """Documentation-only commits may differ; detector/config bytes must match a frozen pair."""
    if frozen is None:
        return None
    matches = [role for role in ("baseline", "candidate")
               if frozen[role]["detector_source_sha256"] == source["detector_source_sha256"]
               and frozen[role]["config_sha256"] == config_sha256]
    if not matches:
        raise ValueError("reserved evaluation source/config does not match frozen baseline or candidate")
    return "+".join(matches)


def generate(args):
    # Imported only here: fixture replay and scoring do not require Open3D.
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame

    protocol = json.loads(args.protocol.read_text())
    frozen = candidate_freeze(args.candidate_freeze, args.split)
    source = source_identity(args.source_commit)
    cfg = DetectorConfig.from_yaml(str(args.config))
    role = frozen_role(frozen, source, json_hash(asdict(cfg)))
    settings = protocol["splits"][args.split]
    all_cases = sequence_cases(protocol, args.split)
    selected = set(args.cases.split(",")) if args.cases else {c["name"] for c in all_cases}
    unknown = selected - {c["name"] for c in all_cases}
    if unknown:
        raise ValueError(f"unknown cases: {sorted(unknown)}")
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / "manifest.json"
    manifest = {"schema": "resense.synthetic_sequence_cache.v1", "synthetic": True,
                "protocol_sha256": file_hash(args.protocol), "protocol": protocol, "split": args.split,
                "candidate_freeze": frozen, "generator": source, "frozen_role": role,
                "evaluator_sha256": file_hash(__file__), "cases": []}
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        for key in ("schema", "protocol_sha256", "split", "candidate_freeze", "evaluator_sha256"):
            if old.get(key) != manifest[key]:
                raise ValueError(f"existing cache has different {key}; use a fresh output directory")
        if old["generator"]["files"]["resense/synthetic.py"] != manifest["generator"]["files"]["resense/synthetic.py"]:
            raise ValueError("existing cache uses a different raycaster")
        manifest = old
    recorded = {c["name"]: c for c in manifest["cases"]}
    sensor = cfg.sensor
    for case in all_cases:
        if case["name"] not in selected:
            continue
        if case["name"] in recorded:
            for row in recorded[case["name"]]["frames"]:
                if file_hash(args.output / row["file"]) != row["sha256"]:
                    raise ValueError(f"changed cache file {row['file']}")
            print(f"verified existing {case['name']}", flush=True)
            continue
        folder = args.output / case["name"]
        folder.mkdir(exist_ok=True)
        specs = [] if case["kind"] is None else [ObstacleSpec(
            kind=case["kind"], size=tuple(case["size_m"]), distance=case["distance_m"],
            lateral=case["lateral_m"], yaw_deg=case["yaw_deg"], base_z=case["floor_z"],
            reflectivity=settings["reflectivity"], label=case["name"])]
        rows = []
        for index in range(protocol["frame_count"]):
            frame, labels, _ = synthetic_tunnel_frame(
                **settings["geometry"], specs=specs, rng=np.random.default_rng(case["seed"] + index))
            raw = raw_compact(frame, sensor)
            path = folder / f"frame_{index:03d}.npz"
            np.savez_compressed(path, points=raw, target_mask=(labels == 1))
            rows.append({"file": str(path.relative_to(args.output)), "sha256": file_hash(path),
                         "stamp_s": index * protocol["frame_period_s"], "index": index,
                         "seed": case["seed"] + index, "target_returns": int(np.count_nonzero(labels == 1))})
        recorded[case["name"]] = {**case, "frames": rows}
        manifest["cases"] = [recorded[c["name"]] for c in all_cases if c["name"] in recorded]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(f"generated {case['name']}: {len(rows)} frames", flush=True)


def target_matches(detection, case, matching):
    if not case["positive"]:
        return False
    length, width, height = case["size_m"]
    yaw = np.radians(case.get("yaw_deg", 0.0))
    half = np.array([(abs(np.cos(yaw)) * length + abs(np.sin(yaw)) * width) / 2,
                     (abs(np.sin(yaw)) * length + abs(np.cos(yaw)) * width) / 2, height / 2])
    center = np.array([case["distance_m"] + length / 2, case["axis_y"] + case["lateral_m"],
                       case["floor_z"] + height / 2])
    tol = max(matching["distance_tolerance_m"], matching["distance_tolerance_fraction"] * case["distance_m"])
    return bool(abs(detection.distance - case["distance_m"]) <= tol
                and np.all(abs(detection.center - center) <= half + matching["bbox_padding_m"]))


def observation(result, case, returns, index, stamp, matching):
    matched = [target_matches(d, case, matching) for d in result.detections]
    level = result.health.get("level", "ok")
    decision = ("STOP" if result.obstacle else "FAULT" if level == "error" else "CAUTION"
                if result.warning or result.health.get("decision_level", level) == "warn" else "GO")
    return {"frame": index, "stamp_s": stamp, "target_returns": returns,
            "visible": bool(case["positive"] and returns > 0), "stop": bool(result.obstacle),
            "matched_stop": any(matched), "unmatched_stop": any(not m for m in matched),
            "matched_ids": [d.id for d, match in zip(result.detections, matched) if match],
            "detections": [{"id": int(d.id), "distance": float(d.distance),
                            "center": np.asarray(d.center).tolist(), "size": np.asarray(d.size).tolist(),
                            "kind": d.kind, "reason": d.reason} for d in result.detections],
            "health": result.health, "decision": decision,
            "decision_scope": "offline detector policy; no ROS freshness/watchdog evaluation",
            "clear_distance_m": float(result.clear_distance),
            "clear_overclaim": bool(case["positive"] and returns > 0 and result.clear_distance > case["distance_m"] + 1.0),
            "target_distance_m": case["distance_m"], "warning": bool(result.warning)}


def longest_run(values):
    longest = current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(current, longest)
    return longest


def episodes(values):
    return sum(bool(value) and (index == 0 or not values[index - 1]) for index, value in enumerate(values))


def sequence_metrics(rows, metric_cfg):
    hits = [r["matched_stop"] for r in rows]
    visible = [r["visible"] for r in rows]
    first = next((i for i, hit in enumerate(hits) if hit), None)
    steady = rows[metric_cfg["steady_start_frame"]:]
    steady_visible = sum(r["visible"] for r in steady)
    steady_hits = sum(r["visible"] and r["matched_stop"] for r in steady)
    recall = steady_hits / steady_visible if steady_visible else None
    streak = longest_run(hits)
    return {"frames": len(rows), "visible_frames": sum(visible), "matched_stop_frames": sum(hits),
            "visible_matched_stop_frames": sum(v and h for v, h in zip(visible, hits)),
            "visible_recall": sum(v and h for v, h in zip(visible, hits)) / sum(visible) if any(visible) else None,
            "steady_visible_frames": steady_visible, "steady_visible_recall": recall,
            "first_stop_frame": rows[first]["frame"] if first is not None else None,
            "first_stop_distance_m": rows[first]["target_distance_m"] if first is not None else None,
            "longest_stop_streak": streak,
            "longest_visible_miss_after_stop": longest_run([v and not h for v, h in zip(visible[first:], hits[first:])]) if first is not None else None,
            "stop_frames": sum(r["stop"] for r in rows), "stop_episodes": episodes([r["stop"] for r in rows]),
            "unmatched_stop_frames": sum(r["unmatched_stop"] for r in rows),
            "unmatched_stop_episodes": episodes([r["unmatched_stop"] for r in rows]),
            "clear_overclaim_frames": sum(r["clear_overclaim"] for r in rows),
            "sustained": bool(streak >= metric_cfg["sustained_min_consecutive_frames"]
                              and recall is not None and recall >= metric_cfg["sustained_visible_recall_min"])}


def evaluate(args):
    manifest = json.loads((args.cache / "manifest.json").read_text())
    if manifest["protocol_sha256"] != file_hash(args.protocol):
        raise ValueError("cache protocol hash does not match requested protocol")
    frozen = candidate_freeze(args.candidate_freeze, manifest["split"])
    if frozen != manifest["candidate_freeze"]:
        raise ValueError("cache and evaluator candidate-freeze records differ")
    protocol = manifest["protocol"]
    cfg = DetectorConfig.from_yaml(str(args.config))
    source = source_identity(args.source_commit)
    config_sha256 = json_hash(asdict(cfg))
    role = frozen_role(frozen, source, config_sha256)
    report = {"schema": "resense.synthetic_sensitivity_result.v1", "synthetic": True,
              "protocol_sha256": manifest["protocol_sha256"], "cache_manifest_sha256": file_hash(args.cache / "manifest.json"),
              "split": manifest["split"], "candidate_freeze": frozen, "source": source,
              "frozen_role": role, "config_sha256": config_sha256, "config": asdict(cfg),
              "runtime": {"python": platform.python_version(), "numpy": np.__version__,
                          "native": _native.status(), "native_library_sha256": file_hash(_native.LIBRARY) if _native.LIBRARY else None},
              "evaluator_sha256": file_hash(__file__),
              "cache_generator_script_sha256": manifest["evaluator_sha256"], "cases": []}
    for case in manifest["cases"]:
        detectors = {name: Detector(cfg) for name in ("float32", "compact16")}
        outputs = {name: [] for name in detectors}
        for row in case["frames"]:
            path = args.cache / row["file"]
            if file_hash(path) != row["sha256"]:
                raise ValueError(f"changed cache file {row['file']}")
            with np.load(path, allow_pickle=False) as saved:
                raw = saved["points"]
                returns = int(np.count_nonzero(saved["target_mask"]))
            packed = compact_to_compact16(raw)
            if len(raw) != len(packed):
                raise ValueError("encoding pair dropped points")
            for encoding, array in (("float32", raw), ("compact16", packed)):
                frame = frame_from_compact(array, cfg.sensor, stamp=row["stamp_s"])
                result = detectors[encoding].process(frame)
                outputs[encoding].append(observation(result, case, returns, row["index"], row["stamp_s"], protocol["matching"]))
        report["cases"].append({"case": {k: v for k, v in case.items() if k != "frames"},
                                "input_sha256": json_hash(case["frames"]),
                                "encodings": {name: {"metrics": sequence_metrics(rows, protocol["metrics"]), "rows": rows}
                                              for name, rows in outputs.items()},
                                "quantization_disagreement_frames": [a["frame"] for a, b in zip(outputs["float32"], outputs["compact16"])
                                                                     if a["matched_stop"] != b["matched_stop"]]})
        print(f"evaluated {case['name']}", flush=True)
    expected = {c["name"] for c in sequence_cases(protocol, manifest["split"])}
    report["expected_cases"] = sorted(expected)
    report["complete_split"] = {c["case"]["name"] for c in report["cases"]} == expected
    if args.baseline:
        report["comparison"] = compare_reports(json.loads(args.baseline.read_text()), report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    if args.baseline and not report["comparison"]["passed"]:
        return 1
    return 0


def compare_reports(baseline, current):
    """Enforce every registered per-case criterion, including false frame counts."""
    if baseline["protocol_sha256"] != current["protocol_sha256"] or baseline["split"] != current["split"]:
        raise ValueError("cannot compare different protocols or splits")
    old = {c["case"]["name"]: c for c in baseline["cases"]}
    new = {c["case"]["name"]: c for c in current["cases"]}
    if old.keys() != new.keys():
        raise ValueError("cannot compare different case sets")
    incomplete = [name for name, report in (("baseline", baseline), ("current", current))
                  if not report.get("complete_split")
                  or set(report.get("expected_cases", [])) != set(old)]
    if incomplete:
        return {"passed": False, "regressions": [], "improvements": [], "detector_gain": False,
                "incomplete_split": incomplete}
    regressions, improvements = [], []
    for name in old:
        if old[name]["input_sha256"] != new[name]["input_sha256"]:
            raise ValueError(f"input changed for {name}")
        if old[name]["case"] != new[name]["case"]:
            raise ValueError(f"case labels changed for {name}")
        for encoding in ("float32", "compact16"):
            before = old[name]["encodings"][encoding]["metrics"]
            after = new[name]["encodings"][encoding]["metrics"]
            criteria = {"unmatched_stop_frames": -1, "unmatched_stop_episodes": -1}
            if new[name]["case"]["positive"]:
                criteria.update(matched_stop_frames=1, first_stop_frame=-1,
                                longest_visible_miss_after_stop=-1, sustained=1)
            for key, direction in criteria.items():
                a, b = before[key], after[key]
                if a == b:
                    continue
                # An absent first confirmation/miss metric belongs to a never-detected case.
                gain = a is None or (b is not None and direction * (b - a) > 0)
                entry = {"case": name, "encoding": encoding, "metric": key, "baseline": a, "current": b}
                (improvements if gain else regressions).append(entry)
    return {"passed": not regressions, "regressions": regressions, "improvements": improvements,
            "detector_gain": bool(improvements and not regressions)}


def fixture_sequence(name, gap=0, fixture=FIXTURE):
    """Stored development fixture; masking removes target returns without filling occlusion."""
    manifest = json.loads((fixture / "manifest.json").read_text())
    positive = manifest["scenes"]["rail_straddle"]["frames"]
    clear = manifest["scenes"]["clear_tunnel"]["frames"]
    if name == "clear":
        schedule = [(row, False) for row in clear]
    elif name == "transient":
        schedule = [(row, False) for row in clear[:3]] + [(positive[6], False)] + [(row, False) for row in clear[3:]]
    elif name == "removal":
        schedule = [(row, False) for row in positive[:6]] + [(row, False) for row in clear]
    elif name == "gap" and gap in range(4):
        schedule = [(row, 6 <= i < 6 + gap) for i, row in enumerate(positive)]
    else:
        raise ValueError(f"unknown fixture sequence {name} or gap {gap}")
    for index, (row, drop) in enumerate(schedule):
        raw = np.load(fixture / row["points_file"], allow_pickle=False)
        mask = row.get("object_masks", {}).get("1")
        if mask:
            bits = np.load(fixture / mask["file"], allow_pickle=False)
            target = np.unpackbits(bits, bitorder="little")[:len(raw)].astype(bool)
            if drop:
                raw = raw[~target]
            returns = 0 if drop else int(target.sum())
        else:
            returns = 0
        yield index, raw, returns


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--split", choices=("development", "evaluation"), default="development")
    gen.add_argument("--cases", help="comma-separated case names; indices/seeds keep full protocol order")
    gen.add_argument("--output", type=Path, required=True)
    ev = sub.add_parser("evaluate")
    ev.add_argument("--cache", type=Path, required=True)
    ev.add_argument("--baseline", type=Path)
    ev.add_argument("--output", type=Path, required=True)
    for command in (gen, ev):
        command.add_argument("--config", type=Path, default=ROOT / "configs/default.yaml")
        command.add_argument("--protocol", type=Path, default=PROTOCOL)
        command.add_argument("--candidate-freeze", type=Path)
        command.add_argument("--source-commit", help="host checkout commit when a container cannot resolve worktree Git metadata")
    args = parser.parse_args(argv)
    try:
        return generate(args) if args.command == "generate" else evaluate(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
