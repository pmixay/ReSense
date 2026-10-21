"""Falcon clear-distance defect (P4 review of 20.10, docs/evidence/p4_review_h_mount_falcon_2026-10-20,
findings 1 and 2; lane docs/evidence/falcon_clear_distance_2026-10-21).

(a) ``health.clear_lost_model``: when the track model is on its prior (the rail pair was found in fewer than
    ``min_lock_rate`` of the last ``lock_window`` frames: the monitor's own "track model on its prior"
    warning) the bed under the corridor is not verified, and a person standing 3 m ahead is not a corridor
    candidate against a wandering bed. ``docs/ALGORITHM.md`` §4b: "a lost track model ... makes it equal to 0".
    The clear distance is then 0 (unknown), which is never beyond the nearest return in the corridor; the
    monitored range, the level, the messages and everything the decision reads are unchanged.
(b) ``health.clear_round_down``: the clear distance is rounded to 0.1 m to nearest while detections are
    rounded to 0.01 m, so it exceeded a STOP distance by up to 0.05 m. Bounded by a confirmed obstacle or a
    candidate it is now rounded down.

Both switches only lower ``clear_distance``. These tests fail on v1.2.0 (the keys do not exist and the
values are the old ones); the defaults of the switches are the same in the class and in both YAML copies.
"""
from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig, GaugeConfig, HealthConfig
from resense.health import HealthMonitor
from resense.track import TrackModel

ROOT = Path(__file__).resolve().parents[1]
KEYS = ("clear_lost_model", "clear_round_down")


def _cfg(lost=False, down=False) -> HealthConfig:
    cfg = HealthConfig()
    cfg.clear_lost_model = lost
    cfg.clear_round_down = down
    return cfg


def _track(rail_score: float) -> TrackModel:
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.77]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                      curvature=0.0, rail_score=rail_score)


def _scene(person_x=None) -> np.ndarray:
    """A tunnel-like frame of 30,000 returns out to 200 m and, optionally, a person-like cluster of 600
    returns 0.2-1.6 m above the mount plane (z = -1.77), |y| < 0.4 m, from ``person_x`` to +0.5 m."""
    rng = np.random.default_rng(3)
    x = rng.uniform(5, 200, 30000)
    xyz = np.stack([x, x * np.tan(np.radians(rng.uniform(-35, 35, x.size))), rng.uniform(-1.8, 2, x.size)], 1)
    xyz = np.concatenate([xyz, np.stack([np.linspace(5, 200, 500), np.zeros(500), np.zeros(500)], 1)])
    if person_x is not None:
        n = 600
        person = np.stack([person_x + rng.uniform(0, 0.5, n), rng.uniform(-0.4, 0.4, n),
                           -1.77 + rng.uniform(0.2, 1.6, n)], 1)
        xyz = np.concatenate([xyz, person])
    return xyz.astype(np.float32)


def _run(hm: HealthMonitor, xyz, track, frames, **kw):
    out = None
    for _ in range(frames):
        out = hm.update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, **kw)
    return out


def test_switch_defaults_are_equal_in_the_class_and_in_both_yaml_files():
    ref = {k: getattr(HealthConfig(), k) for k in KEYS}
    for path in ("configs/default.yaml", "ros2_ws/src/resense_ros/config/detector.yaml"):
        cfg = DetectorConfig.from_yaml(str(ROOT / path))
        assert {k: getattr(cfg.health, k) for k in KEYS} == ref, path
        for k in KEYS:
            assert f"{k}:" in (ROOT / path).read_text(), (path, k)


def test_a_person_at_3_m_with_a_lost_track_model_does_not_leave_a_clear_range_beyond_the_returns():
    """The Falcon frames 4373-4414: no rail pair for 20 frames, a person-like cluster at 3.0-3.5 m on the
    track, no confirmed obstacle, no candidate. v1.2.0 reports the monitored range (here 150 m, on the
    Falcon 21-40 m); the documented meaning of a lost model is 0."""
    xyz, track = _scene(person_x=3.0), _track(rail_score=-1.0)
    near = float(xyz[(np.abs(xyz[:, 1]) < 0.9) & (xyz[:, 2] > -1.77 + 0.2) & (xyz[:, 0] > 2.5)
                    & (xyz[:, 0] < 10)][:, 0].min())
    assert near == pytest.approx(3.0, abs=0.2)
    off = _run(HealthMonitor(_cfg()), xyz, track, 20)
    on_mon = HealthMonitor(_cfg(lost=True))
    on = _run(on_mon, xyz, track, 20)
    assert any("track model on its prior" in m for m in on["messages"])
    assert on["clear_distance"] == 0.0 and on["clear_distance"] <= near
    assert on_mon.last_clear_rule == "lost_model"
    # nothing else moves
    assert off["clear_distance"] > near
    assert {k: v for k, v in on.items() if k != "clear_distance"} == {k: v for k, v in off.items() if k != "clear_distance"}


def test_a_confirmed_obstacle_does_not_keep_a_clear_range_when_the_model_is_lost():
    """The same convention as a health error: a range that is not verified is 0, whatever else the frame has."""
    xyz, track = _scene(), _track(rail_score=-1.0)
    on = _run(HealthMonitor(_cfg(lost=True)), xyz, track, 20, obstacle_distance=40.0)
    assert on["clear_distance"] == 0.0


