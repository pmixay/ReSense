"""Unconfirmed sensor orientation must not report a clear path."""
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from resense.calibration import MountCalibrator, MountObservation
from resense.config import DetectorConfig
from resense.health import HealthMonitor
from resense.track import TrackModel


def scene_health(calibration, *, obstacle_distance=None, empty=False):
    cfg = DetectorConfig()
    angle = np.linspace(-29, 29, 30000)
    points = np.column_stack((np.full(30000, 100), 100 * np.tan(np.radians(angle)), np.zeros(30000))).astype(np.float32)
    if empty:
        points = points[:0]
    track = TrackModel(floor_coef=np.array([-1.1, 0, 0]), floor_range=(0, 150),
                       center=0, yaw=0, curvature=0, rail_score=1)
    return HealthMonitor(cfg.health).update(points, {}, track, cfg.gauge,
                                            150, cfg.track.rails_min_score, None, calibration,
                                            obstacle_distance=obstacle_distance)


def test_unconfirmed_orientation_caps_clear_and_warns_without_removing_obstacle():
    h = scene_health({"status": "pending", "orientation_confirmed": False}, obstacle_distance=40)
    assert h["decision_level"] == "warn"
    assert h["orientation_confirmed"] is False
    assert h["monitored_range"] == h["clear_distance"] == 0
    assert any("orientation unconfirmed" in message for message in h["messages"])
    from ros2_ws.src.resense_ros.resense_ros.decision_policy import evaluate_decision
    assert evaluate_decision(SimpleNamespace(obstacle=True, warning=False, health=h)).decision == "STOP"
    assert evaluate_decision(SimpleNamespace(obstacle=False, warning=False, health=h)).decision == "CAUTION"


def test_orientation_guard_preserves_fault_priority():
    h = scene_health({"status": "pending", "orientation_confirmed": False}, empty=True)
    assert h["level"] == h["decision_level"] == "error"
    assert h["clear_distance"] == 0


@pytest.mark.parametrize("status", ["pending", "provisional", "ok", "identity", "disabled"])
def test_confirmed_orientation_does_not_wait_for_final_tilt(status):
    h = scene_health({"status": status, "orientation_confirmed": True})
    assert h["decision_level"] == "ok"
    assert h["clear_distance"] == 100
    assert h["orientation_confirmed"] is True


def test_calibrator_reports_existing_confirmation_and_explicit_disabled_mode():
    cfg = DetectorConfig()
    cal = MountCalibrator(cfg.calibration, cfg.track)
    assert cal.state.to_dict()["orientation_confirmed"] is False
    observation = MountObservation(ok=True, rail_score=1, roll=0, pitch=0, yaw=0,
                                   height=1.1, lateral=0, forward_ratio=1)
    with patch("resense.calibration.observe_mount", return_value=observation):
        cal.update(np.zeros((0, 3)), np.zeros((0, 3)), None)
    assert cal.state.to_dict()["orientation_confirmed"] is True
    disabled = MountCalibrator(replace(cfg.calibration, enabled=False), cfg.track)
    assert disabled.state.to_dict()["orientation_confirmed"] is True


def test_adoption_confirms_orientation_without_waiting_for_tilt():
    cfg = DetectorConfig()
    cfg.calibration.orientation_votes = 1
    cal = MountCalibrator(cfg.calibration, cfg.track)
    with patch("resense.calibration.observe_mount", return_value=MountObservation(ok=False)), \
         patch.object(cal, "_search_orientation", return_value=(1, MountObservation(ok=True))):
        cal.update(np.zeros((0, 3)), np.zeros((0, 3)), None)
    assert cal.state.status == "pending"
    assert cal.state.to_dict()["orientation_confirmed"] is True


def test_channel_conflict_keeps_fault_and_obstacle_priority_with_readiness_guard():
    from ros2_ws.src.resense_ros.resense_ros.decision_policy import evaluate_decision
    h = scene_health({"status": "pending", "orientation_confirmed": False,
                      "orientation_conflict": True, "message": "channel axis conflict"},
                     obstacle_distance=40)
    assert h["decision_level"] == "error"
    assert h["orientation_confirmed"] is False
    assert h["monitored_range"] == h["clear_distance"] == 0
    assert evaluate_decision(SimpleNamespace(obstacle=True, warning=False, health=h)).decision == "STOP"
    assert evaluate_decision(SimpleNamespace(obstacle=False, warning=False, health=h)).decision == "FAULT"
