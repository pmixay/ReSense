"""``health.clear_lost_bed`` (amendment 1 of docs/evidence/falcon_clear_distance_2026-10-21/PROTOCOL.md).

``clear_lost_model`` (the rail lock lost) zeroed the clear distance also on a platform recording whose bed was right
(``doubleT_platform``: 23 frames, 6.7 % of them). The Falcon defect is a *bed* that left the calibrated mount plane. The
bed is lost when the track model's rail head differs from the mount plane (``z = -mount height``) by more than the H'
tolerance (``cluster.mount_cross_tol`` + ``mount_cross_grade`` * X) at some X = 5, 10, ... ``mount_cross_range`` m; the
clear distance is then 0 (ALGORITHM §4b: a lost track model makes it 0), whatever the rail lock. Only lowers clear.
"""
import numpy as np
import pytest

from resense.config import GaugeConfig, HealthConfig
from resense.health import HealthMonitor, bed_off_mount_plane
from resense.track import TrackModel


def _track(z0, slope=0.0, rail_score=1.0, rng=(4.0, 100.0)) -> TrackModel:
    return TrackModel(floor_coef=np.array([0.0, slope, z0]), floor_range=rng, center=0.0, yaw=0.0, curvature=0.0,
                      rail_score=rail_score, rail_offset=0.0)    # rail head = the fitted level


def test_the_bed_off_the_mount_plane_is_detected_with_the_h_prime_tolerance():
    plane = -1.77
    assert not bed_off_mount_plane(_track(-1.77), plane, 0.5, 0.05, 30.0)
    assert not bed_off_mount_plane(_track(-1.77 + 0.4), plane, 0.5, 0.05, 30.0)            # inside 0.5 + 5 % of X
    assert bed_off_mount_plane(_track(-1.77 + 0.9), plane, 0.5, 0.05, 30.0)                # 0.9 m at 5 m: 0.4 m over
    assert bed_off_mount_plane(_track(-1.77 + 2.0), plane, 0.5, 0.05, 30.0)                # Falcon frame 4396: +1.9 m
    assert not bed_off_mount_plane(_track(-1.77 + 0.9, slope=0.0), plane, 0.5, 0.05, 30.0 / 100.0)  # no sample X in range
    assert not bed_off_mount_plane(_track(-1.77 + 2.0), plane, 0.0, 0.05, 30.0)            # H' off: no tolerance, no rule
    # the climb that leaves the tolerance only far away (slope 0.1 m per m) is found at the far samples of the range
    assert bed_off_mount_plane(_track(-1.77, slope=0.12), plane, 0.5, 0.05, 30.0)
    assert not bed_off_mount_plane(_track(-1.77, slope=0.12), plane, 0.5, 0.05, 5.0)       # 0.6 m at 5 m: inside 0.75 m


def _xyz():
    rng = np.random.default_rng(3)
    x = rng.uniform(5, 200, 30000)
    xyz = np.stack([x, x * np.tan(np.radians(rng.uniform(-35, 35, x.size))), rng.uniform(-1.8, 2, x.size)], 1)
    return np.concatenate([xyz, np.stack([np.linspace(5, 200, 500), np.zeros(500), np.zeros(500)], 1)]).astype(np.float32)


def _cfg(bed: bool) -> HealthConfig:
    cfg = HealthConfig()
    cfg.clear_lost_bed = bed
    return cfg


def test_a_lost_bed_reports_no_clear_range_and_changes_nothing_else():
    xyz, track = _xyz(), _track(-1.77 + 2.0)          # a locked model whose bed sits 2 m above the plane
    off_m, on_m = HealthMonitor(_cfg(False)), HealthMonitor(_cfg(True))
    off = off_m.update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, bed_conflict=True)
    on = on_m.update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, bed_conflict=True)
    assert off["clear_distance"] == 150.0 and on["clear_distance"] == 0.0
    assert on_m.last_clear_rule == "lost_bed" and off_m.last_clear_rule == ""
    assert {k: v for k, v in on.items() if k != "clear_distance"} == {k: v for k, v in off.items() if k != "clear_distance"}
    # no conflict, or the switch off: the old value
    again = HealthMonitor(_cfg(True)).update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, bed_conflict=False)
    assert again == off


def test_a_confirmed_obstacle_does_not_keep_a_range_over_a_lost_bed():
    xyz, track = _xyz(), _track(-1.77 + 2.0)
    on = HealthMonitor(_cfg(True)).update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, obstacle_distance=40.0,
                                          bed_conflict=True)
    assert on["clear_distance"] == 0.0


def test_the_detector_passes_its_mount_plane_and_the_h_prime_tolerance_to_the_monitor(monkeypatch):
    """Wiring: with the switch on and a final mount calibration the detector evaluates the bed against its own calibrated
    mount plane with the H' tolerance and hands the result to the health monitor; with the switch off, or without a final
    calibration, the check is not evaluated. Nothing but clear_distance moves."""
    import resense.detector as detmod
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame

    calls = []

    def fake(track, plane, tol, grade, x_max, step=5.0):
        calls.append((round(plane, 3), tol, grade, x_max))
        return True

    monkeypatch.setattr(detmod, "bed_off_mount_plane", fake)
    xyz = _xyz()
    inten = np.full(len(xyz), 10.0, np.float32)

    def run(on, status):
        cfg = DetectorConfig()
        cfg.health.clear_lost_bed = on
        cfg.calibration.enabled = False
        det = Detector(cfg)
        det.calib.state.height, det.calib.state.status = 1.77, status    # the state tests/test_f1_false_alarms.py sets
        calls.clear()
        res = None
        for k in range(6):
            res = det.process(Frame(xyz=xyz, intensity=inten, ring=None, stamp=0.1 * k, meta={}))
        return res, list(calls), cfg

    off, calls_off, _ = run(False, "ok")
    on, calls_on, cfg = run(True, "ok")
    pend, calls_pend, _ = run(True, "pending")
    assert calls_off == [] and calls_pend == []                                  # not evaluated
    assert calls_on and calls_on[-1] == (-1.77, cfg.cluster.mount_cross_tol, cfg.cluster.mount_cross_grade,
                                         cfg.cluster.mount_cross_range)
    assert on.clear_distance == 0.0 and off.clear_distance > 0.0 and pend.clear_distance == off.clear_distance
    for other in (on, pend):
        assert (other.obstacle, other.warning, other.nearest_distance, other.health["level"],
                other.health["decision_level"]) == (off.obstacle, off.warning, off.nearest_distance,
                                                    off.health["level"], off.health["decision_level"])
        assert [(d.distance, d.zone) for d in other.detections] == [(d.distance, d.zone) for d in off.detections]
