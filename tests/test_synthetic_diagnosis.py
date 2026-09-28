"""Truth/mask attribution in the read-only synthetic stage observer."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

from resense.calibration import rot_x, rot_y
from resense.config import SensorConfig
from resense.pointcloud import COMPACT_DTYPE

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("synthetic_diagnosis", ROOT / "scripts/diagnose_synthetic_sensitivity.py")
diagnosis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(diagnosis)


def test_target_mask_follows_exact_rows_after_background_range_filter():
    array = np.zeros(4, dtype=COMPACT_DTYPE)
    array["x"] = [1.0, 3.0, 24.0, np.nan]
    target, size = diagnosis.filtered_targets(array, [False, False, True, False], SensorConfig())
    assert size == 2
    assert target.tolist() == [1]


def test_independent_rail_truth_uses_mesh_height_and_follows_mount_rotation():
    case = {"floor_z": -1.5, "axis_y": 0.25}
    identity = diagnosis.true_surfaces(case, np.eye(3), 100.0)
    assert identity["rail_z"] == pytest.approx(-1.32)  # actual rail mesh is 0.18 m, not TrackModel's prior
    rotation = rot_y(np.radians(2.0)) @ rot_x(np.radians(-3.0))
    expected_axis = rotation @ [100.0, 0.25, -1.32]
    truth = diagnosis.true_surfaces(case, rotation, expected_axis[0])
    assert truth["axis_y"] == pytest.approx(expected_axis[1])
    assert truth["rail_z"] == pytest.approx(expected_axis[2])
    normal = rotation @ [0.0, 0.0, 1.0]
    assert np.dot(normal, [truth["query_x"], truth["axis_y"], truth["floor_z"]]) == pytest.approx(-1.5)


def test_parity_ignores_only_timing_health_changes():
    baseline = {"stop": False, "decision": "GO", "health": {
        "level": "ok", "decision_level": "ok", "latency_p95_ms": 30.0, "rail_lock": 1.0, "messages": []}}
    timed = {**baseline, "health": {**baseline["health"], "level": "warn", "latency_p95_ms": 250.0,
                                   "messages": ["latency p95 250 ms over the 100 ms budget"]}}
    assert diagnosis.semantic_observation(baseline) == diagnosis.semantic_observation(timed)
    timed["health"]["rail_lock"] = 0.0
    assert diagnosis.semantic_observation(baseline) != diagnosis.semantic_observation(timed)


@pytest.mark.parametrize("height,classification,overlap", [
    (.27, "outside", 0), (.30, "boundary_only", 0), (.31, "interior", .01), (.36, "interior", .06)])
def test_independent_body_audit_distinguishes_contact_from_volume(height, classification, overlap):
    from synthetic_geometry import audit_case
    result = audit_case({"kind": "box", "size_m": [.3, .3, height], "yaw_deg": 4,
                         "floor_z": -1.5, "lateral_m": 0})
    assert result["classification"] == classification
    assert result["vertical_envelope_overlap_m"] == pytest.approx(overlap)


def test_independent_body_audit_uses_actual_person_mesh_and_outside_footprint():
    from synthetic_geometry import audit_case
    case = {"kind": "person", "size_m": [.4, .5, 1.7], "yaw_deg": 0,
            "floor_z": -1.5, "lateral_m": 0}
    inside = audit_case(case)
    outside = audit_case({**case, "lateral_m": 1.6})
    assert inside["body_top_above_rail_m"] == pytest.approx(1.7 * .85 + .22 - .18)
    assert inside["classification"] == "interior"
    assert outside["classification"] == "outside"
    assert outside["vertical_envelope_overlap_m"] > 0
    assert outside["lateral_envelope_overlap_m"] == 0
