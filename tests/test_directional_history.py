"""New ring-free side recovery keeps the correct startup without changing old yaw recovery."""
import numpy as np
import pytest

from resense import Detector, DetectorConfig
from resense.calibration import MountCalibrator, rot_x, rot_y, rot_z
from resense.frame import Frame


def _fov():
    az, el = np.meshgrid(np.linspace(-1., 1., 130), np.linspace(-.2, .1, 20))
    rays = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1).reshape(-1, 3)
    return (rays * np.linspace(4, 100, len(rays))[:, None]).astype(np.float32)


def test_automatic_history_requires_a_first_frame_directional_up_conflict():
    cfg = DetectorConfig()
    xyz = _fov()
    side = (xyz @ rot_x(np.pi / 2).T).astype(np.float32)
    yaw = (xyz @ rot_z(np.pi / 2).T).astype(np.float32)
    def cal():
        return MountCalibrator(cfg.calibration, cfg.track)
    assert cal().directional_startup_history(side, None)
    assert not cal().directional_startup_history(xyz, None)
    assert not cal().directional_startup_history(yaw, None)
    assert not cal().directional_startup_history(side, np.zeros(len(side), np.uint16))
    late = cal()
    late._frames = 1
    assert not late.directional_startup_history(side, None)


def test_default_replay_stays_off_for_existing_orientation_families():
    xyz = _fov()
    for rotation in (np.eye(3), rot_z(np.pi / 2), rot_x(np.pi)):
        det = Detector()
        p = (xyz @ rotation.T).astype(np.float32)
        det.process(Frame(p, np.ones(len(p), np.float32), stamp=.1))
        assert det.cfg.calibration.orientation_replay_frames == 0
        assert det._orientation_replay.max_frames == 0


def test_ring_free_side_startup_owns_its_input_with_existing_budget():
    p = (_fov() @ rot_x(np.pi / 2).T).astype(np.float32)
    det = Detector()
    result = det.process(Frame(p, np.ones(len(p), np.float32), stamp=.1))
    buffer = det._orientation_replay
    assert buffer.max_frames == 4
    assert buffer.peak_bytes <= buffer.MAX_BYTES
    assert len(buffer.frames) == 1
    saved = buffer.frames[0][0].xyz.copy()
    p[:] = 0
    assert np.array_equal(buffer.frames[0][0].xyz, saved)
    assert result.stamp == .1


@pytest.mark.parametrize('rotation', [
    np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], dtype=np.float32),
    np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=np.float32),
])
def test_new_side_recovery_matches_the_correct_startup_model_and_observations(tunnel, rotation):
    frame, _, _ = tunnel
    xyz = frame.xyz.copy()
    xyz[:, 1] -= .6  # Offset track makes an incorrect default prior observable.
    xyz = (xyz @ rot_y(np.radians(-2.4)).T).astype(np.float32)
    cfg = DetectorConfig()
    cfg.calibration.frames, cfg.calibration.obs_spacing = 5, 1
    correct, side = Detector(cfg), Detector(cfg)
    for i in range(8):
        expected = correct.process(Frame(xyz, frame.intensity, stamp=.1 * i))
        recovered = side.process(Frame(xyz @ rotation.T, frame.intensity, stamp=.1 * i))
        if i >= 1:
            assert side.calib._canonical_axes
            assert side.calib._recent == correct.calib._recent
            assert side.calib._obs == correct.calib._obs
            assert recovered.track.to_dict() == expected.track.to_dict()
            assert [d.to_dict() for d in recovered.detections] == [d.to_dict() for d in expected.detections]
            assert len(recovered.candidates) == len(expected.candidates)
        if i == 1:
            assert recovered.mount['orientation_replay']['trigger'] == 'directional_up_axis'
            assert recovered.mount['orientation_replay']['frames'] == 2
        assert recovered.stamp == expected.stamp
