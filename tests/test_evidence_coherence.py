"""Measured rejection diagnostics for the temporal-coherence hypothesis.

The abandoned candidate compared ``Cluster.lateral +/- size[1] / 2`` and the fitted height
interval between adjacent hits.  These tests keep the measurement reproducible, but deliberately do
not turn that comparison into a tracking rule: the fields are model-relative whole-cluster
descriptors, and the saved trace has no object-identity labels for a matched return.

The ride and positive-stress paths are optional local inputs.  The small tracker tests below remain
useful when those captures are unavailable.
"""
from __future__ import annotations

import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.track import TrackModel
from resense.tracking import Tracker
from scripts.analyze_residual_events import inventory, read_rows, support_class, validate_join


MEASUREMENT = Path("D:/Datasets/ReSense/cross_ring_2026-09-28_measurement")
POSITIVE_STRESS = Path("C:/Users/alikh/AppData/Local/Temp/opencode/fresh-stop-positive-stress")


def _cluster(x: float, *, lateral: float = 0.0, width: float = 0.8,
             height: tuple[float, float] = (0.4, 1.4), thin: bool = False) -> Cluster:
    center = np.array([x, lateral, 1.0], dtype=float)
    half = np.array([0.2, width / 2.0, 0.1])
    return Cluster(
        points_idx=np.arange(3), n=10, n_raw=10, centroid=center,
        bbox_min=center - half, bbox_max=center + half, distance=x,
        lateral=lateral, height_min=height[0], height_max=height[1],
        intensity=10.0, n_expected=10.0, score=1.0, zone="gauge",
        n_gauge=8, thin=thin,
    )


def _tracker() -> Tracker:
    return Tracker(TrackingConfig(
        confirm_hits=3, confirm_time_s=0.0, doubt_extra_hits=0,
        near_escalate_voxels=0, stop_keep_signature=False, stop_keep_thin=0,
        fresh_stop_evidence=True,
    ))


def _update(tracker: Tracker, clusters):
    tracker.update(clusters, frame_dt=0.1)
    return tracker.tracks[0] if tracker.tracks else None


@lru_cache(maxsize=1)
def _trace_data():
    trace_path = MEASUREMENT / "false_target_trace" / "trace.json"
    if not trace_path.exists():
        pytest.skip(f"measurement not available: {trace_path}")
    return json.loads(trace_path.read_text(encoding="utf-8"))


def _retained_keys():
    keys = set()
    for path in sorted((MEASUREMENT / "fresh_stop_v1").glob("new_data_*.jsonl")):
        piece = f"{path.stem}.jsonl:"
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["obstacle"]:
                keys.update(piece + str(detection["id"]) for detection in row["detections"])
    return keys


def _interval_breaks(event):
    breaks = []
    matched = [row for row in event["timeline"] if row["misses"] == 0]
    for previous, current in zip(matched, matched[1:]):
        old = previous["cluster"]
        new = current["cluster"]
        if old["thin"] or new["thin"] or old["zone"] != "gauge":
            continue
        old_interval = (old["lateral"] - old["size"][1] / 2,
                        old["lateral"] + old["size"][1] / 2)
        new_interval = (new["lateral"] - new["size"][1] / 2,
                        new["lateral"] + new["size"][1] / 2)
        lateral_gap = max(0.0, new_interval[0] - old_interval[1],
                          old_interval[0] - new_interval[1])
        height_gap = max(0.0, new["height_min"] - old["height_max"],
                         old["height_min"] - new["height_max"])
        if lateral_gap > 0.25 or height_gap > 0.25:
            breaks.append((current["frame_id"], lateral_gap, height_gap))
    return breaks


def test_rejected_candidate_has_no_tracking_flag_or_default():
    assert not hasattr(TrackingConfig(), "evidence_coherence")


