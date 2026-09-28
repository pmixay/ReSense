import copy
import json

import pytest

from scripts.compare_health_gate import compare, normalized, normalized_health, validate_setf


CONFIG = {"latency_affects_decision": False, "latency_budget_ms": 100.0, "latency_window": 50}


def health(**changes):
    base = {"level": "ok", "decision_level": "ok", "messages": [], "latency_p95_ms": 90.0,
            "blocked_sectors": 0, "clear_distance": 80.0}
    base.update(changes)
    return base


def test_latency_crossing_normalizes_only_derived_level():
    a = health(level="warn", messages=["latency p95 110 ms over the 100 ms budget"], latency_p95_ms=110.3)
    b = health(latency_p95_ms=92.1)
    assert normalized_health(a, CONFIG, 9) == normalized_health(b, CONFIG, 9)


def test_nonlatency_message_order_and_values_preserved():
    a = health(level="warn", decision_level="warn", messages=["view blocked", "rail lock lost"])
    b = copy.deepcopy(a)
    b["messages"].reverse()
    assert normalized_health(a, CONFIG, 9) != normalized_health(b, CONFIG, 9)


@pytest.mark.parametrize("changed", [
    {"level": "unknown"},
    {"decision_level": "unknown"},
    {"level": "error"},
    {"latency_p95_ms": float("nan")},
    {"latency_p95_ms": -1},
    {"latency_p95_ms": True},
    {"messages": ["latency p95 something unexpected"]},
    {"level": "warn", "messages": ["latency p95 110 ms over the 99 ms budget"], "latency_p95_ms": 110.0},
    {"level": "warn", "messages": ["latency p95 110 ms over the 100 ms budget"] * 2, "latency_p95_ms": 110.0},
    {"level": "warn", "messages": ["latency p95 110 ms over the 100 ms budget"], "latency_p95_ms": 120.0},
    {"latency_p95_ms": 101.0},
])
def test_unexplained_timing_or_levels_rejected(changed):
    with pytest.raises(ValueError):
        normalized_health(health(**changed), CONFIG, 9)


def test_rounding_at_threshold_preserves_both_possible_warning_states():
    a = health(level="warn", latency_p95_ms=100.0, messages=["latency p95 100 ms over the 100 ms budget"])
    b = health(latency_p95_ms=100.0)
    assert normalized_health(a, CONFIG, 9) == normalized_health(b, CONFIG, 9)
    with pytest.raises(ValueError, match="count"):
        normalized_health(a, CONFIG, 8)


@pytest.mark.parametrize("config", [{}, {**CONFIG, "latency_affects_decision": True}])
def test_decision_latency_enabled_or_unspecified_rejected(config):
    with pytest.raises(ValueError, match="explicit"):
        normalized_health(health(), config, 9)


@pytest.mark.parametrize("field", ["blocked_sectors", "clear_distance"])
def test_health_changes_cannot_hide_in_timing(field):
    a = health()
    b = health(**{field: a[field] + 1})
    assert normalized_health(a, CONFIG, 9) != normalized_health(b, CONFIG, 9)


def test_detection_position_change_is_not_ignored():
    a = {"health": health(), "timing_ms": {"total": 10}, "detections": [{"distance": 20.0}]}
    b = copy.deepcopy(a)
    b["timing_ms"]["total"] = 20
    assert normalized(a, CONFIG, 9) == normalized(b, CONFIG, 9)
    b["detections"][0]["distance"] = 20.01
    assert normalized(a, CONFIG, 9) != normalized(b, CONFIG, 9)


def test_baseline_compared_to_itself_fails_frozen_candidate_identity(tmp_path):
    import hashlib
    reference = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    reference.mkdir()
    candidate.mkdir()
    gate = {"code": {"commit": "baseline", "uncommitted_detector_changes": []}}
    raw = json.dumps(gate).encode()
    (reference / "gate.json").write_bytes(raw)
    (candidate / "gate.json").write_bytes(raw)
    (candidate / "completion.json").write_text('{}')
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps({"baseline_gate": {"sha256": hashlib.sha256(raw).hexdigest(), "measured_commit": "baseline"}}))
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({"commit": "candidate"}))
    with pytest.raises(ValueError, match="frozen clean commit"):
        compare(reference, candidate, protocol, freeze, tmp_path / "output")


def setf_fixture():
    files = [46, 68, 98, 140, 168, 172]
    kinds = ["person", "box1.0", "box0.5", "trolley", "cable"]
    return {"parameters": {"files": ",".join(map(str, files)), "kinds": ",".join(kinds), "frames": 110},
            "sequences": [{"kind": kind, "file0": f"new_data_{file}_0000.npy.zst",
                           "rows": [{"frame": f"new_data_{file}_{i:04d}"} for i in range(102)]}
                          for file in files for kind in kinds]}


@pytest.mark.parametrize("fault", ["missing_case", "duplicate_case", "empty", "skipped", "truncated", "reordered"])
def test_setf_requires_every_frozen_case_and_ordered_actual_row(fault):
    reference = setf_fixture()
    data = copy.deepcopy(reference)
    if fault == "missing_case":
        data["sequences"].pop()
    elif fault == "duplicate_case":
        data["sequences"][-1] = data["sequences"][0]
    elif fault == "empty":
        data["sequences"][0]["rows"] = []
    elif fault == "skipped":
        data["sequences"][0]["skipped"] = "missing timestamp"
    elif fault == "truncated":
        data["sequences"][0]["rows"].pop()
    else:
        data["sequences"][0]["rows"].reverse()
    with pytest.raises(ValueError, match="set F"):
        validate_setf(data, reference)


def test_setf_maximum_is_not_required_actual_length():
    data = setf_fixture()
    validate_setf(data)
    validate_setf(copy.deepcopy(data), data)
