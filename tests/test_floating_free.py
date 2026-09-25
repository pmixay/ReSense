"""The free-hanging exemption of the ``floating`` signature (25.09, round 2; P3).

``cluster.floating_free_max_size`` (with ``floating_free_max_dy`` and ``floating_free_max_top``):
the ``floating`` shape (bottom above 0.7 m, under 1.2 m tall and 1.0 m wide, off the track centre)
does not demote a compact cluster hanging free inside the envelope - every extent at most
``floating_free_max_size``, its outermost point at most ``floating_free_max_dy`` off the axis (it
does not reach the wall side of the corridor) and its top at most ``floating_free_max_top`` (it
does not reach up to the vault). The target is the organizers' 0.3 m cube hanging 1.0-1.4 m above
the rail head 0.6-0.8 m off the axis (set O #2), advisory at 44-59 m with the rule off.
docs/evidence/results/p3_signatures_2026-09-25.json has the pre-registration and the measurements.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from resense.clustering import _advisory_reason, _Blob
from resense.config import ClusterConfig, DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

FREE_SIZE = 0.5          # the candidate measured on 25.09 (m); 0 = off


def _box(x0: float, length: float, lateral: float, bottom: float, height: float, width: float):
    g = np.stack(np.meshgrid(np.linspace(0, length, 6), np.linspace(-width / 2, width / 2, 4),
                             np.linspace(0, height, 4), indexing="ij"), axis=-1).reshape(-1, 3)
    xyz = (g + np.array([x0, lateral, bottom])).astype(np.float32)
    return _Blob.of(xyz, np.arange(xyz.shape[0]), xyz.shape[0]), xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)


def _reason(cfg, x0, length, lateral, bottom, height, width):
    b, dy, h = _box(x0, length, lateral, bottom, height, width)
    return _advisory_reason(b, x0, float(dy.mean()), "gauge", dy, h, cfg, 1e9, None)


def _on(cfg: ClusterConfig = None) -> ClusterConfig:
    return replace(cfg or ClusterConfig(), floating_free_max_size=FREE_SIZE)


def test_free_hanging_classification():
    off = replace(ClusterConfig(), floating_free_max_size=0.0)
    on = _on()
    # the organizers' cube #2 as the detector sees it at 44-56 m: its front face, 0.6-0.8 m off the axis
    for lat in (0.61, 0.7, 0.77):
        assert _reason(off, 50.0, 0.05, lat, 1.17, 0.22, 0.28) == "floating"
        assert _reason(on, 50.0, 0.05, lat, 1.17, 0.22, 0.28) == ""
    assert _reason(on, 50.0, 0.3, 0.7, 1.0, 0.3, 0.3) == ""                 # seen whole
    # what the floating shape must keep demoting
    assert _reason(on, 50.0, 0.3, 1.1, 1.0, 0.3, 0.3) == "floating"         # reaches past 0.95 m: wall side
    assert _reason(on, 50.0, 0.05, 0.95, 1.2, 0.25, 0.5) == "floating"      # a sign 0.7-1.2 m off the axis
    assert _reason(on, 50.0, 0.3, 0.7, 2.3, 0.3, 0.3) == "floating"         # top at 2.6 m: hangs from the vault
    assert _reason(on, 50.0, 1.0, 0.7, 1.0, 0.3, 0.3) == "floating"         # 1 m long: a fixture, not compact
    assert _reason(on, 50.0, 0.3, 0.65, 1.0, 0.3, 0.7) == "floating"        # 0.7 m wide
    assert _reason(on, 104.0, 5.5, 0.5, 2.2, 0.65, 0.2) == "floating"       # the long overhead structure


def test_free_hanging_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml("configs/default.yaml"),
                DetectorConfig.from_yaml("ros2_ws/src/resense_ros/config/detector.yaml")):
        c = cfg.cluster
        assert (c.floating_free_max_size, c.floating_free_max_dy, c.floating_free_max_top) == (0.0, 0.95, 2.5)


def _cast(specs):
    from resense.synthetic import synthetic_tunnel_frame
    frame, labels, _ = synthetic_tunnel_frame(rng=np.random.default_rng(1), specs=specs)
    return frame, labels


def _last(frame: Frame, cfg: DetectorConfig, n: int = 6):
    det = Detector(cfg)
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k))
    return res


def _cfgs():
    off = DetectorConfig()
    off.cluster = replace(off.cluster, floating_free_max_size=0.0)
    on = DetectorConfig()
    on.cluster = _on(on.cluster)
    return off, on


def test_free_hanging_cube_is_a_stop(tunnel):
    """Ray-cast tunnel: the organizers' 0.3 m cube hanging 1.0-1.1 m above the rail head, 0.7-0.75 m off
    the axis, at 30-55 m: advisory ``floating`` with the rule off, a STOP with it on."""
    from resense.synthetic import ObstacleSpec
    off, on = _cfgs()
    for dist, lat, base in ((30.0, 0.75, 1.0), (40.0, 0.75, 1.0), (55.0, 0.7, 1.1)):
        frame, labels = _cast([ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=dist, lateral=lat, base=base)])
        assert (labels == 1).sum() >= 5
        res = _last(frame, off)
        assert not res.obstacle and res.warning and res.warnings[0].reason == "floating", dist
        res = _last(frame, on)
        assert res.obstacle, [(c.distance, c.zone, c.reason) for c in res.candidates]
        d = res.detections[0]
        assert d.zone == "gauge" and d.reason == "" and abs(d.distance - dist) < 0.5
        assert base - 0.05 < d.height_min < base + 0.3 and abs(d.lateral - lat) < 0.1   # the cube itself


def test_nearby_obstacle_and_wall_fixture(tunnel):
    """Ray-cast tunnel: a person-size box standing on the axis next to the cube is a STOP with the
    rule off and on (the rule only takes demotions away); a 0.3 m tall plate fixed to the side wall
    at the cube's height, reaching into the envelope to 0.75 m off the axis, stays advisory
    ``floating`` with the rule on."""
    from resense.synthetic import ObstacleSpec
    off, on = _cfgs()
    cube = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=40.0, lateral=0.75, base=1.0, label="cube")
    person = ObstacleSpec(kind="box", size=(0.3, 0.5, 1.8), distance=40.0, lateral=-0.3, label="person")
    frame, _ = _cast([cube, person])
    for cfg in (off, on):
        res = _last(frame, cfg)
        assert res.obstacle
        assert any(abs(d.lateral + 0.3) < 0.3 and d.height_min < 0.3 for d in res.detections)
    # a plate from the tunnel wall (|y| 2.7 m) to 0.75 m off the axis, 1.0-1.3 m above the rail head
    plate = ObstacleSpec(kind="box", size=(0.3, 1.95, 0.3), distance=40.0, lateral=-(0.75 + 1.95 / 2), base=1.0)
    frame, labels = _cast([plate])
    assert (labels == 1).sum() >= 5
    res = _last(frame, on)
    assert not res.obstacle and res.warning and res.warnings[0].reason == "floating"
