"""Far-structure research counterexamples, not a new rejection rule.

Small snapshot diagnostic (no detector replay)::

    python tests/test_far_structure.py --measurement D:/Datasets/ReSense/cross_ring_2026-09-28_measurement

The committed fixtures are unique centimetre-quantized XYZ support from
new_data_6.jsonl:331 at new_data_9263 and new_data_1.jsonl:298 at new_data_2671.
Model-relative dy/h are rounded to 0.1 mm. There are deliberately no reconstructed
channel IDs: those are absent from the NPZ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy.spatial import cKDTree

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.clustering import cluster_labels, find_clusters, voxelize
from resense.config import ClusterConfig, GaugeConfig
from resense.gauge import gauge_core_mask


FAR_BODY = np.array([
    [109.59, 12.89, -0.58, -0.0727, 0.2781],
    [110.58, 12.98, 1.15, -0.1869, 2.0073],
    [110.70, 12.85, 0.08, -0.3418, 0.9372],
    [110.71, 13.06, 0.63, -0.1338, 1.4872],
    [110.71, 13.18, -0.09, -0.0138, 0.7672],
    [110.72, 13.04, 0.39, -0.1559, 1.2472],
    [110.72, 13.05, 0.08, -0.1459, 0.9372],
    [110.73, 13.25, 0.08, 0.0520, 0.9372],
    [110.73, 13.44, 0.08, 0.2420, 0.9372],
    [110.74, 12.99, -0.09, -0.2101, 0.7672],
    [110.74, 13.26, 0.63, 0.0599, 1.4872],
    [110.75, 13.12, 0.85, -0.0821, 1.7072],
    [110.77, 12.85, 0.40, -0.3563, 1.2572],
    [110.77, 13.21, -0.37, 0.0037, 0.4872],
    [110.78, 12.81, 1.15, -0.3984, 2.0072],
    [110.79, 12.92, 0.85, -0.2904, 1.7072],
    [110.80, 12.88, 0.63, -0.3325, 1.4871],
    [110.80, 13.07, 1.37, -0.1425, 2.2271],
    [110.82, 12.88, 1.37, -0.3367, 2.2271],
    [110.83, 13.25, 0.40, 0.0313, 1.2571],
], dtype=np.float64)


FAR_FACE = np.array([
    [82.54, -1.45, -1.74, -1.0137, 0.4574],
    [85.24, -1.80, -1.80, -1.3458, 0.4370],
    [85.82, -1.66, -1.81, -1.2020, 0.4355],
    [89.08, -1.88, -1.88, -1.4000, 0.4134],
    [89.14, -1.72, -1.88, -1.2396, 0.4142],
    [89.25, -0.59, -2.06, -0.1088, 0.2358],
    [89.25, -0.28, -2.06, 0.2012, 0.2358],
    [89.26, -0.12, -2.06, 0.3612, 0.2360],
    [89.27, -0.43, -2.06, 0.0513, 0.2361],
    [89.29, -0.95, -1.88, -0.4686, 0.4164],
    [89.32, -0.01, -1.88, 0.4716, 0.4169],
    [89.33, -0.79, -1.88, -0.3083, 0.4170],
    [89.33, -0.63, -1.88, -0.1483, 0.4170],
    [89.33, -0.32, -1.88, 0.1617, 0.4170],
    [89.34, -0.48, -1.88, 0.0018, 0.4172],
    [89.34, -0.17, -1.88, 0.3118, 0.4172],
], dtype=np.float64)


# The only two distinct non-target returns joined to FAR_BODY by production
# range-normalized clustering of its saved context (each occurred twice).
FAR_BODY_CONTEXT = np.array([
    [114.40, 13.21, -0.85, -0.7596, 0.0043],
    [119.20, 13.68, -1.19, -1.3312, -0.3394],
], dtype=np.float64)


def _describe(xyz, dy, h):
    cfg = ClusterConfig()
    strict = gauge_core_mask(dy, h, xyz[:, 0], GaugeConfig())
    return find_clusters(xyz, np.full(len(xyz), 30.0), dy, h, strict, cfg)


def _grid(x, y, h):
    """Controlled obstacle support, in a straight frame with rail head at Z=-1.4."""
    q = np.stack(np.meshgrid(x, y, h, indexing="ij"), axis=-1).reshape(-1, 3)
    return np.column_stack((q[:, :2], q[:, 2] - 1.4)), q[:, 1], q[:, 2]


def _geometry(xyz, target, dy, h):
    """Read-only descriptors; tube and nearest-neighbour distance do not prove a connection.

    Deduplicate XYZ before PCA. Strict membership is rails-only, from the saved
    frame's coordinates; it is not an independently surveyed envelope. The 0.45 m
    tube is a fixed diagnostic window, not a candidate threshold.
    """
    q = np.unique(xyz[target], axis=0)
    if len(q) < 3:
        raise ValueError("snapshot needs at least three distinct current target points")
    strict = gauge_core_mask(dy, h, xyz[:, 0], GaugeConfig())
    s = np.unique(xyz[target & strict], axis=0)
    outside = xyz[~target]
    _, singular, axes = np.linalg.svd(q - q.mean(axis=0), full_matrices=False)
    tube = np.linalg.norm(xyz[:, :2] - np.median(q[:, :2], axis=0), axis=1) < 0.45
    v = np.unique(xyz[tube], axis=0)
    nearest = float(cKDTree(outside).query(q)[0].min()) if len(outside) else None
    return {
        "unique_target_points": len(q),
        "unique_rail_strict_points": len(s),
        "target_extent_m": np.ptp(q, axis=0).tolist(),
        "rail_strict_extent_m": np.ptp(s, axis=0).tolist() if len(s) else None,
        "principal_direction_abs_xyz": np.abs(axes[0]).tolist(),
        "principal_variance_share": float(singular[0] ** 2 / np.sum(singular ** 2)),
        "nearest_non_target_m": nearest,
        "vertical_tube_extent_m": float(np.ptp(v[:, 2])) if len(v) else None,
        "outside_tube_unique_points": len(np.unique(xyz[tube & ~target], axis=0)),
    }


def _connected_geometry(xyz, target):
    """Production metric applied to the *saved crop*, without a rejection decision."""
    cfg = ClusterConfig()
    vox, inv = voxelize(xyz, cfg)
    labels = cluster_labels(vox, cfg)[inv]
    seeds = np.unique(labels[target])
    selected = np.isin(labels, seeds[seeds >= 0])
    q = np.unique(xyz[selected], axis=0)
    _, _, axes = np.linalg.svd(q - q.mean(axis=0), full_matrices=False)
    return {
        "seed_component_labels": seeds.tolist(),
        "connected_unique_points": len(q),
        "connected_non_target_unique_points": len(np.unique(xyz[selected & ~target], axis=0)),
        "connected_extent_m": np.ptp(q, axis=0).tolist(),
        "connected_principal_direction_abs_xyz": np.abs(axes[0]).tolist(),
    }


def test_real_far_body_is_ordinary_gauge_support_not_a_thin_scanline():
    # Real failure mechanism: a compact, vertically resolved body wholly inside
    # the fitted strict gauge. Nine channels in the trace cannot classify its identity.
    xyz, dy, h = FAR_BODY[:, :3], FAR_BODY[:, 3], FAR_BODY[:, 4]
    clusters = _describe(xyz, dy, h)
    assert len(clusters) == 1
    c = clusters[0]
    assert c.zone == "gauge" and not c.reason and not c.thin and not c.weak
    assert c.n_gauge == c.n
    np.testing.assert_allclose(c.size, [1.24, 0.63, 1.95], atol=1e-5)


def test_real_far_full_cluster_direction_does_not_describe_its_strict_face():
    xyz, dy, h = FAR_FACE[:, :3], FAR_FACE[:, 3], FAR_FACE[:, 4]
    desc = _geometry(xyz, np.ones(len(xyz), bool), dy, h)
    assert desc["principal_direction_abs_xyz"][0] > 0.97
    assert desc["target_extent_m"][0] == pytest.approx(6.80)
    np.testing.assert_allclose(desc["rail_strict_extent_m"], [0.09, 0.94, 0.18], atol=1e-5)
    strict = gauge_core_mask(dy, h, xyz[:, 0], GaugeConfig())
    face = xyz[strict]
    _, _, axes = np.linalg.svd(face - face.mean(axis=0), full_matrices=False)
    assert abs(axes[0, 1]) > 0.99  # the in-gauge face is transverse, not along-track


def test_real_far_body_two_context_returns_flip_the_connected_shape_direction():
    data = np.concatenate((FAR_BODY, FAR_BODY_CONTEXT))
    target = np.arange(len(data)) < len(FAR_BODY)
    local = _geometry(data[:, :3], target, data[:, 3], data[:, 4])
    connected = _connected_geometry(data[:, :3], target)
    assert local["nearest_non_target_m"] > 3.16
    assert local["principal_direction_abs_xyz"][2] > 0.96
    assert connected["connected_non_target_unique_points"] == 2
    assert connected["connected_extent_m"][0] == pytest.approx(9.61)
    assert connected["connected_principal_direction_abs_xyz"][0] > 0.97
    assert len(connected["seed_component_labels"]) == 1


def test_person_can_also_join_farther_ground_returns_under_the_production_metric():
    person, dy, h = _grid([110.0], np.linspace(-0.25, 0.25, 4), np.linspace(0.1, 1.8, 10))
    # A local positive body with a pair of more distant low returns, like the real
    # negative's context. They must not make its original strict support a long line.
    outside = np.array([[113.6, 0.1, -1.55], [118.4, 0.4, -1.89]])
    xyz = np.concatenate((person, outside))
    target = np.arange(len(xyz)) < len(person)
    connected = _connected_geometry(xyz, target)
    assert connected["connected_non_target_unique_points"] == 2
    assert connected["connected_extent_m"][0] > ClusterConfig().max_extent
    assert connected["connected_principal_direction_abs_xyz"][0] > 0.96
    assert _describe(person, dy, h)[0].zone == "gauge"


@pytest.mark.parametrize("kind", ["person", "edge_cube", "plank", "above_box"])
def test_positive_obstacles_keep_ordinary_strict_support(kind):
    # Mechanism counterexamples only: sampled visible surfaces, not a recall benchmark.
    shapes = {
        "person": ([110.0], np.linspace(-0.25, 0.25, 4), np.linspace(0.1, 1.8, 10)),
        "edge_cube": ([110.0, 110.3], np.linspace(0.60, 0.90, 4), np.linspace(1.0, 1.3, 4)),
        "plank": (np.linspace(110.0, 112.2, 15), np.linspace(-0.5, 0.5, 6), [0.20, 0.30]),
        # A taller 2 m-wide object has only this lower strip below the envelope top.
        "above_box": ([110.0], np.linspace(-1.0, 1.0, 13), np.linspace(2.5, 2.95, 4)),
    }
    xyz, dy, h = _grid(*shapes[kind])
    clusters = _describe(xyz, dy, h)
    assert len(clusters) == 1
    assert clusters[0].zone == "gauge" and not clusters[0].reason
    assert not clusters[0].thin and not clusters[0].weak


def test_connected_vertical_context_can_hide_a_real_local_protrusion_in_global_pca():
    # A person beside a narrow vertical structure. Dense full-context PCA points
    # vertically even though the body protrudes 0.6 m from the structure's face.
    person, dy, h = _grid([110.0], np.linspace(0.20, 0.70, 4), np.linspace(0.1, 1.8, 10))
    column, cy, ch = _grid([110.0], [0.75, 0.80], np.linspace(0.0, 5.0, 120))
    cloud = np.concatenate((person, column))
    mask = np.arange(len(cloud)) < len(person)
    desc = _geometry(cloud, mask, np.r_[dy, cy], np.r_[h, ch])
    assert desc["nearest_non_target_m"] < 0.06
    _, _, axes = np.linalg.svd(cloud - cloud.mean(axis=0), full_matrices=False)
    assert abs(axes[0, 2]) > 0.99
    assert column[:, 1].max() - person[:, 1].min() == pytest.approx(0.60)
    assert _describe(person, dy, h)[0].zone == "gauge"


def _snapshot_report(measurement: Path):
    """All 15 far event onsets plus the nearer ordinary edge example; no cherry-picking."""
    trace_path = measurement / "false_target_trace" / "trace.json"
    inventory_path = measurement / "false_alarm_scenes_source" / "inventory.json"
    analysis_path = measurement / "false_alarm_analysis.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    assert trace["frames"] == 11271 and not trace["detection_mismatch_frames"]
    assert len(trace["events"]) == inventory["alarm_events"] == 32
    assert {e["key"] for e in trace["events"]} == {e["key"] for e in inventory["events"]}
    far = {e["key"] for e in analysis["events"] if max(e["range_m"]) >= 80}
    assert len(far) == 15
    rows = []
    for event in trace["events"]:
        if event["key"] not in far | {"new_data_5.jsonl:330"}:
            continue
        r = next(r for r in event["timeline"] if r["alarm"])
        # A stale track.last never supplies current-frame points to this diagnostic.
        assert r["misses"] == 0 and "point_snapshot" in r
        path = measurement / "false_target_trace" / "points" / r["point_snapshot"]
        with np.load(path, allow_pickle=False) as z:
            assert int(z["target"].sum()) == r["cluster"]["n_points_idx"]
            geometry = _geometry(z["xyz"], z["target"], z["dy"], z["h"])
            connected = _connected_geometry(z["xyz"], z["target"])
        rows.append({"key": event["key"], "frame": r["frame_id"],
                     "snapshot": r["point_snapshot"],
                     "snapshot_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                     "trace_strict_rings": r["cluster"]["ring_count"],
                     "trace_n_gauge_voxels": r["cluster"]["n_gauge"],
                     **geometry, **connected})
    return {"status": "diagnostic_only_no_rejection_candidate",
            "input_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in (trace_path, inventory_path, analysis_path)},
            "events": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(_snapshot_report(args.measurement), indent=2))
