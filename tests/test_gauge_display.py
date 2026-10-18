"""Gauge display preserves trusted geometry bounds without altering detector state."""

from copy import deepcopy

import numpy as np

from resense.track import TrackModel
from ros2_ws.src.resense_ros.resense_ros.gauge_display import GaugeDisplay


def track(**overrides):
    args = dict(
        floor_coef=np.array([0.0, 0.0, -1.6]),
        floor_range=(3.0, 60.0),
        center=0.0,
        yaw=0.0,
        curvature=0.0,
        axis_valid=150.0,
    )
    return TrackModel(**{**args, **overrides})


def test_box_cross_section_caps_growth_and_falling_support_immediately():
    display = GaugeDisplay()
    model = track()
    saved = deepcopy(model.to_dict())
    health = {"level": "ok", "monitored_range": 130.0, "freshness_valid": True}
    prior = 0.0
    for i in range(40):
        status = display.update(model, i * 0.1, health)
        assert status["solid_range_m"] <= min(
            model.axis_valid, health["monitored_range"]
        )
        if prior:
            assert status["drawn_range_m"] <= prior + 5.0
        prior = status["drawn_range_m"]
    edges = display.outline([[-1.05, 0.12], [1.05, 0.12], [1.05, 3.0], [-1.05, 3.0]])
    assert len(edges) == 6
    assert np.allclose(edges[1][:, 1] - edges[0][:, 1], 2.1)
    assert np.allclose(edges[2][:, 2] - edges[1][:, 2], 2.88)
    assert model.to_dict() == saved and health["freshness_valid"]
    model.axis_valid = 40.123456
    assert display.update(model, 4.1, health)["solid_range_m"] == model.axis_valid
    model.axis_valid = 150.0
    # A one-frame range spike cannot extend the displayed box.
    assert display.update(model, 4.2, health)["solid_range_m"] == 40.123456


def test_invalid_fit_and_pause_keep_grey_geometry_but_zero_trusted_range():
    display = GaugeDisplay()
    model = track()
    display.update(model, 1.0, {"level": "ok", "monitored_range": 100.0})
    before = display.center.copy()
    for i in range(3):
        state = display.invalidate("paused")
        assert state["solid_range_m"] == 0 and not state["valid"] and state["held"]
        assert np.array_equal(display.center, before)
    state = display.invalidate("paused")
    assert state["hold_expired"] and state["drawn_range_m"] == 0
    assert display.center is None
    display.reset()
    assert not display.outline([[-1.0, 0.0], [1.0, 0.0], [1.0, 3.0], [-1.0, 3.0]])


def test_smoothing_uses_travel_distance_when_available_and_reports_lag():
    slow, fast = GaugeDisplay(), GaugeDisplay()
    health = {"level": "ok", "monitored_range": 150.0}
    for display in (slow, fast):
        display.update(track(), 0.0, health, speed=0.0)
    slow_state = slow.update(track(center=0.1), 0.1, health, speed=0.0)
    fast_state = fast.update(track(center=0.1), 0.1, health, speed=20.0)
    assert 0 < slow.center[40] < fast.center[40] < 0.1
    assert slow_state["max_lateral_lag_m"] > fast_state["max_lateral_lag_m"]
    assert fast_state["smoothing"] == "distance_with_stationary_settling"
    assert fast.update(track(), 0.2, health)["smoothing"] == "time_fallback_no_odometry"


def test_hold_expires_on_wall_clock_even_without_more_input_frames():
    now = [0.]
    display = GaugeDisplay(clock=lambda: now[0])
    display.update(track(), 0., {"level": "ok", "monitored_range": 100.})
    now[0] = .5
    state = display.invalidate("watchdog")
    assert state["hold_expired"] and state["drawn_range_m"] == 0
    assert display.center is None


def test_far_display_lag_reduces_range_and_reports_the_coverage_cost():
    display = GaugeDisplay()
    health = {"level": "ok", "monitored_range": 150.}
    for i in range(40):
        display.update(track(), i*.1, health)
    state = display.update(track(curvature=.001), 4., health)
    assert state["reason"] == "range_limited_by_display_lag"
    assert state["drawn_range_m"] < state["support_range_m"]
    assert state["max_lateral_lag_m"] <= .25


def test_vertical_fit_change_cannot_leave_a_floating_trusted_box():
    display = GaugeDisplay()
    health = {"level": "ok", "monitored_range": 150.}
    for i in range(40):
        display.update(track(), i*.1, health)
    state = display.update(track(floor_coef=np.array([0., .01, -1.6])), 4., health)
    assert state["reason"] == "range_limited_by_display_lag"
    assert state["drawn_range_m"] < 40.
    assert state["max_spatial_lag_m"] <= .25
    assert state["max_vertical_lag_m"] > 0