@pytest.mark.realdata(str(MEASUREMENT))
def test_measured_remaining_inventory_is_133_track_frames():
    trace = _trace_data()
    retained = _retained_keys()
    rows = []
    for path in sorted((MEASUREMENT / "fresh_stop_v1").glob("new_data_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["obstacle"]:
                rows.extend(row["detections"])
    assert len(retained) == 27
    assert len(rows) == 133
    assert sum(1 for path in sorted((MEASUREMENT / "fresh_stop_v1").glob("new_data_*.jsonl"))
               for line in path.read_text(encoding="utf-8").splitlines()
               if json.loads(line)["obstacle"]) == 117
    assert {event["key"] for event in trace["events"]} - retained == {
        "new_data_1.jsonl:295", "new_data_2.jsonl:586", "new_data_4.jsonl:210",
        "new_data_5.jsonl:146", "new_data_6.jsonl:250",
    }


@pytest.mark.realdata(str(MEASUREMENT))
def test_interval_rule_is_not_a_single_false_history_separator():
    trace = _trace_data()
    events = {event["key"]: event for event in trace["events"]}
    breaks = {key: _interval_breaks(events[key]) for key in _retained_keys()}
    breaks = {key: value for key, value in breaks.items() if value}
    assert sum(map(len, breaks.values())) == 9
    assert len(breaks) == 6
    assert "new_data_1.jsonl:293" in breaks
    # Several retained breaks are ordinary-to-ordinary and another is low-to-low; the
    # proposed interval does not identify the mixed low-to-ordinary mechanism specifically.
    assert "new_data_0.jsonl:3" in breaks
    assert "new_data_4.jsonl:58" in breaks


@pytest.mark.realdata(str(MEASUREMENT))
def test_293_fields_and_reference_change_are_not_identity_evidence():
    trace = _trace_data()
    event = next(event for event in trace["events"] if event["key"] == "new_data_1.jsonl:293")
    rows = {row["frame_id"]: row for row in event["timeline"]}
    low = rows["new_data_2671"]
    ordinary = rows["new_data_2673"]
    old = low["cluster"]
    new = ordinary["cluster"]

    old_interval = (old["lateral"] - old["size"][1] / 2,
                    old["lateral"] + old["size"][1] / 2)
    new_interval = (new["lateral"] - new["size"][1] / 2,
                    new["lateral"] + new["size"][1] / 2)
    assert max(0.0, new_interval[0] - old_interval[1]) == pytest.approx(0.6563437, abs=1e-5)
    # The raw saved bbox gives the report's .56 m gap, while whole-target rail dy gives a
    # third measurement.  They are not interchangeable local footprints.
    assert new["bbox_min"][1] - old["bbox_max"][1] == pytest.approx(0.56, abs=1e-6)
    assert low["support"]["dy_max"] < ordinary["support"]["dy_min"]
    assert ordinary["support"]["dy_min"] - low["support"]["dy_max"] == pytest.approx(0.6346, abs=2e-3)

    # The fitted reference changes during the missing-return interval: one side becomes available,
    # the rail offset moves, and trusted axis range expands.  A model-relative jump is not proof of
    # a new physical object.
    reference = rows["new_data_2672"]["track"]
    assert reference["center"] - low["track"]["center"] == pytest.approx(-0.101, abs=1e-6)
    assert reference["rail_offset"] - low["track"]["rail_offset"] == pytest.approx(0.020, abs=1e-6)
    assert (low["track"]["axis_valid"], reference["axis_valid"]) == (115.0, 143.0)
    assert (low["track"]["axis_sides"], reference["axis_sides"]) == (1, 2)


@pytest.mark.realdata(str(MEASUREMENT))
def test_association_residuals_do_not_prove_wrong_association():
    trace = _trace_data()
    retained = _retained_keys()
    ratios = []
    for event in trace["events"]:
        if event["key"] not in retained:
            continue
        for row in event["timeline"]:
            association = row.get("association")
            if association:
                assert association["residual_yz"] <= association["base_gate"] + 1e-9
                ratios.append((association["residual_yz"] / association["base_gate"],
                               event["key"], row["frame_id"]))
    assert sum(ratio >= 0.5 for ratio, _, _ in ratios) == 2
    ratio = next(ratio for ratio, key, frame in ratios
                 if key == "new_data_1.jsonl:293" and frame == "new_data_2673")
    assert ratio == pytest.approx(0.7189, abs=2e-3)


def test_earned_stop_survives_occlusion_and_reacquisition():
    tracker = _tracker()
    for x in (60.0, 58.0, 56.0):
        track = _update(tracker, [_cluster(x)])
    assert track.reported
    track = _update(tracker, [])
    assert track.reported and track.misses == 1
    track = _update(tracker, [_cluster(54.0, lateral=0.9, width=0.3)])
    assert track.reported and track.misses == 0


def test_late_arrival_can_earn_a_new_stop_without_prior_evidence():
    tracker = _tracker()
    assert _update(tracker, []) is None
    assert _update(tracker, []) is None
    _update(tracker, [_cluster(80.0, lateral=0.8, width=0.4)])
    _update(tracker, [_cluster(78.0, lateral=0.82, width=0.35)])
    track = _update(tracker, [_cluster(76.0, lateral=0.8, width=0.3)])
    assert track.reported and track.zone == "gauge"


@pytest.mark.realdata(str(POSITIVE_STRESS))
def test_sparse_edge_positive_rows_are_unchanged_by_fresh_onset_replay():
    base_path = POSITIVE_STRESS / "setF_edge_base.json"
    fresh_path = POSITIVE_STRESS / "setF_edge_fresh.json"
    assert base_path.exists() and fresh_path.exists(), "marked positive stress cache is incomplete"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    fresh = json.loads(fresh_path.read_text(encoding="utf-8"))
    base_rows = [row for sequence in base["sequences"] for row in sequence["rows"]]
    fresh_rows = [row for sequence in fresh["sequences"] for row in sequence["rows"]]
    assert len(base_rows) == len(fresh_rows) == 357
    assert base_rows == fresh_rows
    assert base["summary"]["per_kind"]["person"]["detected"] == 2
    assert base["summary"]["per_kind"]["person"]["sustained_m"] == [86.6, 98.4]


def _gaps(old, new):
    """The rejected calculation, deliberately confined to research tests."""
    return (
        max(0.0, abs(new.lateral - old.lateral) - (new.size[1] + old.size[1]) / 2),
        max(0.0, new.height_min - old.height_max, old.height_min - new.height_max),
    )


class _RejectedTracker(Tracker):
    """Test-only intervention: reproduce the abandoned ordinary-hit evidence reset.

    _note is called after t.last is overwritten, so retain the preceding matched cluster separately.
    The production association, vote, opinion and continuation implementations are inherited.
    """

    def __init__(self, cfg):
        super().__init__(cfg)
        self.previous = {}

    def _note(self, t, cl, far_thin, zw, source="ordinary"):
        previous = self.previous.get(t.id)
        if (source == "ordinary" and cl.zone == "gauge" and previous is not None
                and previous.zone == "gauge" and not previous.thin and not cl.thin
                and max(_gaps(previous, cl)) > 0.25 + 1e-9):
            t.evidence_hist = []
        self.previous[t.id] = cl
        super()._note(t, cl, far_thin, zw, source)


@pytest.mark.parametrize("case", ["partial_person", "sparse_edge", "axis", "height_reference"])
def test_known_same_body_or_same_points_are_delayed_by_rejected_rule(case):
    """Only the visible subset/reference changes: identity is controlled, not inferred from gaps."""
    if case == "partial_person":
        # One 1.7 m person, lower then upper visible patches, including one pre-onset occlusion.
        first = _cluster(80, lateral=0.0, width=0.4, height=(0.45, 0.65))
        next_hit = _cluster(80, lateral=0.5, width=0.4, height=(1.15, 1.35))
    elif case == "sparse_edge":
        # Sparse visible patches on opposite strips of one 0.48 m-tall edge body.
        first = _cluster(80, lateral=0.7, width=0.2, height=(1.30, 1.40))
        next_hit = _cluster(80, lateral=1.25, width=0.2, height=(1.68, 1.78))
    else:
        # A controlled same-body fixture: a reference shift can change the reported lateral interval.
        first = _cluster(80, lateral=-0.3, width=0.4, height=(0.8, 0.95))
        next_hit = _cluster(80, lateral=0.5 if case == "axis" else -0.3,
                            width=0.4, height=(1.3, 1.45) if case == "height_reference"
                            else (0.8, 0.95))
        # Hold sensor-space support fixed; only its fitted-reference descriptors change.
        next_hit.centroid = first.centroid.copy()
        next_hit.bbox_min = first.bbox_min.copy()
        next_hit.bbox_max = first.bbox_max.copy()
    assert max(_gaps(first, next_hit)) > 0.25
    fresh = _tracker()
    rejected = _RejectedTracker(fresh.cfg)
    for tracker in (fresh, rejected):
        _update(tracker, [first])
        _update(tracker, [first])
        if case == "partial_person":
            _update(tracker, [])
        _update(tracker, [next_hit])
        assert len(tracker.tracks) == 1 and tracker.tracks[0].hits == 3
    assert fresh.tracks[0].reported and fresh.tracks[0].zone == "gauge"
    assert not rejected.tracks[0].reported
    # A brief late visibility opportunity is lost; only another compatible return restores onset.
    _update(rejected, [])
    assert not rejected.tracks[0].reported
    _update(rejected, [next_hit])
    assert rejected.tracks[0].reported


def test_low_to_ordinary_can_be_two_visible_parts_of_one_positive_body():
    low = _cluster(40, height=(0.03, 0.07))
    low.kind = "low"
    ordinary = _cluster(40, lateral=0.8, width=0.4, height=(0.4, 0.55))
    # A body reaching from .03 to .55 m can present its bottom or upper face. Same-object truth
    # is specified by the fixture; production descriptors alone cannot recover that truth.
    fresh = _tracker()
    rejected = _RejectedTracker(fresh.cfg)
    for tracker in (fresh, rejected):
        _update(tracker, [low])
        _update(tracker, [low])
        _update(tracker, [ordinary])
    assert fresh.tracks[0].reported
    assert not rejected.tracks[0].reported


def test_known_wrong_association_with_overlapping_projections_evades_rule():
    # Two physically distinct targets at different X but equal Y/Z. The second appears inside
    # the existing gate. Removing X from the rule makes their projection gap exactly zero.
    first = _cluster(80, lateral=0.0, width=0.4, height=(0.5, 0.8))
    second = _cluster(82, lateral=0.0, width=0.4, height=(0.5, 0.8))
    assert _gaps(first, second) == (0.0, 0.0)
    tracker = _RejectedTracker(_tracker().cfg)
    for cl in (first, first, second):
        _update(tracker, [cl])
    assert len(tracker.tracks) == 1
    assert tracker.tracks[0].reported and tracker.tracks[0].hits == 3


def _transition(previous, current):
    old, new = previous["cluster"], current["cluster"]
    gap = max(0.0, abs(new["lateral"] - old["lateral"])
              - (new["size"][1] + old["size"][1]) / 2)
    height_gap = max(0.0, new["height_min"] - old["height_max"],
                     old["height_min"] - new["height_max"])
    x = np.array([new["centroid"][0]])
    old_model, new_model = TrackModel(**previous["track"]), TrackModel(**current["track"])
    return {
        "previous_frame": previous["frame_id"], "frame": current["frame_id"],
        "kind": [old["kind"] or "ordinary", new["kind"] or "ordinary"],
        "zone": [old["zone"], new["zone"]], "lateral_gap_m": gap,
        "height_gap_m": height_gap,
        "raw_bbox_y_gap_m": max(0.0, new["bbox_min"][1] - old["bbox_max"][1],
                               old["bbox_min"][1] - new["bbox_max"][1]),
        "centroid_delta_y_m": new["centroid"][1] - old["centroid"][1],
        "lateral_delta_m": new["lateral"] - old["lateral"],
        "axis_delta_at_current_x_m": float((new_model.center_y(x) - old_model.center_y(x))[0]),
        "rail_delta_at_current_x_m": float((new_model.rail_z(x) - old_model.rail_z(x))[0]),
        "comparison_break": (not old["thin"] and not new["thin"] and old["zone"] == "gauge"
                             and max(gap, height_gap) > 0.25 + 1e-9),
        "reset_proxy": (not old["thin"] and not new["thin"]
                        and old["zone"] == new["zone"] == "gauge"
                        and max(gap, height_gap) > 0.25 + 1e-9),
        "association": current.get("association"),
    }


def diagnostic(measurement):
    """Validate all 133 source/output joins and retain all matched history transitions.

    A reset proxy is conditional on ordinary input routing; it is not a reconstructed tracker
    decision. In particular the trace lacks weak/far/keep source flags and candidate opinion state.
    """
    paths = [measurement / "false_target_trace/trace.json"]
    trace = json.loads(paths[0].read_text(encoding="utf-8"))
    pieces, base = {}, {}
    for path in sorted((measurement / "fresh_stop_v1").glob("new_data_*.jsonl")):
        paths.extend([path, measurement / "base" / path.name])
        pieces[path.name] = read_rows(path)
        base[path.name] = read_rows(paths[-1])
    events, counts = inventory(pieces)
    assert counts["frames"] == trace["frames"] == 11271
    assert not trace["detection_mismatch_frames"]
    source = {event["key"]: event for event in trace["events"]}
    result, classes = [], Counter()
    for key, outputs in events.items():
        timeline = source[key]["timeline"]
        records = {r["frame_id"]: r for r in timeline}
        piece = key.split(":")[0]
        stops = []
        for row, detection in outputs:
            record = records[row["frame_id"]]
            validate_join(row, detection, base[piece][row["frame"]], record)
            cls = support_class(record)
            classes[cls] += 1
            stops.append({"frame": row["frame_id"], "support": cls,
                          "source_cluster_zone": record["cluster"]["zone"],
                          "source_hits": record["hits"], "source_misses": record["misses"]})
        matched = [row for row in timeline if row["misses"] == 0]
        transitions = [_transition(a, b) for a, b in zip(matched, matched[1:])]
        onset = outputs[0][0]["frame_id"]
        result.append({"key": key, "onset": onset, "stop_rows": stops,
                       "matched_source_rows": len(matched), "transitions": transitions})
    counts.pop("episode_ranges")
    flat = [t for event in result for t in event["transitions"]]
    return {
        "status": "rejected_whole_cluster_interval_rule_no_candidate_replay",
        "sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "counts": counts, "source_support_classes": dict(classes),
        "matched_transitions": len(flat),
        "comparison_breaks": sum(t["comparison_break"] for t in flat),
        "reset_proxies": sum(t["reset_proxy"] for t in flat),
        "kind_switches": sum(t["kind"][0] != t["kind"][1] for t in flat),
        "events": result,
    }


@pytest.mark.realdata(str(MEASUREMENT))
def test_all_saved_stop_rows_validate_against_base_and_source():
    _trace_data()  # local capture availability check
    report = diagnostic(MEASUREMENT)
    assert report["counts"] == dict(frames=11271, events=27, stop_frames=117,
                                    track_stop_frames=133, episodes=26)
    assert report["source_support_classes"] == dict(ordinary=74, low=18, missed=32, off_gauge=9)
    assert report["comparison_breaks"] == 9
    assert report["reset_proxies"] == 6


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, default=MEASUREMENT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = diagnostic(args.measurement)
    if args.out:
        if not args.out.parent.is_dir():
            parser.error("output parent must already exist")
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in ("events", "sha256")},
                     indent=2))
    for event in report["events"]:
        for transition in event["transitions"]:
            if transition["comparison_break"]:
                print(event["key"], "onset", event["onset"], json.dumps(transition))
