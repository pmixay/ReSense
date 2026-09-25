"""Mount auto-calibration (resense/calibration.py) and production guards (resense/health.py).

The synthetic ray-cast tunnel (rails, bed, benches) is re-mounted by known rotations; the
calibrator must find the orientation from the data, recover roll and pitch, and the detector
must then report the obstacle at the right distance as if the sensor had been mounted
correctly. The guards must turn a blinded / empty / NaN-poisoned input into a health error
with nothing verified, without raising.
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.calibration import MountCalibrator, orientation_candidates, rot_x, rot_y, rot_z
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame


def _remount(frame: Frame, M: np.ndarray) -> Frame:
    """The same scene seen by a sensor whose configured-vehicle frame is rotated by M^T
    (p_seen = M @ p_true): the calibrator should come back with R ~ M^T."""
    return Frame(xyz=(frame.xyz @ M.T).astype(np.float32), intensity=frame.intensity, ring=frame.ring,
                 stamp=frame.stamp, frame_id=frame.frame_id, meta=dict(frame.meta))


def _angle_deg(R: np.ndarray) -> float:
    return float(np.degrees(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0))))


def test_orientation_candidates_are_the_24_proper_rotations():
    c = orientation_candidates()
    assert len(c) == 24
    assert np.allclose(c[0], np.eye(3))
    for R in c:
        assert np.allclose(R @ R.T, np.eye(3)) and abs(np.linalg.det(R) - 1.0) < 1e-9
    assert len({tuple(R.ravel()) for R in c}) == 24


def test_default_search_keeps_the_spin_axis_vertical():
    """8 of the 24: upright or inverted, forward along any horizontal axis. The sideways ones let
    a flat tunnel wall pass for the bed (real square-tunnel frames, EXPERIMENTS.md section 6)."""
    c = orientation_candidates(keep_up_axis=True)
    assert len(c) == 8 and np.allclose(c[0], np.eye(3))
    assert all(abs(R[2, 2]) == 1.0 for R in c)
    for M in (rot_x(np.pi), rot_z(np.pi / 2), rot_z(-np.pi / 2), rot_z(np.pi)):
        assert any(np.allclose(R, M.T, atol=1e-9) for R in c)


def test_sideways_mount_only_with_the_full_search(tunnel):
    """A spinning LiDAR on its side is not searched by default (the mapping is kept and the
    calibration reports it); with ``keep_up_axis: false`` the 24-candidate search finds it."""
    frame, _, _ = tunnel
    M = rot_x(np.pi / 2)
    cfg = DetectorConfig()
    cfg.calibration.max_frames = 12
    det = Detector(cfg)
    res = _run(det, _remount(frame, M), 14)
    assert res.mount["orientation"] == "configured" and res.mount["status"] == "fallback", res.mount
    cfg = DetectorConfig()
    cfg.calibration.keep_up_axis = False
    det = Detector(cfg)
    res = _run(det, _remount(frame, M), 12)
    assert _angle_deg(det.mount_rotation @ M) < 0.5, res.mount


def _short(cfg: DetectorConfig = None) -> DetectorConfig:
    """The final tilt after 5 consecutive observations: the synthetic scene is one static frame,
    so the 20 s spacing of the defaults (a moving train's cant averaging out) would only make
    the test long."""
    cfg = cfg or DetectorConfig()
    cfg.calibration.frames, cfg.calibration.obs_spacing = 5, 1
    return cfg


def _run(det: Detector, frame: Frame, n: int):
    res = None
    for k in range(n):
        f = Frame(xyz=frame.xyz, intensity=frame.intensity, ring=frame.ring, stamp=0.1 * k, meta=dict(frame.meta))
        res = det.process(f)
    return res


def test_calibrator_confirms_a_correct_mount(tunnel):
    frame, _, _ = tunnel
    det = Detector(_short())
    res = _run(det, frame, 8)
    assert res.mount["status"] == "identity", res.mount
    assert np.allclose(det.mount_rotation, np.eye(3))
    assert not res.obstacle


@pytest.mark.parametrize("roll,pitch", [(3.0, 0.0), (0.0, -2.5), (-2.0, 2.0)])
def test_calibrator_recovers_roll_and_pitch(tunnel, roll, pitch):
    frame, _, _ = tunnel
    M = rot_y(np.radians(pitch)) @ rot_x(np.radians(roll))
    det = Detector(_short())
    res = _run(det, _remount(frame, M), 8)
    assert res.mount["status"] == "ok", res.mount
    assert _angle_deg(det.mount_rotation @ M) < 0.5, (res.mount, det.mount_rotation @ M)
    assert not res.obstacle


def test_provisional_tilt_only_for_a_clearly_tilted_rig(tunnel):
    """Defaults: a 3.3 deg roll (the doubleT_obstacle rig) is corrected after 5 frames; a 1.5 deg
    one waits for the spaced 20-observation window (on a moving train the per-frame roll swings
    by +-1 deg with the cant), and is then applied."""
    frame, _, _ = tunnel
    det = Detector(DetectorConfig())
    M = rot_x(np.radians(3.3))
    res = _run(det, _remount(frame, M), 6)
    assert res.mount["status"] == "provisional", res.mount
    assert _angle_deg(det.mount_rotation @ M) < 0.5
    cfg = DetectorConfig()
    cfg.calibration.obs_spacing = 2
    cfg.calibration.frames = 6
    det = Detector(cfg)
    M = rot_x(np.radians(1.5))
    res = _run(det, _remount(frame, M), 6)
    assert res.mount["status"] == "pending" and np.allclose(det.mount_rotation, np.eye(3)), res.mount
    res = _run(det, _remount(frame, M), 8)
    assert res.mount["status"] == "ok", res.mount
    assert _angle_deg(det.mount_rotation @ M) < 0.5


def test_drift_monitor_warns_on_a_lasting_tilt_not_on_a_curve(tunnel):
    """After freezing, single checks with +-1.8 deg of roll (cant, lean) leave the median of the
    window small; a mount knocked 3 deg is reported once the window holds it."""
    frame, _, _ = tunnel
    cfg = _short()
    cfg.calibration.monitor_period = 1
    cfg.calibration.drift_window = 6
    cal = MountCalibrator(cfg.calibration, cfg.track)
    xyz = frame.xyz
    for _ in range(6):
        cal.update(xyz, xyz, None)
    assert cal.frozen and cal.state.status == "identity"
    for k in range(12):
        c = _remount(frame, rot_x(np.radians(1.8 if k % 2 else -1.8))).xyz
        cal.update(c, c, None)
    assert cal.state.drift_deg < 1.5 and "drift" not in cal.state.message, cal.state
    knocked = _remount(frame, rot_x(np.radians(3.0))).xyz
    for _ in range(6):
        cal.update(knocked, knocked, None)
    assert cal.state.drift_deg > 1.5 and cal.state.message.startswith("mount drift"), cal.state


@pytest.mark.parametrize("name,M", [
    ("upside down", rot_x(np.pi)),
    ("forward = +x (ROS convention)", rot_z(np.pi / 2)),
    ("mounted backwards", rot_z(np.pi)),
    ("forward = +x, rolled 2 deg", rot_x(np.radians(2.0)) @ rot_z(-np.pi / 2)),
])
@pytest.mark.synthetic
def test_calibrator_finds_the_orientation_and_the_detector_works(name, M):
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(3),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=40.0)])
    det = Detector(_short())
    res = _run(det, _remount(frame, M), 12)
    assert res.mount["orientation"] != "configured", res.mount
    assert _angle_deg(det.mount_rotation @ M) < 0.5, (name, res.mount)
    assert res.obstacle, (name, res.mount, res.health)
    assert 38.0 < res.nearest_distance < 42.0


def test_calibration_can_be_switched_off(tunnel):
    frame, _, _ = tunnel
    cfg = DetectorConfig()
    cfg.calibration.enabled = False
    det = Detector(cfg)
    res = _run(det, _remount(frame, rot_x(np.radians(3.0))), 6)
    assert res.mount["status"] == "disabled"
    assert np.allclose(det.mount_rotation, np.eye(3))


def test_calibrator_gives_up_without_rails():
    """A cloud with no rail pair anywhere (a featureless box): keep the configured mapping."""
    rng = np.random.default_rng(0)
    xyz = np.stack([rng.uniform(3, 80, 50000), rng.uniform(-2.5, 2.5, 50000), rng.uniform(-1.5, 3, 50000)], 1)
    cfg = DetectorConfig()
    cfg.calibration.max_frames = 4
    cal = MountCalibrator(cfg.calibration, cfg.track)
    for _ in range(5):
        cal.update(xyz.astype(np.float32), xyz.astype(np.float32), None)
    assert cal.state.status == "fallback" and np.allclose(cal.R, np.eye(3))


# ---------------------------------------------------------------------------
# 25.09 (P3, SCORECARD #13): 5 Hz input and a re-mounted rig
# ---------------------------------------------------------------------------

def _run_at(det: Detector, frame: Frame, n: int, dt: float):
    """``n`` frames ``dt`` apart; the result of the last and the sensor time of the first
    frame whose calibration is final (None: never)."""
    res, t_final = None, None
    for k in range(n):
        f = Frame(xyz=frame.xyz, intensity=frame.intensity, ring=frame.ring, stamp=dt * k, meta=dict(frame.meta))
        res = det.process(f)
        if t_final is None and res.mount["status"] in ("ok", "identity"):
            t_final = round(dt * k, 6)
    return res, t_final


def _cadence(time_cadence: bool) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.calibration.frames, cfg.calibration.obs_spacing = 4, 4       # 4 observations 0.4 s apart at 10 Hz
    cfg.calibration.time_cadence = time_cadence
    return cfg


def test_time_cadence_calibrates_5hz_in_the_same_sensor_time(tunnel):
    """Ray-cast tunnel, rig rolled 3.3 deg. The spacing of the final observations counted
    processed frames, so 5 Hz took twice the sensor time (the 20 x 10-frame window of the
    defaults never completed on the 25 s roundT_doubleT); with ``time_cadence`` it counts
    nominal periods from the stamps and 5 Hz is final when 10 Hz is, with the same tilt."""
    frame, _, _ = tunnel
    M = rot_x(np.radians(3.3))
    seen = _remount(frame, M)
    _, t10 = _run_at(Detector(_cadence(False)), seen, 14, 0.1)
    _, t10_on = _run_at(Detector(_cadence(True)), seen, 14, 0.1)
    _, t5_frames = _run_at(Detector(_cadence(False)), seen, 14, 0.2)
    det = Detector(_cadence(True))
    res, t5 = _run_at(det, seen, 8, 0.2)
    assert t10 == t10_on == pytest.approx(1.2)              # observations at 0, 0.4, 0.8, 1.2 s
    assert t5_frames == pytest.approx(2.4)                   # every 4th 5 Hz frame
    assert t5 == pytest.approx(1.2), res.mount
    assert res.mount["status"] == "ok" and _angle_deg(det.mount_rotation @ M) < 0.5, res.mount


def test_refine_replaces_a_provisional_tilt_taken_on_a_canted_stretch(tunnel):
    """The provisional tilt is the median of the first 5 consecutive frames; in roundT_doubleT
    those see one canted stretch of rail and measure roll -1.0 ... -2.2 deg (the spaced
    observations settle near 0), so a re-mounted rig ran 20 s with a 1.6-2 deg roll error and
    alarmed on a rail at 40-50 m. Ray-cast: rig rolled 3 deg, the first 5 frames see 5 deg. With
    ``refine_min_deg`` the spaced observations replace the provisional tilt once their median
    moves; without, the error stays until the final."""
    frame, _, _ = tunnel
    true, canted = rot_x(np.radians(3.0)), rot_x(np.radians(5.0))

    def run(refine: float) -> MountCalibrator:
        cfg = DetectorConfig()
        cfg.calibration.obs_spacing = 1
        cfg.calibration.refine_min_deg = refine
        cal = MountCalibrator(cfg.calibration, cfg.track)
        for k in range(14):
            xyz = _remount(frame, canted if k < 5 else true).xyz
            cal.update(xyz, cal.apply(xyz), None)
        return cal

    off, on = run(0.0), run(0.5)
    assert off.state.status == on.state.status == "provisional"      # the final needs 20 observations
    assert _angle_deg(off.R @ true) > 1.5, off.state
    assert _angle_deg(on.R @ true) < 0.5, on.state
    assert on.state.message.startswith("provisional tilt refined"), on.state.message


def test_a_final_within_keep_within_deg_keeps_the_provisional_tilt(tunnel):
    """doubleT_obstacle: the final (roll +3.02 / pitch -0.88) confirmed the provisional one
    (+3.18 / -0.81) within 0.16 deg, the correction changed anyway, the track model was
    re-seeded, and the object was missed on the next frame. With ``keep_within_deg`` such a
    final keeps the applied correction: no change is reported, nothing is re-seeded."""
    frame, _, _ = tunnel

    def run(keep: float):
        cfg = DetectorConfig()
        cfg.calibration.frames, cfg.calibration.obs_spacing = 10, 1
        cfg.calibration.keep_within_deg = keep
        cal = MountCalibrator(cfg.calibration, cfg.track)
        changed = []
        for k in range(10):
            xyz = _remount(frame, rot_x(np.radians(3.3 if k < 5 else 3.45))).xyz
            changed.append(cal.update(xyz, cal.apply(xyz), None))
        return cal, changed

    off, changed_off = run(0.0)
    on, changed_on = run(0.25)
    assert off.state.status == on.state.status == "ok"
    assert changed_off[4] and changed_on[4]                  # the provisional tilt, both
    assert changed_off[9] and not changed_on[9]              # the final: applied / kept
    assert abs(on.state.roll_deg - off.state.roll_deg) < 0.25


def test_robustness_flags_are_on_by_default():
    """Shipped 25.09 after the 10 Hz gate (identical but doubleT_obstacle 185 -> 186 labelled
    hits); the per-axis provisional gating was tried and is off (EXPERIMENTS.md section 1i)."""
    cfg = DetectorConfig()
    assert cfg.calibration.time_cadence and cfg.track.rates_per_period and cfg.track.walls_smoothing_per_period
    assert cfg.calibration.refine_min_deg == 0.5 and cfg.calibration.keep_within_deg == 0.25
    assert not cfg.calibration.provisional_per_axis


@pytest.mark.synthetic
def test_nearby_obstacle_still_stops_at_5hz_on_a_tilted_rig():
    """A 0.6 m box 30 m ahead, rig pitched 3 deg, 5 Hz stamps, the shipped defaults (time
    cadence, rates and yaw / curvature smoothing per period, refinement, keep-within): the
    provisional tilt comes after 5 frames, the tracker restarts, and the box is a STOP at the
    right distance within 0.6 s of sensor time after that, and stays one."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=30.0)])
    M = rot_y(np.radians(3.0))
    det = Detector(DetectorConfig())
    seen = _remount(frame, M)
    stops = []
    for k in range(12):
        res = det.process(Frame(xyz=seen.xyz, intensity=seen.intensity, stamp=0.2 * k, meta=dict(seen.meta)))
        stops.append(bool(res.obstacle))
    assert res.mount["status"] == "provisional" and _angle_deg(det.mount_rotation @ M) < 0.5, res.mount
    assert all(stops[8:]), stops                             # frame 4: provisional; 5-7: 3 hits = 0.6 s
    assert 28.0 < res.nearest_distance < 32.0, res.nearest_distance


# ---------------------------------------------------------------------------
# production guards
# ---------------------------------------------------------------------------

def test_health_on_a_clear_tunnel_reports_the_verified_range(tunnel):
    frame, _, _ = tunnel
    res = _run(Detector(DetectorConfig()), frame, 5)
    h = res.health
    assert h["level"] in ("ok", "warn")
    assert h["monitored_range"] > 100.0
    assert res.clear_distance == pytest.approx(h["monitored_range"], abs=0.2)
    d = res.to_dict()
    assert {"health", "mount", "clear_distance"} <= set(d)


def test_clear_distance_is_the_obstacle_distance(tunnel):
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(3),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=40.0)])
    res = _run(Detector(DetectorConfig()), frame, 6)
    assert res.obstacle
    assert res.clear_distance == pytest.approx(res.nearest_distance, abs=0.2)


