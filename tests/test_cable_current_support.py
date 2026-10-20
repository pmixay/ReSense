"""Current returns, not accumulation or ego-motion assumptions, confirm R3."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import find_clusters
from resense.config import DetectorConfig
from resense.tracking import Tracker


def blob(current="body", distance=80.0, copies=1):
    """Old returns resolve a body even when current returns do not."""
    z = np.linspace(-1.5, 1.1, 18)
    old = np.column_stack((np.full(z.size, distance), np.zeros(z.size), z))
    now = old.copy()
    if current == "flat":
        now[:, 2] = 0.0
    elif current == "sparse":
        now = now[:3]
    elif current == "outside":
        now[:, 1] = 0.2
    elif current == "none":
        now = now[:0]
    now = np.repeat(now, copies, axis=0)
    xyz = np.vstack((old, now)).astype(np.float32)
    cfg = replace(DetectorConfig().cluster, voxel=.01, eps=.3,
                  min_samples=2, min_points=3, gauge_min_points=3)
    return find_clusters(xyz, np.full(len(xyz), 30.), xyz[:, 1], xyz[:, 2] + 1.83,
                         np.abs(xyz[:, 1]) < .1, cfg,
                         frame_idx=np.r_[np.full(len(old), -1), np.arange(len(now))])


def stop(tracker):
    return any(t.zone == "gauge" for t in tracker.confirmed())


def test_accumulation_keeps_fast_confirmation_from_current_body():
    tracker = Tracker(DetectorConfig().tracking)
    for k in range(3):
        clusters = blob(distance=80. - k)
        assert len(clusters) == 1
        assert clusters[0].n_raw > len(clusters[0].points_idx)
        tracker.update(clusters, frame_dt=.1, odo_speed=10.)
        assert stop(tracker) == (k == 2)


@pytest.mark.parametrize("current", ["flat", "sparse", "outside", "none"])
@pytest.mark.parametrize("copies", [1, 4])
def test_history_and_duplicate_returns_cannot_complete_current_body(current, copies):
    tracker = Tracker(DetectorConfig().tracking)
    for k in range(3):
        tracker.update(blob(current, distance=80. - k, copies=copies), frame_dt=.1, odo_speed=10.)
        assert not stop(tracker)
        assert all(t.cable_hits == 0 for t in tracker.tracks)


def test_off_switch_keeps_generic_accumulation_confirmation():
    cfg = replace(DetectorConfig().tracking, cable_confirm_time_s=0.)
    tracker = Tracker(cfg)
    for k in range(5):
        tracker.update(blob(distance=80. - k), frame_dt=.1, odo_speed=10.)
        assert stop(tracker) == (k == 4)


def test_resolved_moving_body_is_not_vetoed_when_odometry_is_ready_first():
    # At 20 Hz the generic veto has enough travel/hits before the .3 s
    # cable run. A real body inside the gauge is still a collision target.
    tracker = Tracker(replace(DetectorConfig().tracking, near_escalate_voxels=0))
    for k in range(8):
        tracker.update(blob(distance=80.), frame_dt=.05, odo_speed=25.)
        if k >= 5:
            assert tracker._carried_along(tracker.tracks[0])
            assert stop(tracker)


def test_real_cable_does_not_override_measured_infrastructure_history():
    tracker = Tracker(DetectorConfig().tracking)
    first = blob()[0]
    tracker.update([replace(first, zone="warning", reason="retro")], frame_dt=.1)
    for _ in range(3):
        tracker.update(blob(), frame_dt=.1)
        assert not stop(tracker)
