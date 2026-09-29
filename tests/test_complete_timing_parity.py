"""Fail closed when a timing correction hides a contract or semantic change."""
import copy
import hashlib
import json

import pytest

from scripts.compare_complete_timing import STAGES, normalized_frame, percentile95, validate_identity


CONFIG = {"latency_affects_decision": False, "latency_budget_ms": 100.0, "latency_window": 50}


def rows(complete, count=12, window=50):
    result = []
    for index in range(count):
        timing = {key: 10.0 for key in STAGES}
        timing["total"] = 60.0
        if complete:
            timing.update(stages=60.0, health=200.0 + index * 10, result=4.0,
                          total=264.0 + index * 10)
        totals = [entry["timing_ms"]["total"] for entry in result]
        if not complete:
            totals.append(timing["total"])
        p95 = round(percentile95(totals[-max(1, window):]), 1)
        warning = len(totals[-max(1, window):]) >= 10 and p95 > 100
        health = {"level": "warn" if warning else "ok", "decision_level": "ok",
                  "latency_p95_ms": p95, "messages": [f"latency p95 {p95:.0f} ms over the 100 ms budget"] if warning else [],
                  "clear_distance": 80.0, "floor_shadow_frames": index}
        if complete:
            health.update(latency_basis="previous_complete_process", latency_sample_age_frames=1 if index else None)
        result.append({"frame": index, "frame_id": f"fixture_{index}", "stamp": index * 0.1,
                       "timing_ms": timing, "health": health, "detections": [{"distance": 20.0}],
                       "warnings": [], "mount": {"status": "ok"}, "clear_distance": 80.0})
    return result


def normalize(data, index, complete=True, **kwargs):
    return normalized_frame(data, index, kwargs.pop("config", CONFIG), complete=complete,
                            reset_indices=kwargs.pop("reset_indices", [0]), **kwargs)


@pytest.mark.parametrize("window", [0, 1, 9, 10, 50])
def test_registered_lagged_history_and_historical_stage_contract_match(window):
    before, after = rows(False, window=window), rows(True, window=window)
    cfg = {**CONFIG, "latency_window": window}
    for index in range(len(before)):
        assert normalize(before, index, False, config=cfg) == normalize(after, index, config=cfg)


@pytest.mark.parametrize("field,value", [
    ("latency_basis", "current_stages"), ("latency_sample_age_frames", None),
    ("latency_sample_age_frames", True), ("latency_sample_age_frames", 2),
    ("latency_p95_ms", 60.0), ("latency_p95_ms", float("nan")),
    ("latency_p95_ms", True), ("level", "error"),
    ("messages", ["latency p95 something"]),
])
def test_incorrect_health_contract_fails(field, value):
    data = rows(True)
    data[10]["health"][field] = value
    with pytest.raises(ValueError):
        normalize(data, 10)


@pytest.mark.parametrize("field", ["latency_basis", "latency_sample_age_frames"])
def test_missing_metadata_is_rejected(field):
    data = rows(True)
    data[0]["health"].pop(field)
    with pytest.raises(ValueError):
        normalize(data, 0)


def test_first_sample_cannot_be_fabricated_or_include_the_current_call():
    data = rows(True)
    data[0]["health"]["latency_p95_ms"] = 0.01
    with pytest.raises(ValueError, match="empty latency history"):
        normalize(data, 0)
    data = rows(True)
    data[1]["health"]["latency_p95_ms"] = data[1]["timing_ms"]["total"]
    with pytest.raises(ValueError, match="history"):
        normalize(data, 1)


def test_warning_at_result_ten_is_rejected_but_result_eleven_is_required():
    data = rows(True)
    h = data[9]["health"]
    h.update(level="warn", messages=[f"latency p95 {h['latency_p95_ms']:.0f} ms over the 100 ms budget"])
    with pytest.raises(ValueError, match="count"):
        normalize(data, 9)
    data = rows(True)
    data[10]["health"].update(level="ok", messages=[])
    with pytest.raises(ValueError, match="missing latency warning"):
        normalize(data, 10)


@pytest.mark.parametrize("field,value", [
    ("total", 60.0), ("stages", 59.0), ("health", 201.0), ("result", 5.0),
    ("track", -1), ("track", True), ("track", float("inf")),
])
def test_timing_omission_double_counting_and_invalid_numbers_fail(field, value):
    data = rows(True)
    data[0]["timing_ms"][field] = value
    with pytest.raises(ValueError):
        normalize(data, 0)


def test_rounding_bounds_are_specific_to_each_measured_interval():
    data = rows(True)
    data[1]["health"]["latency_p95_ms"] += 0.055
    normalize(data, 1)
    data[1]["health"]["latency_p95_ms"] += 0.001
    with pytest.raises(ValueError, match="history"):
        normalize(data, 1)
    data = rows(True)
    data[0]["timing_ms"]["total"] += 0.02
    normalize(data, 0)
    data[0]["timing_ms"]["total"] += 0.001
    with pytest.raises(ValueError, match="do not equal total"):
        normalize(data, 0)


@pytest.mark.parametrize("reset_indices", [[], [1], [0, 5]])
def test_unregistered_resets_cannot_waive_history(reset_indices):
    with pytest.raises(ValueError, match="no internal reset"):
        normalize(rows(True), 5, reset_indices=reset_indices)


@pytest.mark.parametrize("field", ["detections", "warnings", "mount", "clear_distance"])
def test_semantic_changes_are_preserved(field):
    before, after = rows(False), rows(True)
    after[10][field] = "changed"
    assert normalize(before, 10, False) != normalize(after, 10)


def test_nonlatency_health_fields_and_new_unknown_fields_are_preserved():
    before, after = rows(False), rows(True)
    for field in ("clear_distance", "floor_shadow_frames", "unknown_new_field"):
        changed = copy.deepcopy(after)
        changed[10]["health"][field] = 999
        assert normalize(before, 10, False) != normalize(changed, 10)


def test_legacy_capture_cannot_be_pretended_to_use_complete_timing():
    with pytest.raises(ValueError, match="timing fields"):
        normalize(rows(False), 0)


def test_baseline_cannot_masquerade_as_the_frozen_candidate(tmp_path):
    reference, candidate = tmp_path / "reference", tmp_path / "candidate"
    reference.mkdir()
    candidate.mkdir()
    gate = {"code": {"commit": "baseline", "uncommitted_detector_changes": []}}
    raw = json.dumps(gate).encode()
    (reference / "gate.json").write_bytes(raw)
    (candidate / "gate.json").write_bytes(raw)
    (candidate / "completion.json").write_text("{}")
    registration = {"baseline_gate": {"sha256": hashlib.sha256(raw).hexdigest(), "measured_commit": "baseline"}}
    with pytest.raises(ValueError, match="frozen clean commit"):
        validate_identity(reference, candidate, registration, {"commit": "candidate"}, tmp_path)
