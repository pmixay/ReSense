#!/usr/bin/env python3
"""Observe existing development clouds without changing detector decisions or thresholds."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import gzip
import inspect
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from resense import clustering  # noqa: E402
import resense.detector as detector_module  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.gauge import point_in_polygon  # noqa: E402
from resense.pointcloud import compact_to_compact16, compact_to_xyz, expand_compact16  # noqa: E402
from synthetic_sensitivity import file_hash, json_hash, observation, source_identity  # noqa: E402
from trace_detector_stages import TraceDetector, cluster_record  # noqa: E402


def load_json(path):
    with (gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)) as stream:
        return json.load(stream)


def bounds(values):
    return [float(np.min(values)), float(np.max(values))] if len(values) else None


def filtered_targets(array, target_mask, sensor):
    """Apply the actual compact decoder's range predicate, preserving exact row membership."""
    xyz = compact_to_xyz(expand_compact16(array))
    r2 = (xyz * xyz).sum(axis=1)
    keep = np.isfinite(r2) & (r2 >= sensor.min_range ** 2) & (r2 <= sensor.max_range ** 2)
    return np.flatnonzero(np.asarray(target_mask, bool)[keep]), int(keep.sum())


def true_surfaces(case, rotation, query_x):
    """The generator's actual floor/rail mesh planes after the same mount correction.

    Mesh rails are 0.18 m high (synthetic_tunnel_frame), independent of TrackModel's
    default rail_offset. Grade is zero by registration. No fitted detector quantity
    supplies the truth except the coordinate at which both surfaces are compared.
    """
    if abs(rotation[0, 0]) < 1e-6 or abs(rotation[2, 2]) < 1e-6:
        raise ValueError("unexpected orientation for this fixed synthetic sensor")
    rail_z = case["floor_z"] + 0.18
    original_x = (query_x - rotation[0, 1] * case["axis_y"] - rotation[0, 2] * rail_z) / rotation[0, 0]
    axis = rotation @ np.array([original_x, case["axis_y"], rail_z])
    normal = rotation @ np.array([0.0, 0.0, 1.0])
    floor = (case["floor_z"] - normal[0] * query_x - normal[1] * axis[1]) / normal[2]
    rail = (rail_z - normal[0] * query_x - normal[1] * axis[1]) / normal[2]
    return {"query_x": float(query_x), "axis_y": float(axis[1]), "floor_z": float(floor), "rail_z": float(rail)}


class SensitivityTrace(TraceDetector):
    @contextmanager
    def _observe_density(self):
        original = clustering.cluster_labels

        def labels(voxels, cfg):
            answer = original(voxels, cfg)
            caller = inspect.currentframe().f_back
            if caller.f_code is clustering.find_clusters.__code__:
                values = caller.f_locals
                ids, inv = values["frame_idx"], values["inv"]
                target = np.isin(ids, self.target_indices)
                assigned = answer[inv]
                self.trace.setdefault("density", []).append({
                    "kind": "low" if values.get("low_cfg") is not None else "corridor",
                    "candidate_points": len(ids), "target_points": int(target.sum()),
                    "target_voxels": int(np.unique(inv[target]).size),
                    "target_noise_points": int((target & (assigned < 0)).sum()),
                    "target_clustered_points": int((target & (assigned >= 0)).sum()),
                    "target_strict_points": int((target & values["in_gauge"]).sum()),
                    "eps": cfg.eps, "min_samples": cfg.min_samples,
                })
            return answer

        clustering.cluster_labels = labels
        try:
            yield
        finally:
            clustering.cluster_labels = original

    def _cluster(self, *args):
        with self._observe_density():
            return super()._cluster(*args)

    def _low_stage(self, *args):
        original = detector_module.low_candidates

        def observe(*positional, **kwargs):
            params = inspect.signature(original).bind(*positional, **kwargs).arguments
            captured = {}

            def profile(frame, event, value):
                if event == "return" and frame.f_code is original.__code__:
                    captured.update(frame.f_locals)

            previous = sys.getprofile()
            if previous is not None:
                raise RuntimeError("low-stage tracing requires an unused profile hook")
            sys.setprofile(profile)
            try:
                answer = original(*positional, **kwargs)
            finally:
                sys.setprofile(previous)
            ids = self.target_indices
            cfg, x, dy, height = (params[k] for k in ("cfg", "X", "dy", "h"))
            idx = captured.get("idx", np.empty(0, dtype=int))
            target = np.isin(idx, ids)
            record = {"configured_range_max": cfg.range_max, "height_reference_limit": params["x_limit"],
                      "observed_bed_range": float(answer[1]), "template_ready": params["template"].prof is not None,
                      "target_in_configured_range": int(((x[ids] >= params["range_min"]) & (x[ids] < cfg.range_max)).sum()),
                      "target_in_lateral_band": int((abs(dy[ids]) <= cfg.half_width).sum()),
                      "target_below_corridor_floor": int((height[ids] < params["h_bottom"]).sum()),
                      "target_above_point_top": int((height[ids] > cfg.min_point_top).sum()),
                      "target_selected": int(target.sum()),
                      "target_anomaly_points": int(np.isin(answer[2], ids).sum()),
                      "target_kept_points": int(np.isin(answer[0], ids).sum()),
                      "thresholds": {k: getattr(cfg, k) for k in ("half_width", "min_excess", "max_excess", "min_point_top")}}
            for key in ("res", "r", "h"):
                if key in captured and key != "h":
                    record[f"target_{key}_range"] = bounds(captured[key][target])
            for key in ("bed", "anomaly", "keep"):
                if key in captured:
                    record[f"target_{key}_points"] = int((captured[key] & target).sum())
            self.trace["bed"] = record
            return answer

        detector_module.low_candidates = observe
        try:
            return super()._low_stage(*args)
        finally:
            detector_module.low_candidates = original


