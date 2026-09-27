from types import SimpleNamespace

import pytest

from scripts.evaluate_thin_monitoring import thin_distance, thin_row
from scripts.score_clear_distance import decision


def cluster(**kwargs):
    return SimpleNamespace(**dict(dict(thin=True, kind="", zone="gauge", reason="",
                                       n_gauge=3, distance=30.0), **kwargs))


@pytest.mark.parametrize("change", [{"kind": "low"}, {"zone": "warning"}, {"reason": "column"},
                                   {"thin": False}, {"n_gauge": 2}, {"distance": 61.0},
                                   {"distance": float("nan")}, {"distance": -1.0}])
def test_unsupported_or_demoted_cluster_does_not_cap(change):
    assert thin_distance([cluster(**change)], 3, 60, 1) is None


def test_caps_nearest_supported_single_frame_thin_cluster_only():
    clusters = [cluster(distance=40), cluster(), cluster(distance=20, n_gauge=2)]
    assert thin_distance(clusters, 3, 60, 1) == 30
    assert thin_distance(clusters, 3, 60, 2) is None
    assert thin_distance(clusters, 3, 29, 1) is None


def test_uncertainty_is_explicit_and_stop_fault_are_preserved():
    old = {"clear_distance": 100, "obstacle": False, "warning": False,
           "health": {"level": "ok", "decision_level": "ok", "messages": []}}
    new = thin_row(old, 30)
    assert new["clear_distance"] == 30
    assert new["health"]["monitoring_status"] == "unresolved_thin_cluster"
    assert new["health"]["thin_cluster_distance"] == 30
    assert decision(new) == "CAUTION"
    assert decision(thin_row(dict(old, obstacle=True), 30)) == "STOP"
    old["health"]["level"] = "error"
    assert decision(thin_row(old, 30)) == "FAULT"
    assert old["clear_distance"] == 100 and old["health"]["messages"] == []