def test_blinded_sensor_is_an_error_with_nothing_verified(tunnel):
    frame, _, _ = tunnel
    det = Detector(DetectorConfig())
    _run(det, frame, 3)
    few = Frame(xyz=frame.xyz[:500], intensity=frame.intensity[:500], stamp=0.5)
    res = det.process(few)
    assert res.health["level"] == "error"
    assert res.health["monitored_range"] == 0.0 and res.clear_distance == 0.0
    empty = Frame(xyz=np.zeros((0, 3), np.float32), intensity=np.zeros(0, np.float32), stamp=0.6)
    res = det.process(empty)
    assert res.health["level"] == "error" and not res.obstacle


def test_nan_points_are_dropped_not_propagated(tunnel):
    frame, _, _ = tunnel
    xyz = frame.xyz.copy()
    xyz[::50] = np.nan
    xyz[1::97, 2] = np.inf
    res = _run(Detector(DetectorConfig()), Frame(xyz=xyz, intensity=frame.intensity), 4)
    assert not res.obstacle
    assert np.isfinite(res.track.center) and np.isfinite(res.track.yaw)


def test_window_dirt_is_flagged(tunnel):
    frame, _, _ = tunnel
    det = Detector(DetectorConfig())
    f = Frame(xyz=frame.xyz, intensity=frame.intensity, meta={"n_raw": frame.n * 2, "n_near": frame.n})
    res = det.process(f)
    assert any("window" in m for m in res.health["messages"])