def semantic_observation(row):
    # Instrumentation changes wall time and timing-only health warnings. Every actual output
    # used by this evaluation must match, including geometry, clear distance and decision.
    result = {key: value for key, value in row.items() if key != "health"}
    health = {key: value for key, value in row["health"].items() if key not in ("latency_p95_ms", "level", "messages")}
    health["messages"] = [message for message in row["health"].get("messages", []) if not message.startswith("latency p95 ")]
    result["health_without_timing"] = health
    return result


def run(args):
    manifest = load_json(args.cache / "manifest.json")
    baseline = load_json(args.baseline)
    if manifest["split"] != "development" or baseline["split"] != "development":
        raise ValueError("diagnostics are restricted to inspected development cases")
    if file_hash(args.cache / "manifest.json") != baseline["cache_manifest_sha256"]:
        raise ValueError("cache differs from baseline")
    cfg = DetectorConfig.from_yaml(str(args.config))
    source = source_identity(args.source_commit)
    if json_hash(asdict(cfg)) != baseline["config_sha256"] or source["detector_source_sha256"] != baseline["source"]["detector_source_sha256"]:
        raise ValueError("observer must use exactly the baseline detector and config")
    by_name = {c["case"]["name"]: c for c in baseline["cases"]}
    selected = set(args.cases.split(",")) if args.cases else {
        name for name, case in by_name.items() if case["case"]["positive"]
        and not case["encodings"]["float32"]["metrics"]["sustained"]}
    selected.add("person_150m_0")
    if selected - by_name.keys():
        raise ValueError(f"unknown cases: {sorted(selected - by_name.keys())}")
    report = {"schema": "resense.synthetic_stage_diagnosis.v1", "source": source,
              "config_sha256": baseline["config_sha256"], "baseline_sha256": file_hash(args.baseline),
              "cache_manifest_sha256": baseline["cache_manifest_sha256"], "runner_sha256": file_hash(__file__),
              "observer_sha256": file_hash(ROOT / "scripts/trace_detector_stages.py"),
              "synthetic_development_only": True, "instrumented_timing_valid": False,
              "output_parity_frames": 0, "cases": []}
    for case in manifest["cases"]:
        name = case["name"]
        if name not in selected:
            continue
        record = {"case": {k: v for k, v in case.items() if k != "frames"}, "encodings": {}}
        for encoding in args.encodings.split(","):
            if encoding not in ("float32", "compact16"):
                raise ValueError("encoding must be float32 or compact16")
            detector = SensitivityTrace(cfg)
            rows = []
            for source_row in case["frames"]:
                path = args.cache / source_row["file"]
                if file_hash(path) != source_row["sha256"]:
                    raise ValueError(f"cache hash differs: {path}")
                with np.load(path, allow_pickle=False) as saved:
                    raw, mask = saved["points"], saved["target_mask"]
                array = raw if encoding == "float32" else compact_to_compact16(raw)
                ids, size = filtered_targets(array, mask, cfg.sensor)
                frame = frame_from_compact(array, cfg.sensor, stamp=source_row["stamp_s"])
                if frame.n != size:
                    raise ValueError("target mask row mapping differs from production decoder")
                result = detector.process_target(frame, {name: ids})
                actual = observation(result, case, int(mask.sum()), source_row["index"], source_row["stamp_s"], manifest["protocol"]["matching"])
                expected = by_name[name]["encodings"][encoding]["rows"][source_row["index"]]
                if semantic_observation(actual) != semantic_observation(expected):
                    raise ValueError(f"instrumented output differs: {name}, {encoding}, frame {source_row['index']}")
                report["output_parity_frames"] += 1
                raw_points = frame.xyz[ids]
                true_h = raw_points[:, 2] - case["floor_z"] - 0.18
                true_dy = raw_points[:, 1] - case["axis_y"]
                x = float(np.mean(result.xyz[ids, 0])) if len(ids) else float(case["distance_m"])
                truth = true_surfaces(case, detector.mount_rotation, x)
                truth.update(fitted_axis_y=float(result.track.center_y(x)), fitted_floor_z=float(result.track.floor_z(x)),
                             fitted_rail_z=float(result.track.rail_z(x)), fitted_rail_offset=float(result.track.rail_offset))
                truth.update(axis_error=truth["fitted_axis_y"] - truth["axis_y"], floor_error=truth["fitted_floor_z"] - truth["floor_z"],
                             rail_error=truth["fitted_rail_z"] - truth["rail_z"])
                truth.update(target_physical_height_range=bounds(true_h), target_physical_lateral_range=bounds(true_dy),
                             target_physical_nominal_gauge_points=int(point_in_polygon(true_dy, true_h, cfg.gauge.profile).sum()))
                detector.trace["thin_clusters"] = [{**cluster_record(c, ids), "weak": bool(c.weak)}
                                                  for c in detector._thin if np.isin(c.points_idx, ids).any()]
                rows.append({"frame": source_row["index"], "source_file": source_row["file"],
                             "output": actual, "independent_geometry": truth, "trace": detector.trace})
            record["encodings"][encoding] = rows
        report["cases"].append(record)
        print(f"traced {name}; all {len(case['frames']) * len(record['encodings'])} outputs match baseline", flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(report, separators=(",", ":")) + "\n").encode()
    args.output.write_bytes(gzip.compress(data, mtime=0) if str(args.output).endswith(".gz") else data)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/default.yaml")
    parser.add_argument("--cases", help="defaults to all missed development positives plus person_150m_0")
    parser.add_argument("--encodings", default="float32,compact16")
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    try:
        return run(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    sys.exit(main())
