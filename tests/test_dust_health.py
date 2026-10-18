from types import SimpleNamespace

import numpy as np
import pytest

from resense.dust_health import diffuse_evidence, mark_degraded_health, mark_unsupported_clusters


def cluster(n):
    return SimpleNamespace(points_idx=np.arange(n), zone="gauge", reason="", demoted=False, distance=50.)


def mark(xyz, intensity, active=True):
    c = cluster(len(xyz))
    result = mark_unsupported_clusters([c], xyz, np.asarray(intensity), np.zeros(len(xyz)),
                                      np.ones(len(xyz)), {"active": active})
    return c, result


@pytest.mark.parametrize("distance", [10., 50., 100., 200.])
@pytest.mark.parametrize("count", [1, 2, 3])
def test_newly_appearing_sparse_dark_objects_are_never_demoted(distance, count):
    xyz = np.array([[distance, 0, 0], [distance, .4, .4], [distance, .8, .8]])[:count]
    c, result = mark(xyz, np.ones(count))
    assert c.zone == "gauge" and result["marked"] == 0


@pytest.mark.parametrize("intensity", [[1, 30, 1, 1], [30, 1, 1, 1]])
def test_strong_coincident_echo_survives_dedup_in_either_input_order(intensity):
    xyz = np.array([[50, 0, 0], [50, 0, 0], [51, 1, 1], [52, 2, 2]])
    c, result = mark(xyz, intensity)
    assert c.zone == "gauge" and result["protected_strong"] == 1


def test_local_dark_body_support_is_preserved():
    xyz = np.array([[50, 0, 0], [50, .1, .1], [50, .2, .2]])
    c, result = mark(xyz, [0, 0, 0])
    assert c.zone == "gauge" and result["marked"] == 0


@pytest.mark.parametrize("xyz", [
    [[30, 0, 0], [30, 0, .4], [30, 0, .8], [30, 0, 1.2]],
    [[30, 0, 0], [30.4, .4, .4], [30.8, .8, .8], [31.2, 1.2, 1.2]],
    [[30, 0, 0], [30, 0, .8], [30, .8, 0], [30, .8, .8]],
])
def test_new_dark_thin_cable_and_planar_box_survive_sparse_sampling(xyz):
    c, result = mark(np.array(xyz), [0, 0, 0, 0])
    assert c.zone == "gauge" and result["protected_surface"] == 1


def test_near_clutter_cannot_demote_far_sparse_object():
    xyz = np.array([[150, 0, 0], [150, 1, 1], [150, 2, 2], [20, 0, 1]])
    c = cluster(3)
    result = mark_unsupported_clusters([c], xyz, np.ones(4), np.zeros(4), np.ones(4),
                                      {"active": True, "examined_range": 60.0})
    assert c.zone == "gauge" and result["protected_outside"] == 1


def test_isolated_multi_return_clutter_becomes_visible_advisory_only_when_diffuse():
    xyz = np.array([[50, 0, 0], [50, 1, 1], [51, 0, 1], [51, 1, 0]])
    c, result = mark(xyz, [1, 1, 1, 1])
    assert c.zone == "warning" and c.reason == "diffuse_low_support" and result["marked"] == 1
    c, result = mark(xyz, [1, 1, 1, 1], active=False)
    assert c.zone == "gauge" and result["marked"] == 0


def test_flat_surface_does_not_satisfy_volumetric_coverage():
    x, y, h = np.meshgrid(np.arange(5, 60, .5), [-.75], np.arange(.3, 2.7, .1))
    xyz = np.column_stack((x.ravel(), y.ravel(), h.ravel()))
    assert not diffuse_evidence(xyz, np.ones(len(xyz)), xyz[:, 1], xyz[:, 2], 60)["active"]


def test_broad_volume_is_flagged_without_dust_truth_or_intensity_units_inference():
    rng = np.random.default_rng(0)
    xyz = rng.uniform([5, -1, .3], [60, 1, 2.7], (5000, 3))
    evidence = diffuse_evidence(xyz, np.ones(len(xyz)), xyz[:, 1], xyz[:, 2], 60)
    assert evidence["active"] and evidence["occupied_fraction"] > .9
    assert not diffuse_evidence(xyz, np.full(len(xyz), 30), xyz[:, 1], xyz[:, 2], 60)["active"]
    health = mark_degraded_health({"level": "error", "decision_level": "error", "clear_distance": 80}, evidence, {})
    assert health["level"] == health["decision_level"] == "error"
    assert health["clear_distance"] == health["monitored_range"] == 0
