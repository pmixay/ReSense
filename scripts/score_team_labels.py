#!/usr/bin/env python3
"""Score frozen team annotations without converting uncertain gauge labels to negatives.

This is a point-supported, object-level diagnostic, not organizer ground truth or a
release gate. All frame IDs must be present in both files. Matching uses sensor/vehicle
3D geometry and maximum-cardinality one-to-one assignments; bounds retain matching and
gauge uncertainty. No detector decision, track estimate or detection creates a label.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

RELATIONS = {"inside", "outside", "boundary_uncertain", "unknown"}
EXPECTED_FRAMES = {"synthetic_platform": 386, "synthetic_switch": 736, "synthetic_tunnels": 545}
PROTOCOL = {
    "version": "team-labels-v1",
    "forward_range_m": [0.0, 250.0],
    "near_range": "raw decoder radial 2.5 m filter is not a 2.5 m forward-distance threshold",
    "forward_tolerance": "max(2 m, 3% of target min-forward) + half target forward extent",
    "lateral_tolerance": "1 m between sensor/vehicle bbox centres",
    "vertical_tolerance": "0.5 m maximum gap between observed vertical extents",
    "assignment": "maximum-cardinality one-to-one; all valid assignments retained as bounds",
    "population": "positive-return annotation rows within range; gauge certainty kept separately",
    "unmatched": "unresolved unless annotations explicitly declare exhaustive_obstacles=true",
    "held": "90% of supported rows at that distance or nearer; assignment lower bound",
}


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _box(value):
    if not isinstance(value, list):
        raise TypeError("bbox must be a list")
    if len(value) == 6:
        lo, hi = value[::2], value[1::2]
    elif len(value) == 2 and all(isinstance(v, list) and len(v) == 3 for v in value):
        lo, hi = value
    else:
        raise ValueError("bbox must be [[xmin,ymin,zmin],[xmax,ymax,zmax]] or six interleaved limits")
    lo = [_number(v, "bbox minimum") for v in lo]
    hi = [_number(v, "bbox maximum") for v in hi]
    if any(a > b for a, b in zip(lo, hi)):
        raise ValueError("bbox minimum exceeds maximum")
    return lo, hi


def validate_labels(labels):
    meta = labels.get("_meta", {})
    count = meta.get("total_frames")
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("_meta.total_frames must be a positive integer")
    if meta.get("bag") in EXPECTED_FRAMES and count != EXPECTED_FRAMES[meta["bag"]]:
        raise ValueError("frame count does not match the complete known recording")
    if meta.get("coordinate_frame") != "sensor_axis_mapped" or meta.get("sensor_to_vehicle_identity") is not True:
        raise ValueError("these captures require verified sensor_axis_mapped == vehicle identity coordinates")
    expected = {f"{i:05d}" for i in range(count)}
    if {k for k in labels if not k.startswith("_")} != expected:
        raise ValueError("labels must contain every frame exactly once, with five-digit frame keys")
    unknown = meta.get("coverage_unknown_frames", [])
    if not isinstance(unknown, list) or any(type(v) is not int or not 0 <= v < count for v in unknown):
        raise ValueError("coverage_unknown_frames must contain valid integer frame indices")
    for key in sorted(expected):
        if not isinstance(labels[key], list):
            raise TypeError(f"{key}: annotation rows must be a list")
        names = set()
        for row in labels[key]:
            name = row.get("name")
            if not isinstance(name, str) or not name or name in names:
                raise ValueError(f"{key}: object names must be nonempty and unique per frame")
            names.add(name)
            relation = row.get("gauge_relation")
            if relation not in RELATIONS:
                raise ValueError(f"{key}/{name}: explicit gauge_relation required")
            expected_gauge = True if relation == "inside" else False if relation == "outside" else None
            if "in_gauge" not in row or row["in_gauge"] is not expected_gauge:
                raise ValueError(f"{key}/{name}: in_gauge must preserve gauge uncertainty as null")
            points = row.get("n_points")
            if type(points) is not int or points < 0:
                raise ValueError(f"{key}/{name}: n_points must be a nonnegative integer")
            lo, _ = _box(row.get("bbox"))
            if abs(_number(row.get("distance"), "distance") - lo[0]) > 0.051:
                raise ValueError(f"{key}/{name}: distance must equal bbox minimum forward (rounding <=5 cm)")
    return meta


def _detection(raw):
    centre = raw.get("c", raw.get("center"))
    size = raw.get("size")
    if not isinstance(centre, (list, tuple)) or len(centre) != 3:
        raise ValueError("detections need a three-dimensional vehicle centre; track lateral is not a substitute")
    if not isinstance(size, (list, tuple)) or len(size) != 3:
        raise ValueError("detections need three-dimensional size")
    centre = [_number(v, "detection centre") for v in centre]
    size = [_number(v, "detection size") for v in size]
    if min(size) < 0:
        raise ValueError("detection sizes must be nonnegative")
    return {"distance": _number(raw.get("d", raw.get("distance")), "detection distance"),
            "centre": centre, "size": size}


def normalize_results(results, count):
    rows = []
    for raw in results:
        index = raw.get("i", raw.get("frame"))
        if type(index) is not int:
            raise ValueError("result frame must be an integer")
        decision = raw.get("decision")
        if decision not in {"GO", "CAUTION", "STOP", "FAULT"}:
            raise ValueError("results must retain their actual decision")
        for key in ("obstacle", "warning"):
            if type(raw.get(key)) is not bool:
                raise ValueError(f"result {key} must be boolean")
        rows.append({"frame": index, "decision": decision,
                     "dets": [_detection(d) for d in raw.get("dets", raw.get("detections", []))],
                     "warns": ([_detection(d) for d in raw.get("warns", raw.get("warnings", []))]
                               if raw["warning"] else [])})
    if [r["frame"] for r in rows] != list(range(count)):
        raise ValueError("results must contain every frame once in chronological order")
    return rows


def compatible(det, target):
    lo, hi = _box(target["bbox"])
    distance = float(target["distance"])
    tolerance = max(2.0, 0.03 * distance) + (hi[0] - lo[0]) / 2
    dzlo = det["centre"][2] - det["size"][2] / 2
    dzhi = det["centre"][2] + det["size"][2] / 2
    vertical_gap = max(lo[2] - dzhi, dzlo - hi[2], 0.0)
    return (abs(det["distance"] - distance) <= tolerance
            and abs(det["centre"][1] - (lo[1] + hi[1]) / 2) <= 1.0
            and vertical_gap <= 0.5)


def _cardinality(graph, selected=None):
    """Maximum bipartite matching, object -> detection; no greedy assignment bias."""
    matched = {}

    def augment(obj, seen):
        for det in graph[obj]:
            if det in seen:
                continue
            seen.add(det)
            if det not in matched or augment(matched[det], seen):
                matched[det] = obj
                return True
        return False

    for obj in range(len(graph)) if selected is None else selected:
        augment(obj, set())
    return len(matched)


def match_bounds(graph, selected):
    """Bounds among maximum-cardinality assignments for a selected object subset."""
    selected = set(selected)
    maximum = _cardinality(graph)
    other = [i for i in range(len(graph)) if i not in selected]
    return [maximum - _cardinality(graph, other), _cardinality(graph, sorted(selected))]


def _add_interval(destination, key, bounds):
    total = destination.setdefault(key, [0, 0])
    total[0] += bounds[0]
    total[1] += bounds[1]


def _held(rows):
    hits = 0
    held = None
    # Equal-distance rows enter as a group; ordering ties must not improve this statistic.
    groups = {}
    for row in rows:
        groups.setdefault(row["distance"], []).append(row)
    count = 0
    for distance, group in sorted(groups.items()):
        hits += sum(r["stop_match"][0] for r in group)
        count += len(group)
        if hits >= 0.9 * count:
            held = distance
    return held


def score(results, labels):
    meta = validate_labels(labels)
    rows = normalize_results(results, meta["total_frames"])
    objects, summary, frame_scores = {}, {}, []
    relation_counts, exclusions, decisions = Counter(), Counter(), Counter()
    unknown_coverage = set(meta.get("coverage_unknown_frames", []))
    exhaustive = meta.get("exhaustive_obstacles") is True and meta.get("reviewed_all_frames") is True
    for result in rows:
        index = result["frame"]
        decisions[result["decision"]] += 1
        targets = []
        for target in labels[f"{index:05d}"]:
            if target["n_points"] == 0:
                exclusions["no_point_support"] += 1
            elif not 0.0 <= target["distance"] <= 250.0:
                exclusions["outside_range"] += 1
            else:
                targets.append(target)
        # An object proposal in a non-STOP frame is not a matched STOP.
        dets = result["dets"] if result["decision"] == "STOP" else []
        graph = [[di for di, det in enumerate(dets) if compatible(det, target)] for target in targets]
        warnings = [[wi for wi, warn in enumerate(result["warns"]) if compatible(warn, target)]
                    for target in targets]
        certain = [i for i, t in enumerate(targets) if t["gauge_relation"] == "inside"]
        possible = [i for i, t in enumerate(targets) if t["gauge_relation"] != "outside"]
        outside = [i for i, t in enumerate(targets) if t["gauge_relation"] == "outside"]
        matched = _cardinality(graph)
        true_bounds = [match_bounds(graph, certain)[0], match_bounds(graph, possible)[1]]
        false_bounds = match_bounds(graph, outside)
        unmatched = len(dets) - matched
        if exhaustive and index not in unknown_coverage:
            false_bounds = [len(dets) - true_bounds[1], len(dets) - true_bounds[0]]
        else:
            # Ambiguous matched targets can be outside; all unmatched alarms remain unresolved.
            false_bounds[1] = len(dets) - true_bounds[0]
        _add_interval(summary, "true_stop_detections_bounds", true_bounds)
        _add_interval(summary, "false_stop_detections_bounds", false_bounds)
        _add_interval(summary, "certain_inside_matched_bounds", match_bounds(graph, certain))
        summary["certain_inside_object_frames"] = summary.get("certain_inside_object_frames", 0) + len(certain)
        summary["possible_inside_object_frames"] = summary.get("possible_inside_object_frames", 0) + len(possible)
        summary["unmatched_stop_detections"] = summary.get("unmatched_stop_detections", 0) + unmatched
        summary["stop_detections"] = summary.get("stop_detections", 0) + len(dets)
        summary["stop_frames_without_geometry"] = summary.get("stop_frames_without_geometry", 0) + int(
            result["decision"] == "STOP" and not dets)
        if dets:
            frame_scores.append({"frame": index, "detections": len(dets), "true_bounds": true_bounds,
                                 "false_bounds": false_bounds, "unmatched": unmatched,
                                 "coverage_exhaustive": exhaustive and index not in unknown_coverage})
        for i, target in enumerate(targets):
            relation_counts[target["gauge_relation"]] += 1
            item = {"frame": index, "distance": target["distance"], "gauge_relation": target["gauge_relation"],
                    "stop_match": match_bounds(graph, [i]), "warning_match": match_bounds(warnings, [i]),
                    "decision": result["decision"]}
            objects.setdefault(target["name"], []).append(item)
    object_report = {}
    for name, observations in sorted(objects.items()):
        stop_lower = [r for r in observations if r["stop_match"][0]]
        stop_upper = [r for r in observations if r["stop_match"][1]]
        inside_rows = [r for r in observations if r["gauge_relation"] == "inside"]
        bins = {}
        for low, high in zip([0, 30, 60, 100, 150], [30, 60, 100, 150, 250]):
            population = [r for r in observations if low <= r["distance"] < high
                          or (high == 250 and r["distance"] == 250)]
            if population:
                bins[f"{low}-{high}"] = {
                    "supported": len(population),
                    "stop_match_bounds": [sum(r["stop_match"][j] for r in population) for j in (0, 1)],
                    "gauge_relation_frames": dict(Counter(r["gauge_relation"] for r in population)),
                }
        object_report[name] = {
            "point_supported_frames": len(observations),
            "first_frame": observations[0]["frame"], "last_frame": observations[-1]["frame"],
            "first_visible_m": max(r["distance"] for r in observations),
            "gauge_relation_frames": dict(Counter(r["gauge_relation"] for r in observations)),
            "stop_match_frames_bounds": [len(stop_lower), len(stop_upper)],
            "first_stop_frame_certain_assignment": min((r["frame"] for r in stop_lower), default=None),
            "first_stop_m_certain_assignment": max((r["distance"] for r in stop_lower), default=None),
            "first_stop_m_possible_assignment": max((r["distance"] for r in stop_upper), default=None),
            "stop_held_from_m_certain_assignment": _held(observations),
            "certain_inside_frames": len(inside_rows),
            "certain_inside_stop_frames_bounds": [sum(r["stop_match"][j] for r in inside_rows) for j in (0, 1)],
            "warning_match_frames_bounds": [sum(r["warning_match"][j] for r in observations) for j in (0, 1)],
            "bins_m": bins,
            "observations": observations,
        }
    denominator = summary["certain_inside_object_frames"]
    summary["certain_inside_recall_bounds"] = ([v / denominator for v in summary["certain_inside_matched_bounds"]]
                                                if denominator else None)
    return {"protocol": PROTOCOL, "frames": len(rows), "decisions": dict(sorted(decisions.items())),
            "coverage": {"all_frame_ids_present": True, "reviewed_all_frames": meta.get("reviewed_all_frames") is True,
                         "exhaustive_obstacles": exhaustive, "unknown_frames": sorted(unknown_coverage)},
            "annotation_gauge_relation_frames": dict(sorted(relation_counts.items())),
            "excluded_object_frames": dict(exclusions), "summary": summary,
            "objects": object_report, "stop_frames": frame_scores}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.resolve() in {args.results.resolve(), args.gt.resolve()}:
        parser.error("output must not overwrite input evidence")
    try:
        opener = gzip.open if args.results.suffix == ".gz" else open
        with opener(args.results, "rt", encoding="utf-8") as stream:
            results = [json.loads(line) for line in stream if line.strip()]
        labels = json.loads(args.gt.read_text())
        report = score(results, labels)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))
    report["inputs"] = {"results": str(args.results), "labels": str(args.gt),
                        "results_sha256": hashlib.sha256(args.results.read_bytes()).hexdigest(),
                        "labels_sha256": hashlib.sha256(args.gt.read_bytes()).hexdigest(),
                        "scorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"frames": report["frames"], "objects": len(report["objects"]), "summary": report["summary"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
