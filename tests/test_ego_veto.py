"""Opt-in ego-motion consistency veto ``tracking.ego_veto_*`` (after TunnelGuard ``_carried_along``)."""
from __future__ import annotations

import numpy as np

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.tracking import Tracker


def _cluster(x: float) -> Cluster:
    c = np.array([x, 0.0, 1.0], dtype=float)
    return Cluster(points_idx=np.arange(3), n=10, n_raw=10, centroid=c, bbox_min=c - 0.2, bbox_max=c + 0.2,
                   distance=x, lateral=0.0, height_min=0.5, height_max=1.5, intensity=10.0, n_expected=10.0,
                   score=1.0, zone="gauge", n_gauge=8)


def _cfg(**overrides) -> TrackingConfig:
    values = dict(confirm_hits=6, confirm_time_s=0.0, doubt_extra_hits=0, near_escalate_voxels=0,
                  stop_keep_signature=False, stop_keep_thin=0, ego_veto_min_speed=4.0)
    values.update(overrides)
    return TrackingConfig(**values)


def _run(tracker: Tracker, distances, speed):
    track = None
    for d in distances:
        tracker.update([_cluster(d)], ego_shift=(speed or 0.0) * 0.1, frame_dt=0.1, far_thin=[], odo_speed=speed)
        track = tracker.tracks[0]
    return track


def _is_stop(track) -> bool:
    return bool(track is not None and track.reported and track.zone == "gauge")


def test_off_by_default():
    assert TrackingConfig().ego_veto_min_speed == 0.0


def test_a_static_object_approaches_at_the_train_speed_and_stops():
    v = 10.0
    track = _run(Tracker(_cfg()), [100.0 - v * 0.1 * k for k in range(8)], v)
    assert _is_stop(track)


def test_an_artefact_carried_with_the_moving_train_stays_advisory():
    track = _run(Tracker(_cfg()), [100.0] * 8, 10.0)
    assert track.reported and not _is_stop(track)
    base = _run(Tracker(_cfg(ego_veto_min_speed=0.0)), [100.0] * 8, 10.0)
    assert _is_stop(base)


def test_no_veto_while_the_train_stands_or_the_speed_is_unknown():
    assert _is_stop(_run(Tracker(_cfg()), [100.0] * 8, 0.0))
    assert _is_stop(_run(Tracker(_cfg()), [100.0] * 8, None))


def test_no_veto_near_the_train():
    assert _is_stop(_run(Tracker(_cfg()), [20.0] * 8, 10.0))


def test_an_implausible_speed_jump_restarts_the_odometry():
    t = Tracker(_cfg())
    _run(t, [100.0] * 4, 10.0)
    seg = t._odo_seg
    _run(t, [100.0], 25.0)
    assert t._odo_seg == seg + 1


def test_an_earned_stop_is_not_vetoed_later():
    t = Tracker(_cfg())
    v = 10.0
    track = _run(t, [100.0 - v * 0.1 * k for k in range(8)], v)
    assert _is_stop(track)
    track = _run(t, [92.0] * 6, v)           # the object now keeps its distance (it moves away)
    assert _is_stop(track)
