"""Opt-in provenance-aware STOP onset evidence.

The candidate is deliberately narrower than a general persistence change: it only gates a track
that has not yet earned a gauge STOP (including reported advisories), and it does not alter
the existing one-miss STOP continuation.
"""
from __future__ import annotations

import numpy as np

from resense.clustering import Cluster
from resense.config import DetectorConfig, TrackingConfig
from resense.tracking import Tracker


def _cluster(x: float, *, zone: str = "gauge", kind: str = "", thin: bool = False) -> Cluster:
    c = np.array([x, 0.0, 1.0], dtype=float)
    return Cluster(
        points_idx=np.arange(3), n=10, n_raw=10, centroid=c,
        bbox_min=c - 0.2, bbox_max=c + 0.2, distance=x, lateral=0.0,
        height_min=0.5, height_max=1.5, intensity=10.0, n_expected=10.0,
        score=1.0, zone=zone, n_gauge=8 if zone == "gauge" else 0,
        kind=kind, thin=thin,
    )


def _cfg(**overrides) -> TrackingConfig:
    values = dict(
        confirm_hits=3, confirm_time_s=0.0, doubt_extra_hits=0,
        near_escalate_voxels=0, stop_keep_signature=False, stop_keep_thin=0,
        fresh_stop_evidence=True, fresh_stop_evidence_window=3,
        fresh_stop_evidence_min_hits=2,
    )
    values.update(overrides)
    return TrackingConfig(**values)


def _update(tracker: Tracker, clusters, *, far_thin=None):
    tracker.update(clusters, frame_dt=0.1, far_thin=far_thin or [])
    return tracker.tracks[0] if tracker.tracks else None


def test_stale_gauge_vote_cannot_start_on_an_off_gauge_hit_but_late_clean_hit_can():
    candidate = Tracker(_cfg())
    baseline = Tracker(_cfg(fresh_stop_evidence=False))

    for _ in range(2):
        _update(candidate, [_cluster(80.0)])
        _update(baseline, [_cluster(80.0)])
    candidate_track = _update(candidate, [_cluster(80.0, zone="warning")])
    baseline_track = _update(baseline, [_cluster(80.0, zone="warning")])
    assert not candidate_track.reported
    assert baseline_track.reported

    # The late strict hit is accepted; the two strict entries in the bounded window are fresh
    # provenance, while the intervening advisory hit is not.
    candidate_track = _update(candidate, [_cluster(80.0)])
    assert candidate_track.reported and candidate_track.zone == "gauge"


def test_low_object_is_fresh_onset_evidence_and_occlusion_keeps_earned_stop():
    tracker = Tracker(_cfg(low_confirm_hits=3))
    for _ in range(2):
        track = _update(tracker, [_cluster(45.0)])
    track = _update(tracker, [_cluster(45.0, kind="low")])
    assert track.reported and track.last.kind == "low"

    # Continuation is intentionally independent of the onset provenance check.
    track = _update(tracker, [])
    assert track.reported and track.misses == 1
    track = _update(tracker, [_cluster(43.0)])
    assert track.reported and track.misses == 0


def test_reported_advisory_to_stop_transition_is_gated_and_keeps_advisory_visible():
    tracker = Tracker(_cfg(fresh_stop_evidence_min_hits=3, zone_window=3))
    for _ in range(3):
        track = _update(tracker, [_cluster(60.0, zone="warning")])
    assert track.reported and track.zone == "warning"

    # The old warning report must not bypass the onset check. Two strict hits make the zone vote
    # gauge, but are below this candidate's bounded provenance requirement.
    for _ in range(2):
        track = _update(tracker, [_cluster(60.0)])
        assert track.reported and track.zone == "warning"

    track = _update(tracker, [_cluster(60.0)])
    assert track.reported and track.zone == "gauge"


def test_static_far_history_does_not_count_for_a_current_ordinary_onset():
    tracker = Tracker(_cfg(
        thin_far_min_distance=60.0, approach_hits=3,
        zone_window=3, zone_min_fraction=0.5,
        fresh_stop_evidence_min_hits=3,
    ))
    for _ in range(3):
        track = _update(tracker, [], far_thin=[_cluster(90.0, thin=True)])
    assert track.reported and track.zone == "warning"

    # With two current ordinary hits the rule zone is gauge, but the bounded history is
    # [far_thin, ordinary, ordinary]. Static far evidence is not eligible without an approach,
    # so this must remain advisory. A third ordinary hit supplies the required fresh provenance.
    for _ in range(2):
        track = _update(tracker, [_cluster(90.0)])
        assert track.reported and track.zone == "warning"
    track = _update(tracker, [_cluster(90.0)])
    assert track.reported and track.zone == "gauge"


def test_approaching_far_thin_and_ordinary_onsets_have_separate_provenance():
    far_cfg = _cfg(thin_far_min_distance=60.0, approach_hits=3)
    approaching = Tracker(far_cfg)
    static = Tracker(far_cfg)
    for k in range(3):
        _update(approaching, [], far_thin=[_cluster(90.0 - 2.0 * k, thin=True)])
        _update(static, [], far_thin=[_cluster(90.0, thin=True)])
    assert approaching.tracks[0].reported and approaching.tracks[0].zone == "gauge"
    assert not (static.tracks[0].reported and static.tracks[0].zone == "gauge")
    assert static.tracks[0].reported and static.tracks[0].zone == "warning"

    ordinary = Tracker(_cfg())
    for _ in range(3):
        track = _update(ordinary, [_cluster(90.0)])
    assert track.reported and track.zone == "gauge"


def test_thin_continuation_cannot_confirm_an_unreported_track():
    tracker = Tracker(_cfg(stop_keep_thin=2))
    _update(tracker, [_cluster(70.0)])
    for _ in range(3):
        # A mode-2 keep-thin candidate can match an unreported track, but it is not fresh onset
        # evidence and must not turn the accumulated hit count into a STOP.
        tracker.update([], frame_dt=0.1, thin=[_cluster(70.0, thin=True)])
    assert not any(t.reported and t.zone == "gauge" for t in tracker.tracks)


def test_defaults_and_experiment_yaml_are_independent():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert DetectorConfig().tracking.fresh_stop_evidence is False
    experiment = DetectorConfig.from_yaml(str(root / "configs/experimental_fresh_stop_evidence.yaml"))
    assert experiment.tracking.fresh_stop_evidence is True
    assert (experiment.tracking.fresh_stop_evidence_window,
            experiment.tracking.fresh_stop_evidence_min_hits) == (3, 2)
