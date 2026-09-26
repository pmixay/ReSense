"""T1: missing boundary evidence cannot resolve an observed contradiction."""
import numpy as np
import pytest

from resense.calibration import rot_y
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.track import TrackModel, estimate_track


def model(sides=2, disagreement=0.0, valid=180.0):
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4, 150),
                      center=0.0, yaw=0.0, curvature=0.0, axis_sides=sides,
                      axis_disagreement=disagreement, axis_valid=valid, rail_slabs=5)


def observe(det, **kw):
    det.track = model(**kw)
    det._update_axis_trust()
    return det.track.effective_axis_valid


def contradict(det):
    return observe(det, disagreement=2 * det.cfg.track.axis_sides_max_disagreement, valid=60.0)


def test_contradiction_holds_and_tightens_until_fresh_agreement():
    det = Detector()
    assert contradict(det) == 60.0
    for kw, expected in [({'sides': 1, 'disagreement': None, 'valid': 120}, 60),
                         ({'sides': 0, 'disagreement': None, 'valid': 40}, 40),
                         ({'sides': 1, 'disagreement': None, 'valid': 120}, 40),
                         ({'disagreement': .002, 'valid': 60}, 40),
                         ({'disagreement': None, 'valid': 180}, 40),
                         ({'disagreement': float('nan'), 'valid': 180}, 40)]:
        assert observe(det, **kw) == expected
    assert observe(det, disagreement=det.cfg.track.axis_sides_max_disagreement) == 180
    assert det._axis_contradiction_cap is None
    assert observe(det, sides=1, disagreement=None, valid=120) == 120


def test_initial_one_side_is_unchanged_and_reset_releases():
    det = Detector()
    assert observe(det, sides=1, disagreement=None, valid=120) == 120
    contradict(det)
    det.tracker.reset()
    assert observe(det, sides=1, disagreement=None, valid=120) == 60
    det._frame_dt(1000)
    assert observe(det, sides=1, disagreement=None, valid=120) == 60
    det.reset()
    assert det._axis_contradiction_cap is None
    assert observe(det, sides=1, disagreement=None, valid=120) == 120


@pytest.mark.parametrize('disable', ['walls', 'disagreement'])
def test_disabled_rule_preserves_baseline(disable):
    det = Detector()
    contradict(det)
    if disable == 'walls':
        det.cfg.track.walls_enabled = False
    else:
        det.cfg.track.axis_sides_max_disagreement = 0
    assert observe(det, sides=1, disagreement=None, valid=120) == 120
    assert det._axis_contradiction_cap is None


def test_failed_floor_fit_does_not_reuse_prior_agreement(monkeypatch):
    det = Detector()
    contradict(det)
    prior = model(disagreement=0.0)
    monkeypatch.setattr('resense.track._fit_floor', lambda *args, **kw: None)
    held = estimate_track(np.empty((0, 3)), det.cfg.track, prior)
    assert prior.axis_disagreement == 0.0  # previous results remain immutable
    assert held.axis_sides == 2 and held.axis_disagreement is None
    det.track = held
    det._update_axis_trust()
    assert det.track.effective_axis_valid == 60
    assert held.axis_valid == prior.axis_valid == 180
    np.testing.assert_array_equal(held.floor_coef, prior.floor_coef)


def test_fresh_estimate_records_two_side_evidence_only(monkeypatch):
    cfg = DetectorConfig().track
    cfg.rails_enabled = False
    cfg.floor_verify_enabled = False
    monkeypatch.setattr('resense.track._fit_floor', lambda *args, **kw: (np.array([0., 0., -1.5]), (4, 150), 20, .01))
    for sides in (1, 2):
        monkeypatch.setattr('resense.track.estimate_axis_from_walls',
                            lambda *args, **kw: (0., 0., .1, 165., sides, .001, 165., 0))
        fit = estimate_track(np.zeros((10, 3)), cfg)
        assert fit.axis_sides == sides
        assert fit.axis_disagreement == (.001 if sides == 2 else None)


def test_trust_does_not_change_raw_geometry_and_telemetry_names_effective_bound():
    det = Detector()
    contradict(det)
    original = model(sides=1, disagreement=None, valid=120)
    before = original.to_dict()
    det.track = original
    det._update_axis_trust()
    xyz = np.array([[30., 0., -.5], [100., 0., -.5]], dtype=np.float32)
    _, _, _, _, (valid, axis_valid, _) = det._corridor(xyz, np.ones(2))
    assert valid == axis_valid == 60
    assert original.axis_valid == 120
    out = original.to_dict()
    assert out['axis_valid'] == 60 and out['axis_observed_range'] == 120
    assert out['axis_contradiction_cap'] == 60
    assert {k: v for k, v in out.items() if k not in ('axis_valid', 'axis_observed_range', 'axis_contradiction_cap')} == {
        k: v for k, v in before.items() if k != 'axis_valid'}


def mock_calibration(det, monkeypatch, change):
    def update(*args, **kw):
        det.calib.state.R = rot_y(np.radians(change))
        det.calib.last_change_deg = change
        det.calib.last_change_orientation = False
        return True
    monkeypatch.setattr(det.calib, 'update', update)


@pytest.mark.parametrize('change', [.5, 2.0])
def test_mount_reseed_or_rotation_alone_cannot_release(monkeypatch, change):
    det = Detector()
    contradict(det)
    calls = []
    def fit(*args, **kw):
        calls.append(kw.get('prev'))
        return model(sides=1, disagreement=None, valid=120)
    monkeypatch.setattr('resense.detector.estimate_track', fit)
    mock_calibration(det, monkeypatch, change)
    det._fit_track(np.zeros((3, 3), dtype=np.float32))
    assert det.track.effective_axis_valid == 60
    assert len(calls) == (1 if change == .5 else 2)
    if change == 2:
        assert calls[-1] is None


def test_failed_final_reseed_does_not_release_from_intermediate_agreement(monkeypatch):
    det = Detector()
    contradict(det)
    answers = iter([model(disagreement=0.0), model(sides=0, disagreement=None)])
    monkeypatch.setattr('resense.detector.estimate_track', lambda *args, **kw: next(answers))
    mock_calibration(det, monkeypatch, 2.0)
    det._fit_track(np.zeros((3, 3), dtype=np.float32))
    assert det.track.effective_axis_valid == 60


@pytest.mark.parametrize('change', [.5, 2.0])
def test_final_fresh_agreement_can_release_after_mount_change(monkeypatch, change):
    det = Detector()
    contradict(det)
    monkeypatch.setattr('resense.detector.estimate_track', lambda *args, **kw: model(disagreement=0.0))
    mock_calibration(det, monkeypatch, change)
    det._fit_track(np.zeros((3, 3), dtype=np.float32))
    assert det.track.effective_axis_valid == 180
    assert det._axis_contradiction_cap is None
