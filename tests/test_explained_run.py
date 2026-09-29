"""Opt-in onset rule ``tracking.explained_run`` (after Tactical-Inventor/LCT-2026.NIIstovye): a track that
had a hit demoted with a reason may start a STOP only after a run of consecutive clean strict-gauge hits."""
from __future__ import annotations

import numpy as np

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.tracking import Tracker


def _cluster(x: float, *, zone: str = "gauge", reason: str = "") -> Cluster:
    c = np.array([x, 0.0, 1.0], dtype=float)
    return Cluster(
        points_idx=np.arange(3), n=10, n_raw=10, centroid=c, bbox_min=c - 0.2, bbox_max=c + 0.2,
        distance=x, lateral=0.0, height_min=0.5, height_max=1.5, intensity=10.0, n_expected=10.0,
        score=1.0, zone=zone, n_gauge=8, reason=reason,
    )


def _cfg(**overrides) -> TrackingConfig:
    values = dict(confirm_hits=3, confirm_time_s=0.0, doubt_extra_hits=0, near_escalate_voxels=0,
                  stop_keep_signature=False, stop_keep_thin=0, explained_run=3, zone_window=6,
                  zone_min_fraction=0.5)
    values.update(overrides)
    return TrackingConfig(**values)


def _update(tracker: Tracker, clusters):
    tracker.update(clusters, frame_dt=0.1, far_thin=[])
    return tracker.tracks[0] if tracker.tracks else None


def _is_stop(track) -> bool:
    return bool(track is not None and track.reported and track.zone == "gauge")


def test_off_by_default():
    assert TrackingConfig().explained_run == 0


def test_clean_history_starts_as_before():
    on, off = Tracker(_cfg()), Tracker(_cfg(explained_run=0))
    for _ in range(3):
        a, b = _update(on, [_cluster(90.0)]), _update(off, [_cluster(90.0)])
    assert _is_stop(a) == _is_stop(b) is True


def test_an_explained_history_needs_a_clean_run():
    on, off = Tracker(_cfg()), Tracker(_cfg(explained_run=0))
    seq = [_cluster(90.0, zone="warning", reason="column"), _cluster(90.0), _cluster(90.0)]
    for cl in seq:
        a, b = _update(on, [cl]), _update(off, [cl])
    assert _is_stop(b)                       # the zone vote alone starts the baseline STOP
    assert not _is_stop(a) and a.reported     # the candidate keeps it a visible advisory
    a = _update(on, [_cluster(90.0)])          # the third consecutive clean hit
    assert _is_stop(a)


def test_a_miss_breaks_the_run():
    t = Tracker(_cfg())
    for cl in (_cluster(90.0, zone="warning", reason="beyond_axis"), _cluster(90.0), _cluster(90.0)):
        tr = _update(t, [cl])
    tr = _update(t, [])
    assert tr.clean_run == 0
    for _ in range(2):
        tr = _update(t, [_cluster(90.0)])
    assert not _is_stop(tr)
    tr = _update(t, [_cluster(90.0)])
    assert _is_stop(tr)


def test_an_earned_stop_is_not_taken_down_by_a_later_demotion():
    t = Tracker(_cfg())
    for _ in range(3):
        tr = _update(t, [_cluster(90.0)])
    assert _is_stop(tr)
    tr = _update(t, [_cluster(90.0, reason="floating")])
    tr = _update(t, [_cluster(90.0)])
    assert _is_stop(tr)


def test_reason_filter():
    t = Tracker(_cfg(explained_reasons="column"))
    for cl in (_cluster(90.0, zone="warning", reason="floating"), _cluster(90.0), _cluster(90.0)):
        tr = _update(t, [cl])
    assert _is_stop(tr)                      # 'floating' is not in the explained set here
