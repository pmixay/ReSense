"""B4: an observed scan axis must contradict a wall masquerading as a rail bed.

Acceptance saved before the implementation. Channels are physical ray cones,
not an ordered sensor-specific elevation table. No recorded data required.
"""
import numpy as np
import pytest

from resense.calibration import MountCalibrator, orientation_candidates
from resense.config import DetectorConfig


def _cones(rotation=None):
    """Several channels, unequal ranges and shuffled non-monotone channel IDs."""
    az = np.linspace(-1.1, 1.1, 180)
    elev = np.array([-0.24, -0.11, -0.02, 0.04, 0.12, 0.22])
    a, e = np.meshgrid(az, elev)
    xyz = np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], -1).reshape(-1, 3)
    xyz *= np.linspace(4, 65, xyz.shape[0])[:, None]
    ring = np.repeat([81, 3, 104, 17, 62, 9], len(az)).astype(np.int32)
    if rotation is not None:
        xyz = xyz @ rotation.T
    return xyz.astype(np.float32), ring


@pytest.mark.parametrize('rotation', orientation_candidates())
def test_scan_axis_is_rotation_equivariant(rotation):
    from resense.calibration import scan_axis
    xyz, ring = _cones(rotation)
    axis = scan_axis(xyz, ring)
    assert axis is not None
    assert abs(float(axis @ rotation[:, 2])) > 0.999


@pytest.mark.parametrize('bad', ['missing', 'constant', 'random', 'short', 'negative', 'pencil'])
def test_invalid_channels_are_not_orientation_evidence(bad):
    from resense.calibration import scan_axis
    xyz, ring = _cones()
    if bad == 'missing':
        ring = None
    elif bad == 'constant':
        ring[:] = 0
    elif bad == 'random':
        ring = np.random.default_rng(2).integers(0, 6, len(ring))
    elif bad == 'short':
        ring = ring[:10]
    elif bad == 'negative':
        ring[:] = -1
    else:
        xyz[:, :2] = [10, 0]
    assert scan_axis(xyz, ring) is None


@pytest.mark.parametrize('sideways', [False, True])
def test_wall_cannot_confirm_a_mapping_contradicted_by_scan_axis(monkeypatch, sideways):
    """Even a passing bed/rail observation cannot override a perpendicular scan axis.

    No plausible alternative bed here: the contradiction must leave the mount
    unresolved, rather than adopt an arbitrary orientation on channel evidence alone.
    """
    import resense.calibration as mod
    rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]) if sideways else np.eye(3)
    xyz, ring = _cones(rotation)
    passing = mod.MountObservation(ok=True, rail_score=0.2, roll=0, pitch=0,
                                  yaw=0, height=2, lateral=0, forward_ratio=20)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cfg.calibration.frames = 3
    cfg.calibration.obs_spacing = 1
    cfg.calibration.search_orientations = False
    cal = MountCalibrator(cfg.calibration, cfg.track)
    for _ in range(4):
        cal.update(xyz, xyz, None, ring=ring)
    if sideways:
        assert not cal._config_passed
        assert cal.state.status == 'pending'
        assert cal.state.to_dict()['orientation_conflict'] is True
    else:
        assert cal._config_passed
        assert cal.state.status == 'identity'


def test_detector_hands_channels_to_calibration(tunnel, monkeypatch):
    from resense.detector import Detector
    from resense.frame import Frame
    frame, _, _ = tunnel
    ring = np.arange(frame.n, dtype=np.int32) % 32
    det = Detector()
    seen = []

    def update(*args, **kwargs):
        seen.append(kwargs.get('ring'))
        return False

    monkeypatch.setattr(det.calib, 'update', update)
    det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, ring=ring))
    assert len(seen) == 1 and seen[0] is ring


def test_a_missing_channel_frame_cannot_erase_an_observed_axis_conflict(monkeypatch):
    import resense.calibration as mod
    xyz, ring = _cones(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]))
    passing = mod.MountObservation(ok=True, rail_score=0.2, roll=0, pitch=0,
                                  yaw=0, height=2, lateral=0, forward_ratio=20)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cfg.calibration.search_orientations = False
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.update(xyz, xyz, None, ring=ring)
    cal.update(xyz, xyz, None, ring=None)
    assert not cal._config_passed
    assert cal.state.orientation_conflict


