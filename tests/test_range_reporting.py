"""C2 candidate is conservative, sensor-qualified, and preserves selected decisions."""
from copy import deepcopy

import pytest

from scripts.range_reporting import POLICY, candidate_ranges, small_target_limit
from resense.sensor import expected_points


def row(**kwargs):
    return {"frame": 0, "obstacle": False, "warning": True,
            "warnings": [{"reason": "", "distance": 40.06, "size": [.5, .5, 1.0]}],
            "health": {"level": "ok", "decision_level": "ok", "monitored_range": 150.0,
                       "clear_distance": 120.0}, "clear_distance": 120.0, **kwargs}


@pytest.mark.parametrize("reason", ["", "column", "beyond_axis", "beyond_height_ref", "doubt", "future_reason"])
def test_every_active_v1_advisory_caps_without_mutating_input_or_decision(reason):
    source = row(warnings=[{"distance": 40.06, "reason": reason}])
    before = deepcopy(source)
    after = candidate_ranges(source, sensor_model="pandar128")
    assert after["clear_distance"] == after["health"]["clear_distance"] == 40.0
    assert after["detector_clear_distance"] == 120.0
    assert after["warnings"] == source["warnings"]
    assert POLICY.decision(source) == POLICY.decision(after) == "CAUTION"
    assert source == before


def test_v2_suppressed_advisory_does_not_cap_health_only_caution():
    source = row(warnings=[{"distance": 20.0, "reason": "column"}],
                 health={"level": "warn", "decision_level": "warn", "monitored_range": 120.0})
    after = candidate_ranges(source, "v2")
    assert POLICY.decision(after, "v2") == "CAUTION"
    assert after["advisory_clear_cap"] is None and after["clear_distance"] == 120.0
    source["warnings"].append({"distance": 70.08, "reason": ""})
    assert candidate_ranges(source, "v2")["clear_distance"] == 70.0


@pytest.mark.parametrize("warnings", [None, [], [None], [{}], [{"distance": float("nan")}],
                                      [{"distance": float("inf")}], [{"distance": -1}], [{"distance": True}]])
def test_missing_active_advisory_geometry_never_invents_clear_range(warnings):
    after = candidate_ranges(row(warnings=warnings))
    assert after["clear_distance"] == 0.0 and POLICY.decision(after) == "CAUTION"


def test_small_target_prior_threshold_uses_configured_far_minimum_and_is_explicit():
    limit = small_target_limit("pandar128", 3)
    assert limit == pytest.approx(88.762, abs=.001)
    assert float(expected_points(limit, .3, .3)) >= 3
    assert float(expected_points(limit + .001, .3, .3)) < 3
    assert small_target_limit("pandar128", 6) < limit
    assert small_target_limit("pandar128", 3, 50.0) == 50.0
    source = row(warning=False, warnings=[])
    observed = candidate_ranges(source, sensor_model="pandar128")
    assert observed["monitored_small"] == 88.7 and observed["clear_distance"] == 120.0
    qualified = candidate_ranges(source, sensor_model="pandar128", cap_small_target=True)
    assert qualified["clear_distance"] == qualified["monitored_small"] == 88.7
    assert POLICY.decision(qualified) == "GO"


def test_expanded_judge_range_alias_cannot_disagree_with_projected_output():
    result = candidate_ranges(row(clear=120., monitored=150.), sensor_model="pandar128")
    assert result["clear"] == result["clear_distance"] == 40.0


def test_approved_conservative_profile_names_the_qualified_cap_without_changing_decisions():
    source = row(warning=False, warnings=[])
    result = candidate_ranges(source, sensor_model="pandar128", cap_small_target=True,
                              profile="conservative_2026_10_17")
    assert result["clear_distance"] == 88.7 and POLICY.decision(result) == "GO"
    assert result["range_policy"] == "c2_conservative_2026_10_17"
    with pytest.raises(ValueError):
        candidate_ranges(source, profile="conservative_2026_10_17")
    for threshold in (2, 4):
        with pytest.raises(ValueError, match="min_points_far=3"):
            candidate_ranges(source, sensor_model="pandar128", cap_small_target=True,
                             min_points_far=threshold, profile="conservative_2026_10_17")


@pytest.mark.parametrize("sensor", ["unknown", "falcon_prime"])
def test_unknown_scan_model_is_unavailable_never_pandar(sensor):
    assert small_target_limit(sensor) is None
    result = candidate_ranges(row(), sensor_model=sensor)
    assert result["monitored_small"] is None
    assert result["monitored_small_model"]["available"] is False
    assert result["clear_distance"] == 40.0
    assert candidate_ranges(row(), sensor_model=sensor, cap_small_target=True)["clear_distance"] == 0.0


@pytest.mark.parametrize("state", ["stale", "error", "stop_error"])
def test_invalid_freshness_or_fault_zeroes_all_ranges_and_preserves_stop(state):
    source = row(obstacle=state == "stop_error")
    if state == "stale":
        source["freshness"] = {"valid": False}
    else:
        source["health"]["level"] = source["health"]["decision_level"] = "error"
    result = candidate_ranges(source, sensor_model="pandar128", cap_small_target=True)
    assert result["clear_distance"] == result["monitored_small"] == result["health"]["monitored_range"] == 0
    assert result["detector_clear_distance"] == 120.0
    assert POLICY.decision(result) == POLICY.decision(source)


def test_malformed_health_cannot_keep_positive_candidate_range_even_with_stop():
    for stop in (False, True):
        source = row(obstacle=stop)
        source["health"]["level"] = "bad"
        result = candidate_ranges(source, sensor_model="pandar128")
        assert result["clear_distance"] == result["monitored_small"] == 0.0
        assert result["health"]["monitored_range"] == 0.0


@pytest.mark.parametrize("threshold", [0, -1, 3.0, True])
def test_invalid_density_threshold_rejected(threshold):
    with pytest.raises(ValueError):
        small_target_limit("pandar128", threshold)
