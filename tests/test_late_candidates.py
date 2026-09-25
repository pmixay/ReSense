"""Late detector candidates behind default-off flags (captain action 11, go / no-go 26.09).

* ``cluster.short_signature_max_length`` (P3 / P4 candidate of 24.09): the ``elevated`` and
  ``floating`` signatures do not demote a cluster as short and as near as the organizers' test
  objects. Off by default; the default output must not change.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from resense.clustering import _advisory_reason, _Blob
from resense.config import ClusterConfig, DetectorConfig

ROOT = Path(__file__).resolve().parents[1]


def _box(x0: float, length: float, lateral: float, bottom: float, height: float, width: float):
    """A cluster of points filling a box: (blob, dy, h) with the track axis at y = 0, rail head at z = 0."""
    g = np.stack(np.meshgrid(np.linspace(0, length, 6), np.linspace(-width / 2, width / 2, 4),
                             np.linspace(0, height, 4), indexing="ij"), axis=-1).reshape(-1, 3)
    xyz = (g + np.array([x0, lateral, bottom])).astype(np.float32)
    idx = np.arange(xyz.shape[0])
    return _Blob.of(xyz, idx, xyz.shape[0]), xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)


def _reason(cfg, x0, length, lateral, bottom, height, width):
    b, dy, h = _box(x0, length, lateral, bottom, height, width)
    return _advisory_reason(b, x0, float(dy.mean()), "gauge", dy, h, cfg, 1e9, None)


def test_short_signature_rule_is_off_by_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.short_signature_max_length == 0.0
    cfg = ClusterConfig()
    # the organizers' 0.3 m cube floating mid-envelope off the centre, their 2 x 2 m box at the top
    assert _reason(cfg, 50.0, 0.3, 0.75, 1.0, 0.3, 0.3) == "floating"
    assert _reason(cfg, 40.0, 2.0, 0.0, 2.3, 0.7, 2.2) == "elevated"


def test_short_signature_rule_when_on():
    cfg = replace(ClusterConfig(), short_signature_max_length=3.0, short_signature_max_distance=100.0)
    assert _reason(cfg, 50.0, 0.3, 0.75, 1.0, 0.3, 0.3) == ""               # short, near: an obstacle
    assert _reason(cfg, 40.0, 2.0, 0.0, 2.3, 0.7, 2.2) == ""
    assert _reason(cfg, 104.0, 0.3, 0.75, 1.0, 0.3, 0.3) == "floating"      # beyond 100 m: demoted as before
    assert _reason(cfg, 60.0, 5.5, 0.75, 2.0, 0.6, 0.2) == "floating"       # 5.5 m long structure: demoted
    assert _reason(cfg, 40.0, 4.0, 0.0, 2.3, 0.7, 2.2) == "elevated"
    assert _reason(cfg, 50.0, 0.3, 0.2, 1.0, 0.3, 0.3) == ""                # near the axis: never floating
