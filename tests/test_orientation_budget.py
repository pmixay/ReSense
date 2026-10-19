"""S3 prospective acceptance: bound candidate transforms, retain admission counts."""
import numpy as np

from resense.calibration import MountCalibrator, MountObservation
from resense.config import DetectorConfig


def test_every_candidate_observation_is_bounded_on_a_large_cloud(monkeypatch):
    import resense.calibration as mod
    cfg = DetectorConfig()
    cfg.calibration.keep_up_axis = False
    cal = MountCalibrator(cfg.calibration, cfg.track)
    seen = []

    def observe(xyz, *args, **kwargs):
        seen.append(len(xyz))
        return MountObservation(ok=False)

    monkeypatch.setattr(mod, 'observe_mount', observe)
    xyz = np.random.default_rng(7).normal(size=(350003, 3)).astype(np.float32)
    cal._search_orientation(xyz)
    assert len(seen) == 23
    assert max(seen) <= 60000


def test_search_does_not_run_after_configured_mount_passes(monkeypatch):
    import resense.calibration as mod
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    passing = MountObservation(ok=True, rail_score=.2, roll=0, pitch=0, yaw=0, height=2, lateral=0)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    xyz = np.random.default_rng(7).normal(size=(8000, 3)).astype(np.float32)
    cal.update(xyz, xyz, None)
    assert cal._config_passed

    def forbidden(*args, **kwargs):
        raise AssertionError('orientation search after confirmation')

    monkeypatch.setattr(cal, '_search_orientation', forbidden)
    for _ in range(8):
        cal.update(xyz, xyz, None)


def test_a_sampled_winner_requires_full_cloud_rail_validation(monkeypatch):
    import resense.calibration as mod
    cfg = DetectorConfig()
    cfg.calibration.orientation_votes = 1
    cal = MountCalibrator(cfg.calibration, cfg.track)
    monkeypatch.setattr(cal, '_search_orientation', lambda *a: (1, MountObservation(ok=True)))
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: MountObservation(ok=False))
    xyz = np.zeros((0, 3), dtype=np.float32)
    cal.update(xyz, xyz, None)
    assert not cal._config_passed
    assert not cal.state.orientation_confirmed


def test_search_sample_weights_preserve_the_absolute_admission_bar(monkeypatch):
    import resense.calibration as mod
    cfg = DetectorConfig()
    fitted = []

    def fit(points, *args):
        fitted.append(len(points))
        return None

    monkeypatch.setattr(mod, '_fit_floor', fit)
    # A factor-two source sample: 200 forward / 600 near original returns.
    xyz = np.vstack([np.tile([20., 0., -1.], (100, 1)), np.tile([5., 0., -1.], (200, 1))])
    mod.observe_mount(xyz, cfg.track)
    assert fitted == []  # Positive control for the count guard, not a geometry claim.
    mod.observe_mount(xyz, cfg.track, point_weight=2)
    assert fitted == [300]
