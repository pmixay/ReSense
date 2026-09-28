import gzip
import json

import pytest

from scripts.quality_acceptance import alarm_changes, aligned, monitoring_cost, read_rows
from scripts.evaluate_monitoring_candidate import candidate_row
from scripts.score_clear_distance import decision


def row(i, *, warning=False, distance=100.0, health="ok"):
    return {"frame": i, "frame_id": f"bag_{i}", "stamp": float(i), "clear_distance": distance,
            "obstacle": False, "warning": warning, "health": {"level": health}}


def test_new_uncertainty_cannot_cancel_against_recovered_frames():
    before = [row(i, warning=i < 10) for i in range(100)]
    after = [row(i, warning=10 <= i < 20) for i in range(100)]
    result = monitoring_cost(before, after)
    assert result["reference_decisions"] == result["candidate_decisions"]
    assert result["newly_uncertain_percentage_points"] == 10
    assert not result["passed"]


def test_fault_also_costs_coverage_and_range_collapse_fails():
    before = [row(i) for i in range(100)]
    faults = [row(i, health="error" if i < 6 else "ok") for i in range(100)]
    assert not monitoring_cost(before, faults)["passed"]
    assert not monitoring_cost(before, [row(i, distance=94.9) for i in range(100)])["passed"]
    assert monitoring_cost(before, [row(i, distance=95.0) for i in range(100)])["passed"]


def test_equal_alarm_totals_cannot_hide_new_false_alarm_frames():
    before = [dict(row(i), obstacle=i == 0, detections=[{"id": 1}] if i == 0 else [])
              for i in range(2)]
    after = [dict(row(i), obstacle=i == 1, detections=[{"id": 1}] if i == 1 else [])
             for i in range(2)]
    result = alarm_changes(before, after)
    assert not result["no_new_alarm_frames"]
    assert [r["frame"] for r in result["new_alarm_frames"]] == [1]
    assert [r["frame"] for r in result["removed_alarm_frames"]] == [0]


def test_same_alarm_id_cannot_hide_replaced_detection_geometry():
    before = [dict(row(0), obstacle=True, detections=[{"id": 1, "center": [40, 0, 0]}])]
    after = [dict(row(0), obstacle=True, detections=[{"id": 1, "center": [80, 0, 0]}])]
    result = alarm_changes(before, after)
    assert result["no_new_alarm_frames"]
    assert not result["identical_alarm_outputs"]
    assert result["changed_detection_frames"][0]["candidate"] == after[0]["detections"]
    assert alarm_changes(before, before)["identical_alarm_outputs"]


@pytest.mark.parametrize("after", [[row(0)], [row(1), row(0)], [row(0), dict(row(1), stamp=2.0)]])
def test_misaligned_inputs_rejected(after):
    with pytest.raises(ValueError):
        aligned([row(0), row(1)], after)


def test_duplicate_or_ambiguous_capture_rejected(tmp_path):
    path = tmp_path / "bag.jsonl"
    path.write_text(json.dumps(row(0)) + "\n" + json.dumps(row(0)) + "\n")
    with pytest.raises(ValueError, match="duplicate"):
        read_rows(tmp_path, "bag")
    path.write_text(json.dumps(row(0)) + "\n")
    compressed = tmp_path / "bag.jsonl.gz"
    compressed.write_bytes(gzip.compress(path.read_bytes()))
    with pytest.raises(ValueError, match="exactly one"):
        read_rows(tmp_path, "bag")
    path.unlink()
    rows, provenance = read_rows(tmp_path, "bag")
    assert rows == [row(0)]
    assert provenance["frames"] == 1


def test_monitoring_observer_preserves_reference_and_stop_priority():
    original = row(0)
    original["health"].update(decision_level="ok", messages=[], clear_distance=100.0)
    candidate = candidate_row(original, 30.0)
    assert original["clear_distance"] == 100.0
    assert original["health"]["messages"] == []
    assert candidate["clear_distance"] == 30.0
    assert decision(candidate) == "CAUTION"
    assert decision(candidate_row(dict(original, obstacle=True), 30.0)) == "STOP"


def test_monitoring_observer_does_not_weaken_fault_or_increase_range():
    original = row(0, health="error", distance=0.0)
    original["health"].update(decision_level="error", messages=[], clear_distance=0.0)
    for distance in (None, 30.0):
        candidate = candidate_row(original, distance)
        assert candidate["clear_distance"] == 0.0
        assert decision(candidate) == "FAULT"