def test_scan_axis_does_not_reject_supported_combined_small_tilts(monkeypatch):
    import resense.calibration as mod
    rotation = mod.rot_x(np.radians(12)) @ mod.rot_y(np.radians(12))
    xyz, ring = _cones(rotation)
    passing = mod.MountObservation(ok=True, rail_score=0.2, roll=np.radians(12),
                                  pitch=np.radians(12), yaw=0, height=2,
                                  lateral=0, forward_ratio=20)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.update(xyz, xyz, None, ring=ring)
    assert cal._config_passed
    assert not cal.state.orientation_conflict


def test_repeated_channel_ids_on_only_two_cones_are_not_evidence():
    from resense.calibration import scan_axis
    xyz, ring = _cones()
    # Three hardware IDs, but only two resolved elevation planes.
    xyz = xyz[:540].astype(np.float64)
    azimuth = np.tile(np.linspace(-1.1, 1.1, 180), 3)
    elevation = np.repeat([-.2, -.2, .2], 180)
    xyz[:] = 20 * np.column_stack([np.cos(elevation) * np.cos(azimuth),
                                  np.cos(elevation) * np.sin(azimuth), np.sin(elevation)])
    assert scan_axis(xyz, ring[:540]) is None


@pytest.mark.parametrize('spacing', [1, 3, 10])
@pytest.mark.parametrize('periods', [1, 2, 5])
@pytest.mark.parametrize('time_cadence', [False, True])
def test_recovery_preserves_spaced_observations_and_final_cadence(monkeypatch, spacing, periods, time_cadence):
    import resense.calibration as mod
    passing = mod.MountObservation(ok=True, rail_score=.2, roll=np.radians(3), pitch=0,
                                  yaw=0, height=2, lateral=0, forward_ratio=20)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cfg.calibration.frames = 5
    cfg.calibration.obs_spacing = spacing
    cfg.calibration.time_cadence = time_cadence
    cfg.calibration.provisional_min_deg = 10
    control = MountCalibrator(cfg.calibration, cfg.track)
    recovered = MountCalibrator(cfg.calibration, cfg.track)
    xyz, ring = _cones()
    side, _ = _cones(np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]]))
    for frame in range(60):
        control.update(xyz, control.apply(xyz), None, periods=periods, ring=ring)
        recovered.update(side, recovered.apply(side), None, periods=periods, ring=ring)
        if frame >= 1:
            assert len(recovered._obs) == len(control._obs)
            assert recovered._since_obs == control._since_obs
            assert recovered.frozen == control.frozen
        if control.frozen:
            assert recovered.frozen
            break
    assert control.frozen


def test_recovered_sideways_mount_keeps_its_real_voting_observations(monkeypatch):
    """Do not add a two-frame provisional-tilt delay after the two orientation votes."""
    import resense.calibration as mod
    rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    xyz, ring = _cones(rotation)
    passing = mod.MountObservation(ok=True, rail_score=0.2, roll=np.radians(3),
                                  pitch=0, yaw=0, height=2, lateral=0, forward_ratio=20)
    monkeypatch.setattr(mod, 'observe_mount', lambda *a, **kw: passing)
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    assert not cal.update(xyz, xyz, None, ring=ring)
    assert cal.state.orientation_conflict
    assert not cal.state.orientation_confirmed
    assert cal.update(xyz, xyz, None, ring=ring)
    assert np.allclose(cal.R, rotation.T)
    assert cal.state.orientation_confirmed
    assert not cal.state.orientation_conflict
    assert len(cal._recent) == 2
    assert len(cal._obs) == 1 and cal._since_obs == 1
    for _ in range(3):
        cal.update(xyz, cal.apply(xyz), None, ring=ring)
    assert cal._provisional_done
    assert cal.state.status == 'provisional'


def test_no_channel_proof_keeps_the_original_eight_candidate_search(monkeypatch):
    import resense.calibration as mod
    xyz, _ = _cones()
    observed = []

    def observe(p, *a, **kw):
        observed.append(p)
        return mod.MountObservation(ok=False)

    monkeypatch.setattr(mod, 'observe_mount', observe)
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.update(xyz, xyz, None)
    assert len(observed) == 8  # configured frame plus the seven original alternatives
    assert not cal.state.orientation_conflict


def test_contradicted_orientation_has_no_clear_claim_or_silent_go(tunnel):
    from resense.health import HealthMonitor
    frame, _, track = tunnel
    cfg = DetectorConfig()
    health = HealthMonitor(cfg.health).update(
        frame.xyz, {}, track, cfg.gauge, 150, cfg.track.rails_min_score, None,
        {'status': 'pending', 'orientation_conflict': True, 'message': 'axis conflict'})
    assert health['decision_level'] == health['level'] == 'error'
    assert health['clear_distance'] == health['monitored_range'] == 0
    assert any('orientation unconfirmed' in m for m in health['messages'])
