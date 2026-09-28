#!/usr/bin/env python3
"""Audit registered physical meshes against the canonical rail-relative envelope.

This uses mesh geometry, never detector fits or returned-point visibility. The profile
is the canonical GaugeConfig polygon; range-dependent decision margins are not geometry.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from resense.config import GaugeConfig  # noqa: E402

RAIL_HEIGHT_M = 0.18  # synthetic_tunnel_frame's actual rail mesh, not TrackModel's prior


def clip_rectangle(polygon, left, right, bottom, top):
    vertices = [np.asarray(p, float) for p in polygon]
    for axis, boundary, sign in ((0, left, 1), (0, right, -1), (1, bottom, 1), (1, top, -1)):
        clipped = []
        for a, b in zip(vertices, vertices[1:] + vertices[:1]):
            ain = sign * (a[axis] - boundary) >= -1e-12
            bin = sign * (b[axis] - boundary) >= -1e-12
            if ain:
                clipped.append(a)
            if ain != bin:
                clipped.append(a + (b - a) * (boundary - a[axis]) / (b[axis] - a[axis]))
        vertices = clipped
    return np.asarray(vertices)


def area(polygon):
    if len(polygon) < 3:
        return 0.0
    return float(abs(np.dot(polygon[:, 0], np.roll(polygon[:, 1], 1))
                     - np.dot(polygon[:, 1], np.roll(polygon[:, 0], 1))) / 2)


def physical_projection(case):
    """Exact lateral/height projection of the registered box/person meshes.

    Person follows obstacle_mesh: a 20-sided cylinder plus a sphere of radius 0.11,
    resolution 12. Its actual top is 0.85*declared_height+0.22, not declared_height.
    Longitudinal position does not affect this straight, constant envelope.
    """
    length, width, height = case["size_m"]
    yaw = np.radians(case.get("yaw_deg", 0.0))
    center = case["lateral_m"]
    base = -RAIL_HEIGHT_M
    if case["kind"] == "box":
        half = (abs(np.sin(yaw)) * length + abs(np.cos(yaw)) * width) / 2
        return [np.array([[center - half, base], [center + half, base],
                          [center + half, base + height], [center - half, base + height]])]
    if case["kind"] != "person":
        raise ValueError("geometry audit supports the registered box/person meshes only")
    angles = np.arange(20) * (2 * np.pi / 20) + yaw
    lateral = center + width / 2 * np.sin(angles)
    body = np.array([[lateral.min(), base], [lateral.max(), base],
                     [lateral.max(), base + height * .85], [lateral.min(), base + height * .85]])
    head = [[center, base + height * .85], [center, base + height * .85 + .22]]
    for i in range(1, 12):
        for j in range(24):
            theta, phi = i * np.pi / 12, j * 2 * np.pi / 24 + yaw
            head.append([center + .11 * np.sin(theta) * np.sin(phi),
                         base + height * .85 + .11 + .11 * np.cos(theta)])
    head = np.asarray(head)
    return [body, head[ConvexHull(head).vertices]]


def audit_case(case):
    profile = np.asarray(GaugeConfig().profile)
    left, bottom = profile.min(axis=0)
    right, top = profile.max(axis=0)
    if set(map(tuple, profile)) != {(left, bottom), (right, bottom), (right, top), (left, top)}:
        raise ValueError("canonical profile changed; rectangular audit must be revised")
    common = {"canonical_profile_m": profile.tolist(), "physical_rail_height_m": RAIL_HEIGHT_M,
              "physical_rail_head_z_m": case["floor_z"] + RAIL_HEIGHT_M,
              "uses_fitted_detector_geometry": False}
    if case["kind"] is None:
        return {**common, "classification": "empty", "body_intersects_envelope_interior": False,
                "body_touches_envelope_only": False}
    pieces = physical_projection(case)
    vertices = np.concatenate(pieces)
    clipped = [clip_rectangle(p, left, right, bottom, top) for p in pieces]
    overlap = sum(area(p) for p in clipped)
    interior = overlap > 1e-10
    touches = not interior and any(len(p) for p in clipped)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    return {**common, "classification": "interior" if interior else "boundary_only" if touches else "outside",
            "body_intersects_envelope_interior": bool(interior), "body_touches_envelope_only": bool(touches),
            "body_lateral_interval_m": [float(low[0]), float(high[0])],
            "body_bottom_above_rail_m": float(low[1]), "body_top_above_rail_m": float(high[1]),
            "body_top_z_m": float(case["floor_z"] + RAIL_HEIGHT_M + high[1]),
            "entire_body_below_rail_head": bool(high[1] < -1e-10),
            "vertical_envelope_overlap_m": float(max(0, min(high[1], top) - max(low[1], bottom))),
            "lateral_envelope_overlap_m": float(max(0, min(high[0], right) - max(low[0], left))),
            "projected_envelope_overlap_area_m2": overlap}


def main():
    from synthetic_sensitivity import file_hash, sequence_cases
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text())
    report = {"protocol_sha256": file_hash(args.protocol), "audit_script_sha256": file_hash(__file__),
              "note": "Geometry audit only. No clouds generated, no reserved detector outputs observed, no v1 labels changed.",
              "splits": {split: [{"name": c["name"], "registered_positive": c["positive"], **audit_case(c)}
                                  for c in sequence_cases(protocol, split)] for split in protocol["splits"]}}
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