def test_a_locked_model_or_a_short_history_is_not_a_lost_model():
    xyz = _scene(person_x=3.0)
    for lost_track, frames in ((_track(rail_score=1.0), 20), (_track(rail_score=-1.0), 4)):
        hm = HealthMonitor(_cfg(lost=True))
        on = _run(hm, xyz, lost_track, frames)
        off = _run(HealthMonitor(_cfg()), xyz, lost_track, frames)
        assert on == off and hm.last_clear_rule == ""


def test_the_lost_model_rule_only_lowers_the_clear_distance():
    rng = np.random.default_rng(11)
    xyz = _scene(person_x=6.0)
    for k in range(40):
        lock = [1.0] * int(rng.integers(0, 21)) + [-1.0] * int(rng.integers(0, 21))
        obstacle = None if k % 3 == 0 else float(rng.uniform(5, 150))
        cand = None if k % 2 == 0 else float(rng.uniform(5, 150))
        pair = []
        for lost in (False, True):
            hm = HealthMonitor(_cfg(lost=lost))
            out = None
            for rs in lock:
                out = hm.update(xyz, {}, _track(rs), GaugeConfig(), 150.0, 0.05, None,
                                obstacle_distance=obstacle, candidate_distance=cand)
            pair.append(out)
        off, on = pair
        if off is None:
            continue
        assert on["clear_distance"] <= off["clear_distance"]
        assert {k2: v for k2, v in on.items() if k2 != "clear_distance"} == \
            {k2: v for k2, v in off.items() if k2 != "clear_distance"}


@pytest.mark.parametrize("stop, expected", [(48.06, 48.0), (47.97, 47.9), (115.16, 115.1), (124.09, 124.0), (9.99, 9.9)])
def test_clear_distance_is_rounded_down_below_a_stop_distance(stop, expected):
    """P4 finding 2: 48.0 against a STOP at 47.97, 115.2 against 115.16: nearest rounding of the clear
    distance, 0.01 m rounding of the detection."""
    xyz, track = _scene(), _track(rail_score=1.0)
    off = _run(HealthMonitor(_cfg()), xyz, track, 1, obstacle_distance=stop)
    hm = HealthMonitor(_cfg(down=True))
    on = _run(hm, xyz, track, 1, obstacle_distance=stop)
    assert off["clear_distance"] == round(stop, 1) and off["clear_distance"] > stop - 0.1 + 1e-9
    assert on["clear_distance"] == expected and on["clear_distance"] <= stop
    assert hm.last_clear_rule == "round_down_obstacle"


def test_clear_distance_never_exceeds_a_stop_or_a_candidate_distance_when_rounding_down():
    rng = np.random.default_rng(5)
    xyz, track = _scene(), _track(rail_score=1.0)
    for d in np.concatenate([rng.uniform(3, 149, 300), np.round(rng.uniform(3, 149, 50), 1)]):
        for kw in ({"obstacle_distance": float(d)}, {"candidate_distance": float(d)},
                   {"obstacle_distance": float(d), "candidate_distance": float(d) + 0.03}):
            on = _run(HealthMonitor(_cfg(down=True)), xyz, track, 1, **kw)
            bound = min(kw.values())
            assert on["clear_distance"] <= bound + 1e-9, (d, kw, on["clear_distance"])
            assert bound - on["clear_distance"] < 0.1 + 1e-9


def test_rounding_down_does_not_touch_an_unbounded_range_or_raise_anything():
    xyz, track = _scene(), _track(rail_score=1.0)
    off = _run(HealthMonitor(_cfg()), xyz, track, 1)
    hm = HealthMonitor(_cfg(down=True))
    on = _run(hm, xyz, track, 1)
    assert on == off and hm.last_clear_rule == ""
    for d in (20.04, 20.05, 33.33, 87.96, 20.0):
        a = _run(HealthMonitor(_cfg()), xyz, track, 1, obstacle_distance=d)
        b = _run(HealthMonitor(_cfg(down=True)), xyz, track, 1, obstacle_distance=d)
        assert b["clear_distance"] <= a["clear_distance"]
        assert {k: v for k, v in a.items() if k != "clear_distance"} == {k: v for k, v in b.items() if k != "clear_distance"}


def test_detector_with_the_switches_changes_no_decision_input_and_never_exceeds_a_stop():
    """End to end on a synthetic tunnel: a box that becomes a STOP. Detections, warnings, the decision
    inputs and the health level are those of the detector without the switches; the clear distance is never
    beyond the STOP distance and never beyond the old value."""
    from resense.detector import Detector
    from resense.frame import Frame
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame

    for dist in (17.43, 21.58, 26.91):
        frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(8),
                                             specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=dist)])
        res = {}
        for on in (False, True):
            cfg = DetectorConfig()
            cfg.health.clear_lost_model = on
            cfg.health.clear_round_down = on
            det = Detector(cfg)
            for k in range(8):
                r = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, ring=frame.ring, stamp=0.1 * k,
                                      meta=dict(frame.meta)))
            res[on] = r
        off, on = res[False], res[True]
        assert on.obstacle and off.obstacle
        assert (on.obstacle, on.warning, on.nearest_distance, on.health["level"], on.health["decision_level"]) == \
            (off.obstacle, off.warning, off.nearest_distance, off.health["level"], off.health["decision_level"])
        assert [(d.distance, d.zone) for d in on.detections] == [(d.distance, d.zone) for d in off.detections]
        assert on.clear_distance <= off.clear_distance
        assert on.clear_distance <= on.nearest_distance
