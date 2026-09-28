"""Opt-in provenance-aware STOP onset evidence.

The candidate is deliberately narrower than a general persistence change: it only gates a track
that has not yet earned a gauge STOP (including reported advisories), and it does not alter
the existing one-miss STOP continuation.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

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


def test_weak_low_preserves_earned_stop_but_cannot_supply_reacquisition_evidence():
    tracker = Tracker(_cfg(low_confirm_hits=3, stop_keep_low_s=0.3))
    clean = _cluster(45.0, kind="low")
    weak = replace(clean, low_height_weak=True)
    for _ in range(3):
        track = _update(tracker, [clean])
    assert track.reported and track.stop_earned
    track_id = track.id

    for k in range(3):
        tracker.update([], frame_dt=0.1, low_height=[weak])
        assert track.reported and track.stop_earned and track.last is weak
        assert track.evidence_hist[-1] == "keep_low"
        # Even while earlier ordinary hits remain in the window, a current weak return
        # cannot start a new STOP. It is allowed here only because STOP was already earned.
        assert not tracker._fresh_stop_ok(track)
    assert track.evidence_hist == ["keep_low"] * 3

    tracker.update([], frame_dt=0.1, low_height=[weak])
    assert not track.reported and not track.stop_earned
    track = _update(tracker, [clean])
    assert track.id == track_id and not track.reported and not track.stop_earned
    assert track.evidence_hist == ["keep_low", "keep_low", "ordinary"]
    track = _update(tracker, [clean])
    assert track.id == track_id and track.reported and track.stop_earned


def test_advisory_demotion_rearms_fresh_gate_for_the_same_previous_stop():
    tracker = Tracker(_cfg(fresh_stop_evidence_min_hits=3, zone_window=3))
    for _ in range(3):
        track = _update(tracker, [_cluster(60.0)])
    assert track.stop_earned
    track_id = track.id
    for _ in range(3):
        track = _update(tracker, [_cluster(60.0, zone="warning")])
    assert track.reported and track.zone == "warning" and not track.stop_earned
    for _ in range(2):
        track = _update(tracker, [_cluster(60.0)])
        assert track.id == track_id and track.reported and track.zone == "warning"
        assert not track.stop_earned
    track = _update(tracker, [_cluster(60.0)])
    assert track.id == track_id and track.reported and track.stop_earned


@pytest.mark.parametrize("fresh_enabled", [False, True])
def test_near_escalation_on_advisory_clusters_records_existing_fresh_gate_recall_risk(fresh_enabled):
    """P3 currently vetoes near escalation when the current cluster itself is advisory.

    Preserve that opt-in behavior in this merge; changing it needs a separate candidate and
    paired recall/false-STOP evidence. Strict voxels alone do not bypass the fresh gate.
    """
    tracker = Tracker(_cfg(fresh_stop_evidence=fresh_enabled, start_clean=True,
                           near_escalate_voxels=10, near_escalate_hits=3, zone_window=3))
    advisory = replace(_cluster(20.0, zone="warning"), n_gauge=10,
                       reason="elevated", demoted=True)
    for _ in range(3):
        track = _update(tracker, [advisory])
    assert track.near_escalated and track.rule_zone == "gauge"
    assert (track.reported and track.zone == "gauge") is (not fresh_enabled)
    assert track.stop_earned is (not fresh_enabled)

    # Real ordinary evidence still permits onset without changing the track identity.
    for _ in range(2):
        track = _update(tracker, [_cluster(20.0)])
    assert track.reported and track.zone == "gauge" and track.stop_earned


def test_opinion_withholding_does_not_mark_a_stop_as_earned():
    class DoubtfulOpinion:
        def prob(self, features):
            return 0.0

    tracker = Tracker(_cfg())
    tracker.cfg.doubt_extra_hits = 2
    tracker.cfg.doubt_near = 0.0
    tracker.cfg.doubt_body_height = 0.0
    tracker.opinion = DoubtfulOpinion()
    tracker.record = True
    for _ in range(3):
        track = _update(tracker, [_cluster(60.0)])
    assert track.reported and track.withheld and track.zone == "warning"
    assert not track.stop_earned
    track = _update(tracker, [_cluster(60.0)])
    assert track.withheld and not track.stop_earned
    track = _update(tracker, [_cluster(60.0)])
    assert track.reported and not track.withheld and track.stop_earned


def test_defaults_and_experiment_yaml_are_independent():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    assert DetectorConfig().tracking.fresh_stop_evidence is False
    experiment = DetectorConfig.from_yaml(str(root / "configs/experimental_fresh_stop_evidence.yaml"))
    assert experiment.tracking.fresh_stop_evidence is True
    assert (experiment.tracking.fresh_stop_evidence_window,
            experiment.tracking.fresh_stop_evidence_min_hits) == (3, 2)
