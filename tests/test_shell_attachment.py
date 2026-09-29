"""Opt-in shell attachment (``cluster.shell_*``, after TunnelGuard ``_shell_points``)."""
from dataclasses import replace

import numpy as np

from resense.clustering import Cluster
from resense.config import DetectorConfig
from resense.detector import Detector


def _cluster(idx, x, top, bottom=0.2) -> Cluster:
    c = np.array([x, 0.0, 1.0])
    return Cluster(points_idx=np.asarray(idx), n=10, n_raw=10, centroid=c, bbox_min=np.array([x, -0.2, 0.0]),
                   bbox_max=np.array([x + 0.3, 0.2, 2.5]), distance=x, lateral=0.0, height_min=bottom,
                   height_max=top, intensity=10.0, n_expected=10.0, score=1.0, zone="gauge", n_gauge=8)


def _scene(x=80.0, top=2.5, lining_gap=0.1, lining=True):
    """A column: points up to ``top`` above the rail head, then (optionally) lining from ``top + gap``."""
    col = [(x + 0.1, 0.0, hh) for hh in np.linspace(0.2, top, 12)]
    above = [(x + 0.1, dy, top + lining_gap + k * 0.2) for k in range(4) for dy in (-0.1, 0.1)] if lining else []
    pts = np.array(col + above, dtype=float)
    xyz = np.stack([pts[:, 0], pts[:, 1], pts[:, 2]], axis=1)
    return xyz, pts[:, 1], pts[:, 2], np.arange(len(col))


def _det(**kw):
    cfg = DetectorConfig()
    return Detector(replace(cfg, cluster=replace(cfg.cluster, shell_min_top=2.3, **kw)))


def test_on_by_default():
    assert DetectorConfig().cluster.shell_min_top == 2.3


def test_a_column_continuing_into_the_lining_is_infrastructure():
    xyz, dy, h, idx = _scene()
    cl = _cluster(idx, 80.0, top=2.5)
    _det()._shell([cl], xyz, dy, h)
    assert (cl.reason, cl.zone, cl.demoted) == ("shell", "warning", True)


def test_a_gap_above_the_top_or_no_lining_keeps_the_obstacle():
    for kw in (dict(lining_gap=1.0), dict(lining=False)):
        xyz, dy, h, idx = _scene(**kw)
        cl = _cluster(idx, 80.0, top=2.5)
        _det()._shell([cl], xyz, dy, h)
        assert cl.zone == "gauge" and not cl.reason


def test_person_height_hanging_and_near_clusters_are_not_tested():
    xyz, dy, h, idx = _scene(top=1.8)
    for cl in (_cluster(idx, 80.0, top=1.8), _cluster(idx, 80.0, top=2.5, bottom=1.0), _cluster(idx, 20.0, top=2.5)):
        _det()._shell([cl], xyz, dy, h)
        assert cl.zone == "gauge" and not cl.reason
