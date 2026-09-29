"""Observation parity and coordinate/provenance counterexamples for direct fresh trace."""
from dataclasses import asdict

import numpy as np
import pytest

from resense import clustering
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.track import TrackModel
from scripts.analyze_quality_candidates import semantic
from scripts.trace_fresh_support import SupportTraceDetector, common_reference, jsonable


def observation(xyz, *, center=0., rail=0., rotation=None, stamp=0., strict=None):
    xyz = np.asarray(xyz, float)
    return {"frame_id": str(stamp), "stamp": stamp,
            "rotation": np.eye(3) if rotation is None else rotation,
            "model": asdict(TrackModel(np.zeros(3), (0., 200.), center, 0., 0., rail)),
            "support": {"xyz": xyz, "strict": np.ones(len(xyz), bool) if strict is None else strict}}


def test_common_reference_removes_axis_and_height_jump_without_moving_points():
    xyz = [[80., .2, .6], [80., .3, .7]]
    old = observation(xyz)
    new = observation(xyz, center=.8, rail=.6, stamp=.1)
    result = common_reference(old, new)
    assert result["whole"]["own_rail_dy_gap_m"] == pytest.approx(.7)
    assert result["whole"]["own_rail_h_gap_m"] == pytest.approx(.5)
    assert result["whole"]["common_rail_dy_gap_m"] == 0.
    assert result["whole"]["common_rail_h_gap_m"] == 0.
    assert result["old_reference_delta_on_old_points"]["dy"] == pytest.approx([-.8, -.8])
    assert not result["identity_established"]


def test_common_reference_undoes_mount_rotation_before_reference_projection():
    a = .05
    rotation = np.array([[np.cos(a), -np.sin(a), 0.], [np.sin(a), np.cos(a), 0.], [0., 0., 1.]])
    xyz = np.array([[80., .2, .6], [80., .3, .7]])
    old = observation(xyz)
    new = observation(xyz @ rotation.T, rotation=rotation, stamp=.1)
    result = common_reference(old, new)
    assert result["mount_changed"]
    assert result["whole"]["common_sensor_y_gap_m"] == pytest.approx(0.)
    assert result["whole"]["common_rail_dy_gap_m"] == pytest.approx(0.)


def test_common_reference_does_not_erase_real_visible_support_gap_or_invent_strict_points():
    old = observation([[40., -.3, .5], [40., -.2, .6]], strict=[False, False])
    new = observation([[38., .5, .5], [38., .6, .6]], stamp=.2)
    result = common_reference(old, new)
    assert result["whole"]["common_sensor_y_gap_m"] == pytest.approx(.7)
    assert result["stage_strict"]["common_rail_dy_gap_m"] is None
    assert not result["ego_translation_applied"]


def test_stale_observation_cannot_be_used_as_current_point_support():
    old = observation([[40., 0., .5]])
    new = observation([[38., 0., .5]], stamp=.1)
    new["support"] = None
    with pytest.raises(ValueError, match="current support required"):
        common_reference(old, new)


def test_direct_observer_preserves_stateful_outputs_and_actual_note_calls():
    cloud, labels, _ = synthetic_tunnel_frame(rng=np.random.default_rng(12), specs=[
        ObstacleSpec(kind="box", size=(.3, .3, .3), distance=25, lateral=0, base_z=-.2)])
    cfg = DetectorConfig()
    cfg.tracking.fresh_stop_evidence = True
    # The fixture exercises ordinary/low descriptor routing, not the separate hanging stage.
    cfg.cluster.hanging_enabled = False
    plain = Detector(cfg)
    traced = SupportTraceDetector(DetectorConfig.from_dict(cfg.to_dict()))
    original = clustering._corridor_cluster
    observed = []
    for k in range(8):
        frame = Frame(cloud.xyz, cloud.intensity, stamp=.1 * k, frame_id=str(k))
        result, records = traced.process_observed(frame, range(1, 100))
        assert semantic(result.to_dict()) == semantic(plain.process(frame).to_dict())
        assert clustering._corridor_cluster is original
        for row in records:
            assert row["hit"]["input_source"] == "ordinary"
            assert row["hit"]["evidence_after"] == row["after"]["evidence_hist"]
            support = row["support"]
            ids = np.asarray(support["frame_idx"])
            np.testing.assert_allclose(support["configured_xyz"], frame.xyz[ids])
            assert len(ids) == row["cluster"]["n_points_idx"]
            assert len(set(support["voxel_ids"])) == row["cluster"]["n_voxels"]
        observed.extend(records)
    assert any(r["fresh_gate_calls"] for r in observed)
    assert any(np.any(labels[np.asarray(r["support"]["frame_idx"])]) for r in observed)
    empty = Frame(np.zeros((0, 3), np.float32), np.zeros(0, np.float32), stamp=.8, frame_id="miss")
    result, records = traced.process_observed(empty, range(1, 100))
    assert semantic(result.to_dict()) == semantic(plain.process(empty).to_dict())
    assert records
    assert all(r["after"]["misses"] > 0 and r["support"] is None and r["hit"] is None for r in records)


def test_trace_json_is_portable_and_nonfinite_state_is_explicitly_missing():
    import json
    value = jsonable({"since_clean": float("inf"), "flag": np.bool_(True), "ids": np.arange(2)})
    assert json.loads(json.dumps(value, allow_nan=False)) == {"since_clean": None, "flag": True, "ids": [0, 1]}
