import numpy as np
import pytest

from resense.config import ClusterConfig
from resense.clustering import cluster_labels
from scripts.diagnose_oracle_accumulation import bounded_labels, oracle_speed


def test_motion_fit_retains_duplicate_and_handles_following_jump():
    stamps = [0, .1, .2, .3, .4]
    positions = [100, 98, 96, 96, 92]
    speed, raw = oracle_speed(stamps, positions)
    assert speed == pytest.approx(20)
    assert raw == pytest.approx(20)
    assert positions == [100, 98, 96, 96, 92]


def test_motion_fit_warmup_and_clip_are_explicit():
    assert oracle_speed([0], [100]) == (None, None)
    assert oracle_speed([0, .1], [100, 96]) == pytest.approx((30, 40))
    with pytest.raises(ValueError, match="strictly increasing"):
        oracle_speed([0, 0], [100, 96])


def test_bounded_graph_splits_two_dense_depth_faces():
    cfg = ClusterConfig()
    xyz = np.array([[x, y, 0] for x in (100, 103) for y in (0, .1, .2)], np.float32)
    assert len(set(cluster_labels(xyz, cfg))) == 1
    labels = bounded_labels(xyz, cfg)
    assert labels.tolist() == [0, 0, 0, 1, 1, 1]


def test_bounded_graph_preserves_ordinary_cluster_and_noise():
    cfg = ClusterConfig()
    xyz = np.array([[10, 0, 0], [10, .1, 0], [10, .2, 0], [20, 3, 0]], np.float32)
    assert np.array_equal(bounded_labels(xyz, cfg), cluster_labels(xyz, cfg))
