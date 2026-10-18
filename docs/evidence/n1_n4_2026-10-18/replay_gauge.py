#!/usr/bin/env python3
"""Replay the shared display projection on complete node-decoded recordings.

This is detector + display-function replay, not a ROS/DDS latency test. The saved
curves expose jitter AND lag/availability; unsupported far geometry is never drawn.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from ros2_ws.src.resense_ros.resense_ros.gauge_display import GaugeDisplay  # noqa: E402
from ros2_ws.src.resense_ros.resense_ros.decision_policy import decision  # noqa: E402

EXPECTED_FRAMES = {"cloud_with_fake_obj": 1510, "doubleT_obstacle": 201,
                   "roundT_doubleT": 252, "doubleT_platform": 345}


def source_hashes():
    paths = (list((ROOT / "resense").rglob("*.py"))
             + list((ROOT / "resense/models").rglob("*.json"))
             + list((ROOT / "resense").glob("*.so"))
             + list((ROOT / "native").rglob("*.cpp"))) + [
        ROOT / "ros2_ws/src/resense_ros/resense_ros/gauge_display.py",
        ROOT / "configs/default.yaml", Path(__file__)]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def quantiles(values):
    return {f"p{q}": float(np.percentile(values, q)) if len(values) else None for q in (50, 90, 95, 100)}


def replay(cache, output):
    cfg = DetectorConfig.from_yaml(ROOT / "configs/default.yaml")
    replay_clock = [0.0]
    detector = Detector(cfg)
    display = GaugeDisplay(cfg.gauge.range_min, cfg.gauge.range_max, clock=lambda: replay_clock[0])
    meta = json.loads((cache / "meta.json").read_text())
    rotation = axis_matrix(cfg.sensor).astype(np.float32)
    records, decisions, unchanged = [], Counter(), True
    start = time.monotonic()
    with gzip.open(output, "wt") as stream:
        for item in meta:
            index = item["i"]
            with np.load(cache / f"f_{index:05d}.npz") as data:
                frame = Frame(data["xyz"] @ rotation.T, data["inten"],
                              data["ring"] if item["has_ring"] else None,
                              stamp=item["stamp"], frame_id=item["frame_id"],
                              meta={"n_raw": item["n_raw"], "n_near": item["n_near"]})
            result = detector.process(frame)
            replay_clock[0] = result.stamp
            before = result.to_dict()
            speed = result.ego_speed if result.ego_speed is not None else (
                result.ego_speed_estimate if result.ego_speed_confidence >= .5 else None)
            status = display.update(result.track, result.stamp, result.health, speed)
            unchanged &= result.to_dict() == before
            word = decision(result)
            decisions[word] += 1
            record = {"frame": index, "decision": word, "gauge": status,
                      "stamp": result.stamp, "display_speed_mps": speed,
                      "result": before,
                      "track": result.track.to_dict(), "health": result.health,
                      "clear_distance": result.clear_distance,
                      "raw_y": result.track.center_y(np.array([40., 80., 120.])).tolist(),
                      "raw_z": result.track.rail_z(np.array([40., 80., 120.])).tolist(),
                      "display_y": display.center[[40, 80, 120]].tolist() if display.center is not None else None,
                      "display_z": display.rail[[40, 80, 120]].tolist() if display.rail is not None else None,
                      "outline_present": bool(display.outline(cfg.gauge.profile))}
            records.append(record)
            stream.write(json.dumps(record, allow_nan=False) + "\n")
            if (index + 1) % 250 == 0:
                print(cache.name, index + 1, flush=True)
    jitter = {}
    for j, distance in enumerate((40, 80, 120)):
        paired = [(a, b) for a, b in zip(records, records[1:])
                  if a["gauge"]["valid"] and b["gauge"]["valid"]
                  and min(a["gauge"]["solid_range_m"], b["gauge"]["solid_range_m"]) >= distance]
        raw = [abs(b["raw_y"][j] - a["raw_y"][j]) for a, b in paired]
        shown = [abs(b["display_y"][j] - a["display_y"][j]) for a, b in paired]
        jitter[str(distance)] = {"same_supported_adjacent_pairs": len(paired),
                                 "all_adjacent_pairs": len(records)-1,
                                 "raw_supported_adjacent_pairs": sum(
                                     min(a["track"]["axis_valid"], b["track"]["axis_valid"],
                                         a["health"].get("monitored_range", 0),
                                         b["health"].get("monitored_range", 0)) >= distance
                                     for a, b in zip(records, records[1:])),
                                 "raw_step_m": quantiles(raw), "display_step_m": quantiles(shown),
                                 "display_to_raw_lag_m": quantiles([abs(b["display_y"][j]-b["raw_y"][j]) for _, b in paired])}
        jitter[str(distance)]["raw_3d_vertex_step_m"] = quantiles([
            np.hypot(b["raw_y"][j] - a["raw_y"][j], b["raw_z"][j] - a["raw_z"][j])
            for a, b in paired])
        jitter[str(distance)]["display_3d_vertex_step_m"] = quantiles([
            np.hypot(b["display_y"][j] - a["display_y"][j], b["display_z"][j] - a["display_z"][j])
            for a, b in paired])
        all_pairs = [(a, b) for a, b in zip(records, records[1:]) if a["display_y"] and b["display_y"]]
        jitter[str(distance)]["all_state_raw_step_m"] = quantiles([abs(b["raw_y"][j]-a["raw_y"][j]) for a, b in all_pairs])
        jitter[str(distance)]["all_state_display_step_m_not_all_drawn"] = quantiles([abs(b["display_y"][j]-a["display_y"][j]) for a, b in all_pairs])
        jitter[str(distance)]["all_state_raw_3d_vertex_step_m"] = quantiles([
            np.hypot(b["raw_y"][j]-a["raw_y"][j], b["raw_z"][j]-a["raw_z"][j]) for a, b in all_pairs])
        jitter[str(distance)]["all_state_display_3d_vertex_step_m_not_all_drawn"] = quantiles([
            np.hypot(b["display_y"][j]-a["display_y"][j], b["display_z"][j]-a["display_z"][j]) for a, b in all_pairs])
    missing = [r["frame"] for r in records if r["decision"] in ("GO", "STOP") and not r["outline_present"]]
    missing_supported = [r["frame"] for r in records if r["frame"] in missing
                         and r["health"].get("monitored_range", 0) > cfg.gauge.range_min
                         and r["track"]["axis_valid"] > cfg.gauge.range_min
                         and r["health"].get("level") in ("ok", "warn")]
    violations = [r["frame"] for r in records if r["gauge"]["solid_range_m"] > r["track"]["axis_valid"] + .051]
    report = {"recording": cache.name, "frames": len(records), "elapsed_s": time.monotonic()-start,
              "decisions": dict(decisions), "detector_results_unchanged": unchanged,
              "scope": "complete decoded-frame detector replay + actual shared display function; transport freshness not simulated",
              "jitter": jitter, "missing_GO_STOP_outline_frames": missing,
              "missing_supported_GO_STOP_outline_frames": missing_supported,
              "solid_exceeds_axis_valid_frames": violations,
              "valid_display_frames": sum(r["gauge"]["valid"] for r in records),
              "drawn_range_m": quantiles([r["gauge"]["drawn_range_m"] for r in records]),
              "support_range_m": quantiles([r["gauge"].get("support_range_m", 0) for r in records]),
              "lag_limited_frames": sum(r["gauge"]["reason"] == "range_limited_by_display_lag" for r in records),
              "max_lateral_lag_m": quantiles([r["gauge"]["max_lateral_lag_m"] for r in records if r["gauge"]["max_lateral_lag_m"] is not None]),
              "max_vertical_lag_m": quantiles([r["gauge"]["max_vertical_lag_m"] for r in records if "max_vertical_lag_m" in r["gauge"]]),
              "max_spatial_lag_m": quantiles([r["gauge"]["max_spatial_lag_m"] for r in records if "max_spatial_lag_m" in r["gauge"]]),
              "smoothing_sources": dict(Counter(r["gauge"]["smoothing"] for r in records)),
              "cache_meta_sha256": hashlib.sha256((cache/'meta.json').read_bytes()).hexdigest(),
              "rows_sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    expected = EXPECTED_FRAMES.get(cache.name)
    report["expected_frame_count"] = expected
    report["numeric_checks"] = {
        "complete_expected_recording": expected is not None and len(records) == expected
                                       and [r["frame"] for r in records] == list(range(expected)),
        "detector_results_unchanged": unchanged,
        "no_missing_supported_GO_STOP_outline": not missing_supported,
        "solid_range_within_axis_support": not violations,
        "drawn_spatial_lag_at_most_025m": all(r["gauge"].get("max_spatial_lag_m", 0) <= .25 for r in records),
        **{f"visible_3d_p90_at_{distance}m": jitter[str(distance)]["display_3d_vertex_step_m"]["p90"] is not None
           and jitter[str(distance)]["display_3d_vertex_step_m"]["p90"] <= limit
           for distance, limit in ((40, .05), (80, .08), (120, .15))}}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=Path('/home/resense/data/decoded'))
    parser.add_argument("--rows", type=Path, default=Path('/home/resense/data/n1_display'))
    parser.add_argument("--reports", type=Path, default=Path(__file__).parent)
    parser.add_argument("bags", nargs='+')
    args = parser.parse_args()
    args.rows.mkdir(parents=True, exist_ok=True)
    args.reports.mkdir(parents=True, exist_ok=True)
    before = source_hashes()
    for bag in args.bags:
        result = replay(args.cache_root / bag, args.rows / (bag + '.jsonl.gz'))
        result['source_sha256_at_start'] = before
        result['source_sha256_at_end'] = source_hashes()
        result['source_changed_during_run'] = before != result['source_sha256_at_end']
        result['numeric_checks']['source_unchanged'] = not result['source_changed_during_run']
        result['numeric_screen_passed'] = all(result['numeric_checks'].values())
        (args.reports / (bag+'.json')).write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
