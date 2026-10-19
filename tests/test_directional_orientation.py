"""L16: forward sign alone is not a roll cue; resolved FOV is separately required."""
import numpy as np
import pytest

from resense.calibration import MountCalibrator, directional_axes, orientation_candidates
from resense.config import DetectorConfig


def _fov():
    az, el = np.meshgrid(np.linspace(-1.0, 1.0, 130), np.linspace(-.20, .10, 20))
    p = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], -1).reshape(-1, 3)
    return (p * np.linspace(4, 100, len(p))[:, None]).astype(np.float32)


@pytest.mark.parametrize('rotation', orientation_candidates())
def test_directional_axes_follow_all_proper_axis_rotations(rotation):
    forward, up = directional_axes(_fov() @ rotation.T)
    assert np.array_equal(forward, rotation[:, 0])
    assert abs(up @ rotation[:, 2]) == 1


def test_sign_concentration_alone_does_not_resolve_roll():
    rng = np.random.default_rng(4)
    p = np.column_stack([rng.uniform(10, 20, 3000), rng.uniform(-10, 10, (3000, 2))])
    forward, up = directional_axes(p)
    assert np.array_equal(forward, [1, 0, 0])
    assert up is None


@pytest.mark.parametrize('kind', ['balanced', 'pencil', 'one_sided', 'tiny', 'invalid'])
def test_unresolved_coverage_cannot_supply_an_up_axis(kind):
    p = _fov()
    if kind == 'balanced':
        p = np.concatenate([p, -p])
    elif kind == 'pencil':
        p[:, 1:] *= .001
    elif kind == 'one_sided':
        p[:, 1] = np.abs(p[:, 1])
    elif kind == 'tiny':
        p = p[:20]
    else:
        p[:] = np.nan
    assert directional_axes(p)[1] is None


def test_ring_free_coverage_rejects_a_wall_passing_as_floor(monkeypatch):
    import resense.calibration as mod
    p = _fov() @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]).T
    passing = mod.MountObservation(ok=True, rail_score=.2, roll=0, pitch=0, yaw=0, height=2, lateral=0)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cfg.calibration.search_orientations = False
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.update(p, p, None)
    assert not cal._config_passed
    assert cal.state.orientation_conflict


def test_no_up_evidence_does_not_expand_the_eight_orientation_family(monkeypatch):
    import resense.calibration as mod
    rng = np.random.default_rng(4)
    p = rng.uniform(-50, 50, (3000, 3)).astype(np.float32)
    observed = []

    def observe(p, *a, **kw):
        observed.append(p)
        return mod.MountObservation(ok=False)

    monkeypatch.setattr(mod, 'observe_mount', observe)
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.update(p, p, None)
    assert len(observed) == 8
    assert not cal.state.orientation_conflict
