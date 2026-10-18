"""Associate complete Falcon replay outputs with independently reviewed raw geometry.

Association is not surveyed gauge truth. Unsupported/unknown targets are never
counted as negatives, and interpolation never crosses an unsupported 25-frame gap.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

FOLDER = Path(__file__).resolve().parent
PANDAR = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=float)
STATIC = {
    "static_support_105": [[105.35, 1.4, -6.7], [105.9, 2.1, -3.4]],
    "static_support_115": [[114.8, 1.4, -7.2], [115.5, 2.15, -4.0]],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def references():
    proposals = json.loads((FOLDER / "raw_person_review/atlas_proposals.json").read_text())
    manual = {r["frame"]: r for r in json.loads((FOLDER / "falcon_reviewed_anchors.json").read_text())["anchors"]}
    anchors = {"main_approach": {}, "early_uncertain": {}}
    for row in proposals["anchors"]:
        frame = row["frame"]
        episode = row["episode"]
        if row.get("review_status") != "reviewed_trajectory_body_core":
            raise ValueError(f"Trajectory review is not frozen at {frame}")
        box = row["discovery_bbox"]
        if frame in manual and manual[frame].get("bbox_raw"):
            box = manual[frame]["bbox_raw"]
        anchors[episode][frame] = np.asarray(box)
    by_frame = {}
    for episode, points in anchors.items():
        indices = sorted(points)
        for frame in indices:
            by_frame.setdefault(frame, {})[episode] = points[frame]
        for left, right in zip(indices, indices[1:]):
            if right - left > 25:
                continue
            for frame in range(left + 1, right):
                weight = (frame - left) / (right - left)
                by_frame.setdefault(frame, {})[episode] = points[left] * (1 - weight) + points[right] * weight
    return anchors, by_frame


def in_box(point, box, margin):
    bounds = np.asarray(box)
    return bool(np.all(point >= bounds[0] - margin) and np.all(point <= bounds[1] + margin))


def load_rows(path):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if len(rows) != 4443 or [r["i"] for r in rows] != list(range(4443)):
        raise ValueError(f"A complete, ordered 4,443-frame replay is required: {path}")
    return rows


def summarize(rows, case, by_frame):
    associated = {name: {"stop": [], "advisory": [], "tight_stop": []}
                  for name in (*STATIC, "main_approach", "early_uncertain")}
    unmatched_stop, overlapping_stop = [], []
    windows = []
    first_stamp = rows[0]["stamp"]
    for window in range(9):
        chunk = [r for r in rows if window * 50 <= r["stamp"] - first_stamp < (window + 1) * 50]
        windows.append({"seconds": [window * 50, min((window + 1) * 50, rows[-1]["stamp"] - first_stamp)],
                        "first_frame": chunk[0]["i"], "last_frame": chunk[-1]["i"], "frames": len(chunk),
                        "decisions": dict(Counter(r["decision"] for r in chunk)),
                        "axis_valid_median": float(np.median([r["track_detail"]["axis_valid"] for r in chunk])),
                        "clear_median": float(np.median([r["clear"] for r in chunk]))})
    for row in rows:
        frame = row["i"]
        rotation = np.asarray(row["mount_rotation"])
        if case in ("baseline", "candidate_auto"):
            rotation = rotation @ PANDAR
        boxes = dict(STATIC, **by_frame.get(frame, {}))
        for field, kind in (("dets", "stop"), ("warns", "advisory")):
            frame_matches = set()
            for detection in row[field]:
                raw_center = np.asarray(detection["c"]) @ rotation
                matched = []
                for name, box in boxes.items():
                    margin = np.array([.5, .3, .7]) if name in STATIC else np.array([1., .6, 1.2])
                    if in_box(raw_center, box, margin):
                        frame_matches.add(name)
                        matched.append(name)
                        if kind == "stop" and in_box(raw_center, box, np.array([.5, .35, .5])):
                            associated[name]["tight_stop"].append(frame)
                if kind == "stop" and not matched:
                    unmatched_stop.append(frame)
                if kind == "stop" and len(matched) > 1:
                    overlapping_stop.append(frame)
            for name in frame_matches:
                associated[name][kind].append(frame)
    for name, counts in associated.items():
        for key in ("stop", "advisory", "tight_stop"):
            counts[key] = sorted(set(counts[key]))
        counts["stop_frames"] = len(counts["stop"])
        counts["advisory_frames"] = len(counts["advisory"])
        counts["first_stop_frame"] = counts["stop"][0] if counts["stop"] else None
        counts["first_advisory_frame"] = counts["advisory"][0] if counts["advisory"] else None
        if name not in STATIC:
            covered = sorted(f for f, boxes in by_frame.items() if name in boxes)
            counts["covered_frames"] = len(covered)
            for label, first in (("stop", counts["first_stop_frame"]), ("advisory", counts["first_advisory_frame"])):
                counts[f"first_{label}_raw_forward_m"] = float(by_frame[first][name][0, 0]) if first is not None else None
            hits = np.array([f in counts["stop"] for f in covered], dtype=int)
            suffix = np.cumsum(hits[::-1])[::-1] / np.arange(len(hits), 0, -1)
            eligible = np.flatnonzero((suffix >= .9) & (hits == 1))
            first = covered[int(eligible[0])] if eligible.size else None
            counts["suffix_90pct_association_frame"] = first
            counts["suffix_90pct_raw_forward_m"] = float(by_frame[first][name][0, 0]) if first is not None else None
        for window in windows:
            for kind in ("stop", "advisory"):
                window[f"{name}_{kind}_frames"] = sum(window["first_frame"] <= f <= window["last_frame"] for f in counts[kind])
    return {"frames": len(rows), "decisions": dict(Counter(r["decision"] for r in rows)),
            "associated_targets": associated,
            "frames_with_any_unassociated_stop_detection": sorted(set(unmatched_stop)),
            "multiply_associated_stop_frames": sorted(set(overlapping_stop)), "windows": windows}


def compare(left, right):
    keys = ("decision", "dets", "warns", "nearest", "clear", "monitored")
    return {key: [a["i"] for a, b in zip(left, right) if a[key] != b[key]] for key in keys}


def main():
    anchors, by_frame = references()
    paths = {name: FOLDER / "falcon_full" / (name + ".jsonl")
             for name in ("baseline", "explicit_ros", "native_explicit")}
    candidate = FOLDER / "falcon_replay_candidate/baseline.jsonl"
    if (candidate.parent / "summary.json").exists():
        paths["candidate_auto"] = candidate
    rows = {name: load_rows(path) for name, path in paths.items()}
    result = {
        "interpretation": "Raw-geometry associations, not exact surveyed gauge TP/FP or exhaustive obstacle truth. Unassociated outputs remain unknown.",
        "reference_method": "Reviewed raw anchors and every25-frame linked proposals; linear interpolation only within25frames; two separated episodes never joined.",
        "person_center_matching_margin_m": [1., .6, 1.2],
        "tight_margin_sensitivity_m": [.5, .35, .5],
        "static_center_matching_margin_m": [.5, .3, .7],
        "source_hashes": {str(p.relative_to(FOLDER)): digest(p) for p in [*paths.values(), FOLDER / "motion_discovery.json", FOLDER / "falcon_reviewed_anchors.json", FOLDER / "raw_person_review/atlas_proposals.json"]},
        "anchor_frames": {episode: sorted(points) for episode, points in anchors.items()},
        "cases": {name: summarize(data, name, by_frame) for name, data in rows.items()},
        "native_vs_explicit_ros_mismatches": compare(rows["native_explicit"], rows["explicit_ros"]),
    }
    if "candidate_auto" in rows:
        result["candidate_auto_vs_explicit_ros_mismatches"] = compare(rows["candidate_auto"], rows["explicit_ros"])
    (FOLDER / "falcon_full_associations.json").write_text(json.dumps(result, indent=2) + "\n")
    for case, report in result["cases"].items():
        print(case, report["decisions"], {name: {k: target[k] for k in ("stop_frames", "advisory_frames", "first_stop_frame")}
                                         for name, target in report["associated_targets"].items()})


if __name__ == "__main__":
    main()
