import numpy as np
import pytest

from resense.config import ClusterConfig
from resense.frame import Frame
from scripts.diagnose_range_metric import exact_fixture_indices, measure


def test_radial_bridge_removed_without_dropping_transverse_neighbor():
    cfg = ClusterConfig()
    points = np.array([[100, 0, 0], [103, 0, 0], [100, 1, 0]], np.float32)
    result = measure(points, [True, False, False], [True] * 3, cfg)
    assert result["connected_background_raw_baseline_graph"] == 2
    assert result["connected_background_raw_bounded_graph"] == 1
    assert result["source_background_edges_above_linear_bound"] == 1
    edge = result["source_incident_excess_edges"][0]
    assert edge["distance_m"] == pytest.approx(3)
    assert edge["linear_bound_m"] == pytest.approx(1.225)


def test_radial_voxel_collapse_is_separate_from_neighbor_bridges():
    cfg = ClusterConfig()
    points = np.array([[100.1, 0, 0], [100.2, 0, 0], [100.3, 0, 0]], np.float32)
    base = measure(points, [True, True, False], [True] * 3, cfg)
    refined = measure(points, [True, True, False], [True] * 3, cfg, refine=True)
    assert base["voxels"] == 1
    assert base["target_mixed_voxels"] == 1
    assert base["neighbor_edges"] == 0  # An edge filter cannot undo this mixed cell.
    assert refined["voxels"] > base["voxels"]
    assert refined["target_voxels"] >= base["target_voxels"]


def test_exact_fixture_multiset_records_ambiguity_and_rejects_missing():
    xyz = np.array([[10, .1, .2], [10, .1, .2], [20, 0, 0]], np.float32)
    frame = Frame(xyz, np.ones(3, np.float32))
    source = np.array([[10.001, .101, .201, 1]], np.float32)
    ids, extra = exact_fixture_indices(frame, source)
    assert len(ids) == 1
    assert extra == 1
    with pytest.raises(ValueError, match="missing"):
        exact_fixture_indices(frame, np.array([[11, .1, .2, 1]], np.float32))


def test_empty_corridor_is_reported():
    assert measure(np.empty((0, 3)), [], [], ClusterConfig())["target_raw"] == 0
