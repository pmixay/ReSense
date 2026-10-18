#!/usr/bin/env python3
"""Materialize reviewed, temporally linked synthetic-object boxes from raw clouds.

The input JSON is an annotation artifact, not detector output. Its tracks were proposed
from raw geometry, intensity and temporal continuity, then reviewed in three projections.
Intensity 1 is a selection cue INSIDE a reviewed object volume, never an object label on
its own. Missing support stays explicit; an empty frame does not assert an obstacle-free
scene. No detector module, predicted decision or fitted detector axis is imported.

  python scripts/annotate_synthetic_tracks.py CACHE REVIEWED_BOXES.json --out LABELS.json

PointCloud2 cache axes: forward=-sensor_y, left=sensor_x, up=sensor_z. The source cache
already applies a radial 2.5--250 m filter. A valid label may have forward distance <2.5 m.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def mapped_points(cache: Path, frame: int):
    with np.load(cache / f"f_{frame:05d}.npz") as data:
        points = data["xyz"][:, [1, 0, 2]].copy()
        points[:, 0] *= -1
        return points, data["inten"].copy()


def selected_points(points, intensity, bounds, tolerance=2e-5):
    """Recover the supported returns of a reviewed volume, preserving echo duplicates."""
    lo, hi = np.asarray(bounds, dtype=float)
    if lo.shape != (3,) or hi.shape != (3,) or np.any(lo > hi):
        raise ValueError("invalid annotation bounds")
    return points[
        (intensity == 1.0)
        & np.all(points >= lo - tolerance, axis=1)
        & np.all(points <= hi + tolerance, axis=1)
    ]


def materialize(cache: Path, reviewed: dict):
    metadata = json.loads((cache / "meta.json").read_text())
    total = len(metadata)
    if reviewed["total_frames"] != total or [m["i"] for m in metadata] != list(
        range(total)
    ):
        raise ValueError("annotation/cache frame coverage differs")
    tracks = reviewed["tracks"]
    objects = reviewed["objects"]
    labels = {f"{k:05d}": [] for k in range(total)}
    support_changes = []
    summaries = {}
    unknown_frames = set(reviewed.get("coverage_unknown_frames", []))
    for name, track in tracks.items():
        definition = objects[name]
        rows = []
        for key, annotation in sorted(track.items(), key=lambda item: int(item[0])):
            frame = int(key)
            if not 0 <= frame < total:
                raise ValueError(f"{name}: frame {frame} outside bag")
            points, intensity = mapped_points(cache, frame)
            selected = selected_points(
                points, intensity, [annotation["lo"], annotation["hi"]]
            )
            if not len(selected):
                raise ValueError(
                    f"{name}/{frame}: reviewed box has no supporting raw return"
                )
            lo, hi = selected.min(axis=0), selected.max(axis=0)
            size = hi - lo
            unique = len(np.unique(selected, axis=0))
            if len(selected) != annotation["n"]:
                support_changes.append(
                    {
                        "name": name,
                        "frame": frame,
                        "proposal": annotation["n"],
                        "raw_recovered": len(selected),
                    }
                )
            confidence = annotation.get(
                "annotation_confidence", "high" if unique >= 4 else "sparse_support"
            )
            relation = definition["gauge_relation"]
            # The manually reviewed near-range relationship is not extrapolated through a curve.
            if (
                float(lo[0]) > 60.0
                or abs(float((lo[1] + hi[1]) / 2)) > 3.5
                or confidence == "uncertain"
            ):
                relation = "unknown"
            row = {
                "name": name,
                "label": name,
                "kind": definition["kind"],
                "distance": round(float(lo[0]), 5),
                "lateral": round(float((lo[1] + hi[1]) / 2), 5),
                "lateral_sensor": round(float((lo[1] + hi[1]) / 2), 5),
                "bbox": [
                    [round(float(v), 5) for v in lo],
                    [round(float(v), 5) for v in hi],
                ],
                "size": [round(float(v), 5) for v in size],
                "n_points": len(selected),
                "n_unique_points": unique,
                "gauge_relation": relation,
                "in_gauge": True
                if relation == "inside"
                else False
                if relation == "outside"
                else None,
                "annotation_confidence": confidence,
                "source": "team raw-point geometry and temporal annotation; reviewed volume + intensity cue",
                "coordinate_frame": "sensor_axis_mapped",
                "selection_epsilon_m": 2e-5,
                "gauge_basis": definition["gauge_basis"],
            }
            if confidence == "uncertain":
                unknown_frames.add(frame)
            labels[f"{frame:05d}"].append(row)
            rows.append((frame, row))
        summaries[name] = {
            **definition,
            "supported_rows": len(rows),
            "first_supported_frame": rows[0][0],
            "last_supported_frame": rows[-1][0],
            "first_supported_forward_m": rows[0][1]["distance"],
            "first_supported_confidence": rows[0][1]["annotation_confidence"],
            "missing_support_frames": [
                k for k in range(rows[0][0], rows[-1][0] + 1) if str(k) not in track
            ],
        }
        unknown_frames.update(summaries[name]["missing_support_frames"])
    for rows in labels.values():
        rows.sort(key=lambda row: row["name"])
    meta = {
        "schema": "resense-team-synthetic-annotations-v1",
        "bag": reviewed["bag"],
        "total_frames": total,
        "frames": total,
        "labelled_frames": total,
        "every": 1,
        "coordinate_frame": "sensor_axis_mapped",
        "frame_transform": ["-sensor_y", "sensor_x", "sensor_z"],
        "sensor_to_vehicle_identity": True,
        "identity_evidence": "archived full runs: mount pending for frames0--189, identity thereafter; "
        "calibration begins identity and no provisional rotation occurs",
        "radial_input_range_m": [2.5, 250.0],
        "source_sha256": reviewed["source_sha256"],
        "annotation_type": "team assisted annotations; not organizer labels or exact point truth",
        "source": "scripts/annotate_synthetic_tracks.py from reviewed raw-point box trajectories",
        "reviewed_all_frames": True,
        "review_method": reviewed["review_method"],
        "exhaustive_obstacles": False,
        "negative_scope": "all frames processed; no label row means no supported annotation, not a proven clear scene",
        "coverage_unknown_frames": sorted(unknown_frames),
        "coverage": {
            "frame_keys": total,
            "raw_candidate_sweep_frames": total,
            "supported_object_rows": sum(map(len, labels.values())),
            "frames_with_objects": sum(bool(rows) for rows in labels.values()),
            "frames_without_supported_objects": sum(
                not rows for rows in labels.values()
            ),
        },
        "support_changes_from_proposal": support_changes,
        "objects": summaries,
    }
    return {"_meta": meta, **labels}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("cache", type=Path)
    parser.add_argument("reviewed_boxes", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reviewed = json.loads(args.reviewed_boxes.read_text())
    result = materialize(args.cache, reviewed)
    result["_meta"]["reviewed_boxes_sha256"] = hashlib.sha256(
        args.reviewed_boxes.read_bytes()
    ).hexdigest()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as stream:
        stream.write('{\n "_meta": ' + json.dumps(result.pop("_meta"), indent=1))
        for frame, rows in result.items():
            stream.write(
                ',\n "' + frame + '": ' + json.dumps(rows, separators=(",", ":"))
            )
        stream.write("\n}\n")
    print(args.out)


if __name__ == "__main__":
    main()
