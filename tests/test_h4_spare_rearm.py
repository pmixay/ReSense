"""H4 case 44: imputed column provenance must not delay a corroborated pole's return.

Replay the retained *pre-tracker* measurements, not its expected tracker decisions.
Frames are zero-based; the object is absent on 9/10 and returns on 11.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig
from resense.tracking import Tracker


@pytest.fixture
def pole():
    root = Path(__file__).resolve().parents[1]
    witness = json.loads((root / "docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json").read_text())
    values = dict(witness[0]["frames"][0]["pre"][0])
    values["points_idx"] = np.arange(values["n_raw"])
    for key in ("centroid", "bbox_min", "bbox_max"):
        values[key] = np.array(values[key])
    return Cluster(**values)


def _tracker(**overrides):
    return Tracker(replace(DetectorConfig().tracking, **overrides))


def _step(tracker, cluster=None, **kwargs):
    tracker.update([] if cluster is None else [replace(cluster)], frame_dt=0.1, **kwargs)
    assert len(tracker.tracks) == 1
    return tracker.tracks[0]


def _stop(t):
    return t.reported and t.zone == "gauge"


@pytest.mark.parametrize("fresh", [False, True])
def test_case44_first_returning_frame11_is_stop(pole, fresh):
    tracker = _tracker(fresh_stop_evidence=fresh)
    stops = []
    for frame in range(20):
        t = _step(tracker, None if frame in (9, 10) else pole)
        assert t.id == 1
        if _stop(t):
            stops.append(frame)
        if frame == 0:
            assert t.last.reason == "column" and t.last.spared
            assert t.column_hist == [True] and not t.column_held
        if frame == 9:
            assert _stop(t) and t.misses == 1
        if frame == 10:
            assert not t.reported and not t.stop_earned and t.misses == 2
        if frame == 11:
            assert t.last.n_gauge == 72 and t.last.ring_count == 18
            assert t.last.reason == "" and t.last.spared
            assert t.confidence == pytest.approx(0.85)
            assert sum(t.zone_hist) == 9 and not t.column_held
            assert _stop(t), "H4 returning frame 11 must regain STOP on its clean physical hit"
            assert not t.fresh_blocked
    # Keep the original conservative onset and the published second-miss release.
    assert stops == list(range(5, 10)) + list(range(11, 20))


@pytest.mark.parametrize("reason", ["column", "overhead", "retro", "shell"])
def test_measured_infrastructure_still_requires_run_after_release(pole, reason):
    # Isolate explained_run from the separate two-column hold (tested below).
    tracker = _tracker(column_hold=0)
    measured = replace(pole, zone="warning", reason=reason, spared=False)
    for frame in range(12):
        cl = measured if frame == 0 else pole
        t = _step(tracker, None if frame in (9, 10) else cl)
        if frame == 8:
            assert _stop(t)
        if frame in (9, 10):
            # Misses reset the run, not the measured-hit history.
            assert t.explained_hist[0] and t.clean_run == 0
        if frame == 11:
            assert t.explained_hist[0] and t.clean_run == 1
            assert t.reported and t.fresh_blocked and not _stop(t)


def test_actual_column_plus_one_spare_keeps_column_hold_across_gap(pole):
    tracker = _tracker()
    column = replace(pole, zone="warning", reason="column", spared=False)
    ordinary = replace(pole, spared=False)
    for frame in range(12):
        cl = column if frame == 0 else pole if frame == 1 else ordinary
        t = _step(tracker, None if frame in (9, 10) else cl)
        if frame >= 1:
            assert t.column_held and not _stop(t)
        if frame in (9, 10):
            assert t.column_hist[:2] == [True, True]
            assert any(t.explained_hist)


def test_single_noisy_spare_keeps_advisory_release_guard(pole):
    tracker = _tracker()
    ordinary = replace(pole, spared=False)
    advisory = replace(ordinary, zone="warning", reason="beyond_axis")
    sequence = [ordinary, advisory, ordinary, advisory, advisory, ordinary, pole] + [ordinary] * 5
    stops = []
    for frame, cl in enumerate(sequence):
        t = _step(tracker, cl)
        if _stop(t):
            stops.append(frame)
        if 7 <= frame <= 10:
            assert t.reported and t.zone == "warning"
            if t.rule_zone == "gauge":
                assert t.fresh_blocked
    assert stops == [11]  # Five clean hits, not a spare followed by only three.


def test_new_ordinary_object_after_actual_column_needs_clean_run(pole):
    tracker = _tracker()
    t = _step(tracker, replace(pole, zone="warning", reason="column", spared=False))
    ordinary = replace(pole, spared=False)
    for clean_hits in range(1, 6):
        t = _step(tracker, ordinary)
        assert t.id == 1 and t.clean_run == clean_hits
        assert _stop(t) is (clean_hits == 5)


def test_previous_stop_still_rearms_fresh_onset_gate(pole):
    tracker = _tracker(fresh_stop_evidence=True, fresh_stop_evidence_min_hits=3, zone_window=3)
    for _ in range(9):
        t = _step(tracker, pole)
    assert _stop(t)
    _step(tracker)
    t = _step(tracker)
    assert not t.reported and not t.stop_earned
    advisory = replace(pole, spared=False, zone="warning", reason="beyond_axis")
    for _ in range(3):
        _step(tracker, advisory)
    ordinary = replace(pole, spared=False)
    _step(tracker, ordinary)
    t = _step(tracker, ordinary)
    assert t.id == 1 and t.reported and t.fresh_blocked and not _stop(t)
    t = _step(tracker, ordinary)
    assert _stop(t) and not t.fresh_blocked


def test_corroborated_spare_does_not_bypass_ego_veto(pole):
    tracker = _tracker()
    for _ in range(12):
        t = _step(tracker, pole, odo_speed=10.0)
    assert t.reported and t.fresh_blocked and not _stop(t)


def test_corroborated_spare_does_not_bypass_doubt(pole):
    class DoubtfulOpinion:
        def prob(self, features):
            return 0.0

    tracker = _tracker(doubt_extra_hits=2, doubt_body_height=0.0)
    tracker.opinion = DoubtfulOpinion()
    tracker.record = True
    for _ in range(6):
        t = _step(tracker, pole)
    assert t.reported and t.withheld and not _stop(t) and not t.stop_earned
    t = _step(tracker, pole)
    assert _stop(t)
