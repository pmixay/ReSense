"""Output-identical CPU savings of 25.09 (captain action 11): each replacement must give exactly
what the code it replaces gave.

* ``resense.clustering.dbscan_labels`` against ``sklearn.cluster.DBSCAN`` (labels, including the
  border points and the cluster numbering) on random sets built to hit the edge cases.
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.clustering import cluster_labels, dbscan_labels
from resense.config import ClusterConfig

sklearn_cluster = pytest.importorskip("sklearn.cluster")


def _sets(seed: int = 0, n_sets: int = 400):
    """Uniform clouds, grids spaced exactly eps apart (distance ties), blobs with shared border
    points, duplicated points; float32 like the voxel centres the detector clusters."""
    rng = np.random.default_rng(seed)
    for t in range(n_sets):
        n = int(rng.integers(1, 300))
        kind = t % 4
        if kind == 0:
            p = rng.uniform(0.0, 5.0, (n, 3))
        elif kind == 1:
            p = rng.integers(0, 8, (n, 3)) * 0.35
        elif kind == 2:
            c = rng.uniform(0.0, 10.0, (max(1, n // 20), 3))
            p = c[rng.integers(0, len(c), n)] + rng.normal(0.0, 0.3, (n, 3))
        else:
            p = rng.uniform(0.0, 3.0, (n, 3))
            p[n // 2:] = p[: n - n // 2]
        yield p.astype(np.float32), float(rng.choice([0.1, 0.2, 0.35, 0.5])), int(rng.integers(1, 6))


def test_dbscan_labels_equal_sklearn():
    for p, eps, ms in _sets():
        want = sklearn_cluster.DBSCAN(eps=eps, min_samples=ms, algorithm="kd_tree").fit_predict(p)
        np.testing.assert_array_equal(dbscan_labels(p, eps, ms), want)


def test_dbscan_border_point_takes_the_lowest_cluster():
    # index 0 is a border point between two clusters (0.35 m from one core point of each, with
    # eps 0.4 and 4 samples it is not a core point itself); the cluster listed first (B) gets
    # label 0 and, as in sklearn's seed loop, the border point with it
    border = [(0.5, 0.0, 0.0)]
    b = [(1.0, 0.0, 0.0), (1.0, 0.1, 0.0), (1.0, -0.1, 0.0), (0.85, 0.0, 0.0)]
    a = [(0.0, 0.0, 0.0), (0.0, 0.1, 0.0), (0.0, -0.1, 0.0), (0.15, 0.0, 0.0)]
    p = np.array(border + b + a, dtype=np.float32)
    want = sklearn_cluster.DBSCAN(eps=0.4, min_samples=4, algorithm="kd_tree").fit_predict(p)
    got = dbscan_labels(p, 0.4, 4)
    np.testing.assert_array_equal(got, want)
    assert got.tolist() == [0, 0, 0, 0, 0, 1, 1, 1, 1]


def test_cluster_labels_empty_and_range_scaled():
    cfg = ClusterConfig()
    assert cluster_labels(np.zeros((0, 3), np.float32), cfg).size == 0
    rng = np.random.default_rng(3)
    xyz = (rng.uniform(-1.0, 1.0, (500, 3)) + np.array([60.0, 0.0, 1.0])).astype(np.float32)
    r = np.linalg.norm(xyz, axis=1)
    p = xyz / (1.0 + r / cfg.range_scale)[:, None]
    want = sklearn_cluster.DBSCAN(eps=cfg.eps, min_samples=cfg.min_samples, algorithm="kd_tree").fit_predict(p)
    np.testing.assert_array_equal(cluster_labels(xyz, cfg), want)
