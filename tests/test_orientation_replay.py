"""Bounded real-input startup history, with unchanged confirmation thresholds."""
from copy import deepcopy

import numpy as np
import pytest

from resense.calibration import OrientationReplayBuffer, orientation_candidates
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame


def tiny(stamp=0, frame_id="test"):
    return Frame(np.zeros((0, 3), np.float32), np.zeros(0, np.float32), stamp=stamp,
                 frame_id=frame_id, meta={"nested": [1, 2]})


def test_buffer_owns_inputs_and_current_counts_toward_limit():
    buffer = OrientationReplayBuffer(2)
    frame = Frame(np.ones((5, 3), np.float32), np.ones(5, np.float32), np.arange(5, dtype=np.uint16),
                  meta={"nested": [1, 2]})
    assert buffer.capture(frame, None)
    frame.xyz[:] = 99
    frame.intensity[:] = 99
    frame.ring[:] = 99
    frame.meta["nested"][0] = 99
    saved = buffer.frames[0][0]
    assert saved.xyz.max() == saved.intensity.max() == 1
    assert saved.ring.max() == 4 and saved.meta["nested"] == [1, 2]
    assert buffer.capture(tiny(.1, frame_id=""), 2.0)
    assert not buffer.capture(tiny(.2, frame_id=""), None)
    assert buffer.reason == "frame_budget" and buffer.frames == [] and buffer.used_bytes == 0


@pytest.mark.parametrize("stamp", [0, -.1, 1.01, float("nan"), float("inf")])
def test_bad_or_discontinuous_stamp_discards_history(stamp):
    buffer = OrientationReplayBuffer(4)
    assert buffer.capture(tiny(), None)
    assert not buffer.capture(tiny(stamp), None)
    assert buffer.finished and not buffer.frames


def test_identity_metadata_and_byte_limits_are_bounded(monkeypatch):
    buffer = OrientationReplayBuffer(4)
    assert buffer.capture(tiny(), None)
    assert not buffer.capture(tiny(.1, "different"), None)
    assert buffer.reason == "input_discontinuity"
    monkeypatch.setattr(OrientationReplayBuffer, "MAX_BYTES", 2048)
    frame = tiny()
    frame.meta["large"] = "x" * 4096
    buffer = OrientationReplayBuffer(4)
    assert not buffer.capture(frame, None) and buffer.reason == "byte_budget"
    frame.meta = {"unsupported": object()}
    buffer = OrientationReplayBuffer(4)
    assert not buffer.capture(frame, None) and buffer.reason == "unsupported_input"


def test_object_dtype_scalar_cannot_hide_unbounded_metadata():
    frame = tiny()
    array = np.zeros(1, dtype=[("payload", object)])
    array["payload"][0] = ["unbounded mutable payload"]
    frame.meta = {"scalar": array[0]}
    buffer = OrientationReplayBuffer(4)
    assert not buffer.capture(frame, None)
    assert buffer.reason == "unsupported_input" and not buffer.frames


@pytest.mark.parametrize("budget", [-1, 5, 1.5, True])
def test_invalid_budget_rejected(budget):
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = budget
    with pytest.raises(ValueError, match="0 to 4"):
        Detector(cfg)


def test_reset_releases_pending_inputs_and_empty_input_never_goes_clear():
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = 4
    detector = Detector(cfg)
    result = detector.process(tiny())
    assert result.health["decision_level"] == "error" and result.clear_distance == 0
    assert not result.mount["orientation_confirmed"]
    assert len(detector._orientation_replay.frames) == 1
    detector.reset()
    assert detector._orientation_replay.reason == "scene_reset"
    assert not detector._orientation_replay.frames


def test_instrumentation_subclass_is_explicitly_skipped():
    class Instrumented(Detector):
        pass
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = 4
    result = Instrumented(cfg).process(tiny())
    assert result.mount["orientation_replay"]["reason"] == "unsupported_subclass"


@pytest.fixture(scope="module")
def obstacle_scene():
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    return synthetic_tunnel_frame(rng=np.random.default_rng(3),
                                  specs=[ObstacleSpec(kind="box", size=(.6, .6, .6), distance=40)])[0]


def input_frame(scene, rotation, index):
    return Frame((scene.xyz @ rotation.T).astype(np.float32), scene.intensity, scene.ring,
                 stamp=100 + .1 * index, frame_id="scene", meta=deepcopy(scene.meta))


def safety_record(result):
    return (result.obstacle, result.warning, result.nearest_distance,
            [item.to_dict() for item in result.detections], [item.to_dict() for item in result.warnings],
            result.track.to_dict(), result.clear_distance)


@pytest.mark.synthetic
@pytest.mark.parametrize("rotation", orientation_candidates(True)[1:])
def test_adoption_replay_equals_original_history_and_preserves_stops(obstacle_scene, rotation):
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = 4
    baseline, remounted = Detector(deepcopy(cfg)), Detector(deepcopy(cfg))
    adopted = None
    baseline_stops = 0
    for index in range(12):
        reference = baseline.process(input_frame(obstacle_scene, np.eye(3), index))
        result = remounted.process(input_frame(obstacle_scene, rotation, index))
        baseline_stops += reference.obstacle
        event = result.mount.get("orientation_replay")
        if event and event["status"] == "replayed":
            adopted = index
            assert event["frames"] == index + 1 <= 4
            assert event["bytes"] <= OrientationReplayBuffer.MAX_BYTES
            assert result.stamp == event["published_stamp"] == 100 + .1 * index
            assert result.timing_ms["total"] >= event["replay_ms"]
            assert remounted._previous_latency_ms == event["physical_call_ms"]
        if adopted is not None:
            assert safety_record(result) == safety_record(reference)
        else:
            assert result.health["decision_level"] in ("warn", "error")
            assert result.clear_distance == 0
    assert adopted == 1 and baseline_stops > 0


@pytest.mark.synthetic
def test_late_adoption_skips_history_and_publishes_current_stamp(obstacle_scene):
    cfg = DetectorConfig()
    cfg.calibration.orientation_replay_frames = 2
    cfg.calibration.orientation_votes = 3
    detector = Detector(cfg)
    for index in range(4):
        result = detector.process(input_frame(obstacle_scene, orientation_candidates(True)[1], index))
        assert result.stamp == 100 + .1 * index
        assert result.mount.get("orientation_replay", {}).get("status") != "replayed"
    assert detector.calib._config_passed
    assert detector._orientation_replay.reason == "frame_budget"
