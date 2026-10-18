"""Independent review of the offline clean-transform observation contract."""

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from resense.calibration import MountCalibrator, orientation_candidates, rot_x
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from scripts.dust_reference import process_clean_reference, source_frame_sha256


def _frame(xyz, index=0):
    return Frame(np.asarray(xyz, np.float32), np.ones(len(xyz), np.float32),
                 stamp=100 + .1 * index, frame_id="review", meta={"n_raw": len(xyz)})


def _model():
    return SimpleNamespace(rail_z=lambda x: np.zeros_like(x) - 1.5)


def test_identity_shortcut_records_applied_identity_not_tiny_state_rotation():
    detector = Detector(DetectorConfig())
    detector.calib.state.R = rot_x(1e-10)
    frame = _frame([[10, 1, -1.5]])

    def process(value):
        assert detector.calib.apply(value.xyz) is value.xyz
        return SimpleNamespace(track=_model())

    detector.process = process
    original = MountCalibrator.apply
    _, reference = process_clean_reference(detector, frame)
    assert MountCalibrator.apply is original
    assert np.array_equal(reference["input_to_model_rotation"], np.eye(3))
    assert not np.array_equal(detector.mount_rotation, np.eye(3))
    assert reference["source_frame_sha256"] == source_frame_sha256(frame)


def test_failed_clean_processing_restores_class_method():
    detector = Detector(DetectorConfig())

    def process(frame):
        detector.calib.apply(frame.xyz)
        raise RuntimeError("independent failure probe")

    detector.process = process
    original = MountCalibrator.apply
    with pytest.raises(RuntimeError, match="independent failure probe"):
        process_clean_reference(detector, _frame([[10, 1, -1.5]]))
    assert MountCalibrator.apply is original


@pytest.mark.synthetic
def test_actual_orientation_adoption_and_fresh_replay_capture_final_applied_cloud():
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame

    scene = synthetic_tunnel_frame(
        rng=np.random.default_rng(3),
        specs=[ObstacleSpec(kind="box", size=(.6, .6, .6), distance=40)])[0]
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = 4
    observed, ordinary = Detector(deepcopy(cfg)), Detector(deepcopy(cfg))
    rotation = orientation_candidates(True)[1]
    original = MountCalibrator.apply
    first_calibrator = observed.calib
    replay_seen = False
    for index in range(3):
        frame = Frame((scene.xyz @ rotation.T).astype(np.float32), scene.intensity,
                      scene.ring, stamp=100 + .1 * index, frame_id="review",
                      meta=deepcopy(scene.meta))
        clean_hash = source_frame_sha256(frame)
        baseline = ordinary.process(frame)
        result, reference = process_clean_reference(observed, frame)
        applied = np.asarray(reference["input_to_model_rotation"], np.float32)
        assert MountCalibrator.apply is original
        assert source_frame_sha256(frame) == clean_hash == reference["source_frame_sha256"]
        assert np.array_equal(result.xyz, frame.xyz @ applied.T)
        assert np.array_equal(result.xyz, baseline.xyz)
        assert reference["rail_z_at20"] == float(result.track.rail_z(np.array([20.]))[0])
        for name in ("stamp", "obstacle", "warning", "nearest_distance", "clear_distance"):
            assert getattr(result, name) == getattr(baseline, name)
        assert result.track.to_dict() == baseline.track.to_dict()
        assert [d.to_dict() for d in result.detections] == [d.to_dict() for d in baseline.detections]
        assert [d.to_dict() for d in result.warnings] == [d.to_dict() for d in baseline.warnings]
        if result.mount.get("orientation_replay", {}).get("status") == "replayed":
            assert observed.calib is not first_calibrator
            replay_seen = True
    assert replay_seen
