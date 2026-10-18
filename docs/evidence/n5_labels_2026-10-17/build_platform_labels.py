#!/usr/bin/env python3
"""Build platform team labels from preserved exact labels and reviewed raw boxes.

The input boxes are annotations, not detector predictions. Re-extract intensity-1
points only inside those reviewed boxes. Optional reference checking measures this
same extraction on frames 255--314 where exact source scans exist.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "scripts"))
from label_marked_objects import exact_points  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(cache, frame, box):
    with np.load(cache / f"f_{frame:05d}.npz") as data:
        xyz = data["xyz"]
        points = xyz[:, [1, 0, 2]].copy()
        points[:, 0] *= -1
        selected = np.all((points >= box["lo"]) & (points <= box["hi"]), axis=1)
        selected &= data["inten"] == 1
    if int(selected.sum()) != box["n"]:
        raise ValueError(f"reviewed annotation count changed at frame {frame}")
    return xyz, points, selected


def relation(row):
    if row["distance"] > 60 or not row.get("plausible", True):
        return "unknown"
    return {"obj01": "boundary_uncertain", "obj02": "outside", "obj03": "inside"}[row["name"]]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cache", type=Path)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--out", type=Path, default=HERE / "labels_synthetic_platform.json")
    args = ap.parse_args()
    exact_path = HERE.parent / "synthetic_labels_2026-10-17/labels_synthetic_platform_0-314.json"
    boxes_path = HERE / "platform_reviewed_boxes.json"
    exact = json.loads(exact_path.read_text())
    boxes = json.loads(boxes_path.read_text())["obj03"]
    rows = {f"{k:05d}": copy.deepcopy(exact[f"{k:05d}"]) for k in range(315)}
    for k in range(315, 386):
        _, points, selected = extract(args.cache, k, boxes[str(k)])
        obj = points[selected]
        lo, hi = obj.min(0), obj.max(0)
        rows[f"{k:05d}"] = [{
            "name": "obj03", "label": "obj03", "kind": "inserted",
            "bbox": [lo.tolist(), hi.tolist()], "size": (hi - lo).tolist(),
            "distance": float(lo[0]), "lateral_sensor": float((lo[1] + hi[1]) / 2),
            "n_points": len(obj), "plausible": True,
            "source": "team_reviewed_shape_temporal_extension",
            "geometry_uncertainty": "Bounding box may include sparse background returns; see exact control.",
        }]
    for frame, objects in rows.items():
        for row in objects:
            if "in_gauge" in row:
                row["original_gauge_measured"] = row["in_gauge"]
                row["original_axis_lateral"] = row["lateral"]
            row["lateral"] = row["lateral_sensor"]
            row["gauge_relation"] = relation(row)
            row["in_gauge"] = {"inside": True, "outside": False}.get(row["gauge_relation"])
            row["annotation_confidence"] = "high" if row["n_points"] >= 10 else "sparse_support"
            row["gauge_basis"] = (
                "near-scene geometry; edge box remains uncertain; no organizer intent provided"
                if row["gauge_relation"] != "unknown"
                else "far-range track placement or plausibility not independently resolved"
            )
    registry = {}
    for name in ("obj01", "obj02", "obj03"):
        occurrences = [(int(k), r) for k, rs in rows.items() for r in rs if r["name"] == name]
        registry[name] = {
            "description": {"obj01": "box at rail boundary", "obj02": "box outside near corridor",
                            "obj03": "person-shaped inserted object"}[name],
            "frames": [occurrences[0][0], occurrences[-1][0]],
            "visible_rows": len(occurrences),
            "organizer_intent": "not supplied",
        }
    meta = {
        "bag": "synthetic_platform", "frames": 386, "total_frames": 386,
        "labelled_frames": 386, "unlabelled_frames": [], "every": 1,
        "coordinate_frame": "sensor_axis_mapped", "frame_transform": ["-sensor_y", "sensor_x", "sensor_z"],
        "sensor_to_vehicle_identity": True,
        "detector_transform": "identity_pending_or_identity_mount_verified",
        "transform_evidence": "all archived v100/v110 mount states pending or identity; see annotation review",
        "range_filter_m": [2.5, 250], "scope": "development data; team annotations, not organizer truth",
        "source": "exact reference labels through314; reviewed raw-shape extension315..385",
        "source_sha256": {str(exact_path.relative_to(REPO)): sha(exact_path),
                          boxes_path.name: sha(boxes_path)},
        "reviewed_all_frames": True, "exhaustive_obstacles": False,
        "coverage_unknown_frames": [],
        "frame_coverage": {str(k): {"status": "exact_reference" if k < 315 else "reviewed",
                                    "unresolved_tracks": []} for k in range(386)},
        "review_limit": "Reference region is exact for inserted points. Tail reviewed at every frame; absence of all possible real obstacles is not asserted.",
        "objects": registry,
    }
    args.out.write_text(json.dumps({"_meta": meta, **rows}, indent=2) + "\n")
    if args.reference:
        checks = []
        for k in range(255, 315):
            xyz, points, selected = extract(args.cache, k, boxes[str(k)])
            with np.load(args.reference / f"f_{k + 1195:05d}.npz") as ref:
                indices = exact_points(xyz, ref["xyz"])
            truth = np.zeros(len(xyz), dtype=bool)
            truth[indices] = True
            mid = (boxes[str(k)]["lo"][0] + boxes[str(k)]["hi"][0]) / 2
            truth &= np.abs(points[:, 0] - mid) < 1
            checks.append({
                "frame": k, "tp": int(np.sum(truth & selected)),
                "fp": int(np.sum(~truth & selected)), "fn": int(np.sum(truth & ~selected)),
                "truth": int(truth.sum()), "selected": int(selected.sum()),
                "bbox_abs_error_m": np.abs(np.array([points[selected].min(0), points[selected].max(0)])
                                            - np.array([points[truth].min(0), points[truth].max(0)])).tolist(),
            })
        totals = {key: sum(r[key] for r in checks) for key in ("tp", "fp", "fn", "truth", "selected")}
        result = {"definition": "Same reviewed-box extraction versus exactly-new person points; 60 control frames255..314",
                  "frames": checks, "total": totals,
                  "point_precision": totals["tp"] / totals["selected"],
                  "point_recall": totals["tp"] / totals["truth"],
                  "max_bbox_abs_error_m": np.max([r["bbox_abs_error_m"] for r in checks], axis=0).tolist()}
        (args.out.parent / "platform_extension_control.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({k: v for k, v in result.items() if k != "frames"}))
    print(f"Wrote {args.out}: 386 frames, {sum(map(len, rows.values()))} object rows")


if __name__ == "__main__":
    main()
