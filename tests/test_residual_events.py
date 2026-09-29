"""Inventory counting and provenance regressions; no detector or external dataset needed."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.analyze_residual_events import (
    approach, capture_semantics, config_diff, inventory, markdown_table,
    same_cluster, snapshot, support_class, validate_join,
)

RESULTS = Path(__file__).resolve().parents[1] / "docs/evidence/results"


def row(frame, global_frame, ids):
    return {"frame": frame, "frame_id": f"new_data_{global_frame:04d}",
            "obstacle": bool(ids), "detections": [{"id": i} for i in ids]}


def test_overlap_gaps_and_chunk_local_id_resets():
    events, counts = inventory({
        "new_data_0.jsonl": [row(0, 0, [3, 4]), row(1, 1, [3]), row(2, 2, []), row(3, 3, [4])],
        "new_data_1.jsonl": [row(0, 4, [3])],
    })
    assert set(events) == {"new_data_0.jsonl:3", "new_data_0.jsonl:4", "new_data_1.jsonl:3"}
    assert (counts["events"], counts["stop_frames"], counts["track_stop_frames"], counts["episodes"]) == (3, 4, 5, 3)
    assert counts["episode_ranges"][-2:] == [
        {"piece": "new_data_0.jsonl", "global_frame_range": [3, 3]},
        {"piece": "new_data_1.jsonl", "global_frame_range": [4, 4]},
    ]


@pytest.mark.parametrize("rows", [
    [row(1, 0, [3])], [row(0, 0, [3, 3])],
    [{**row(0, 0, []), "obstacle": True}], [row(0, 0, []), row(1, 2, [3])],
])
def test_invalid_capture_fails_closed(rows):
    with pytest.raises(ValueError):
        inventory({"piece": rows})


def joined_example():
    cluster = {"distance": 103.201, "lateral": 0.4, "centroid": [104.001, 0.4, 0.5],
               "size": [2.011, 0.8, 1.6], "n_voxels": 10, "height_min": 0.153,
               "kind": "", "n_gauge": 6, "n_points_idx": 2}
    detection = {"id": 358, "distance": 103.2, "lateral": 0.4, "center": [104.0, 0.4, 0.5],
                 "size": [2.01, 0.8, 1.6], "n_points": 10, "height_min": 0.15, "kind": ""}
    output = {**row(899, 7944, []), "detections": [detection], "obstacle": True,
              "track": {"center": 0.1}, "stamp": 1000.1}
    source = {"cluster": cluster, "misses": 0, "alarm": True, "frame_id": output["frame_id"],
              "piece_frame": 899, "track": output["track"], "stamp": output["stamp"]}
    return output, detection, source


@pytest.mark.parametrize("mutation", ["onset", "model", "stamp", "geometry", "alarm", "output"])
def test_same_id_cannot_establish_source_join(mutation):
    output, detection, source = joined_example()
    base = deepcopy(output)
    validate_join(output, detection, base, source)
    assert same_cluster(detection, source)
    if mutation == "onset":
        source["frame_id"] = "new_data_7943"
    elif mutation == "model":
        source["track"] = {"center": 0.2}
    elif mutation == "stamp":
        source["stamp"] += 0.1
    elif mutation == "geometry":
        source["cluster"]["n_voxels"] += 1
    elif mutation == "alarm":
        source["alarm"] = False
    else:
        detection["distance"] += 1
    with pytest.raises(ValueError):
        validate_join(output, detection, base, source)


def test_stale_low_or_strict_cluster_is_missed_not_fresh():
    _, detection, source = joined_example()
    assert support_class(source) == "ordinary"
    source["cluster"]["n_gauge"] = 0
    assert support_class(source) == "off_gauge"
    source["cluster"]["kind"] = "low"
    assert support_class(source) == "low"
    source["misses"] = 1
    assert support_class(source) == "missed"
    assert not same_cluster(detection, source)
    with pytest.raises(ValueError, match="stale"):
        snapshot(Path("must_not_open.npz"), source)


def test_snapshot_uses_exact_mask_and_checks_count(tmp_path):
    _, _, source = joined_example()
    path = tmp_path / "points.npz"
    np.savez(path, xyz=np.array([[1., 2., 3.], [1., 2., 3.], [900., 900., 900.]]),
             target=[1, 1, 0], dy=[0.1, 0.1, 50], h=[0.2, 0.2, 50])
    result = snapshot(path, source)
    assert result["raw_target_points"] == 2 and result["distinct_xyz"] == 1
    assert result["xyz_extent"] == [0, 0, 0]
    assert not result["strict_mask_recomputed"]
    source["cluster"]["n_points_idx"] = 3
    with pytest.raises(ValueError, match="count mismatch"):
        snapshot(path, source)


def test_approach_excludes_misses_and_preserves_receding_sign():
    cfg = {"approach_hits": 5, "approach_min_speed": 1, "ego_speed_max": 25,
           "approach_max_residual": 0.5}
    history = [{"frame_id": str(i), "stamp": 1000 + i * 0.1, "misses": 0,
                "cluster": {"distance": 50 - i}} for i in range(5)]
    history.insert(2, {"frame_id": "stale", "stamp": 1000.15, "misses": 1,
                       "cluster": {"distance": 500}})
    fit = approach(history, cfg)
    assert fit["passes_numeric_rule"] and fit["speed_m_s"] == pytest.approx(10)
    assert "stale" not in fit["source_frames"]
    assert approach(history[:-1], cfg)["speed_m_s"] is None
    for r in history:
        r["cluster"]["distance"] *= -1
    fit = approach(history, cfg)
    assert fit["speed_m_s"] == pytest.approx(-10) and not fit["passes_numeric_rule"]
    for r in history:
        r["stamp"] = 0
    assert approach(history, cfg)["speed_m_s"] is None


def test_default_parity_ignores_only_latency_not_faults_or_geometry():
    a = {**row(0, 0, []), "timing_ms": {"total": 1},
         "health": {"level": "ok", "latency_p95_ms": 1, "rail_lock": 1, "messages": []}}
    b = deepcopy(a)
    b["timing_ms"]["total"] = 100
    b["health"].update(level="warning", latency_p95_ms=100, messages=["latency p95 100 ms"])
    assert capture_semantics(a) == capture_semantics(b)
    b["health"]["level"] = "error"
    assert capture_semantics(a) != capture_semantics(b)
    b["health"]["level"] = "ok"
    b["health"]["rail_lock"] = 0
    assert capture_semantics(a) != capture_semantics(b)


def test_config_differences_handle_top_level_scalars_and_missing_legacy_fields():
    assert config_diff({"voxel": 0.1, "tracking": {}},
                       {"voxel": 0.1, "tracking": {"fresh_stop_evidence": True}}) == {
        "tracking.fresh_stop_evidence": {"default": None, "candidate": True}}


@pytest.fixture(scope="module")
def report():
    path = RESULTS / "residual_events_2026-09-28.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_recorded_inventory_counts_are_recoverable_from_retained_rows(report):
    events = report["events"]
    frames, track_frames, support, onsets = set(), 0, Counter(), Counter()
    for event in events:
        piece = event["key"].split(":")[0]
        records = event["candidate_stop_records"]
        assert len(records) == event["candidate_stop_frames"]
        onsets[records[0]["source_support_class"]] += 1
        event_support = Counter(r["source_support_class"] for r in records)
        assert dict(event_support) == {k: v for k, v in event["support_counts"].items() if v}
        for record in records:
            frames.add((piece, record["frame_id"]))
            track_frames += 1
            support[record["source_support_class"]] += 1
            if record["source_misses"]:
                assert record["source_support"] is None and record["source_observed_ring_ids"] is None
                assert "snapshot_path" not in record
    assert (len(events), len(frames), track_frames) == (27, 117, 133)
    assert support == {"ordinary": 74, "low": 18, "missed": 32, "off_gauge": 9}
    assert onsets == {"ordinary": 18, "low": 9}
    assert report["candidate"]["episodes"] == len(report["candidate"]["episode_ranges"]) == 26
    assert report["base"] == report["captured_defaults"]


def test_recorded_changed_onset_and_reacquisition_are_not_relabelled(report):
    events = {e["key"]: e for e in report["events"]}
    delayed = events["new_data_5.jsonl:358"]
    assert delayed["first_onset_frame"] == "new_data_7944"
    assert delayed["removed_global_frames"] == [7943]
    assert all(s["frame_id"] != "new_data_7943" for s in delayed["mapped_fresh_snapshots"])
    body = events["new_data_6.jsonl:331"]
    assert body["candidate_global_frame_ranges"] == [[9263, 9268]]
    assert body["removed_global_frames"] == [9271, 9272, 9273, 9274]
    assert len(report["removed_base_event_keys"]) == 5
    assert len(report["stop_decision_changed_frames"]) == 13


def test_markdown_inventory_matches_machine_record(report):
    path = Path(__file__).resolve().parents[1] / "docs/RESIDUAL_EVENTS_2026-09-28.md"
    assert markdown_table(report) in path.read_text(encoding="utf-8")
