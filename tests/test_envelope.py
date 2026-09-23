"""v0.6 behaviour required by the organizers' Q&A session (docs/organizers/QA_session.md):

* the monitored envelope is the train's 2.1 m x 3.0 m cross-section (an object 1.3 m off the
  axis is advisory, not an alarm);
* the size criterion is a 300 x 300 x 100 mm object on the track (the low-object stage);
* a broken cable hanging into the envelope must be detected (no column / floating / overhead
  demotion near the axis).
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, catalogue_spec, synthetic_tunnel_frame

FLOOR_Z = -1.5          # synthetic_tunnel_frame default: the bed (rails 0.18 m on top of it)


def _scene(specs, seed=5):
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=specs)
    return frame


def _run(frame: Frame, n: int = 6, cfg: DetectorConfig = None):
    det = Detector(cfg or DetectorConfig())
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k))
    return res


def test_default_gauge_is_the_organizers_envelope():
    p = np.asarray(DetectorConfig().gauge.profile)
    assert p[:, 0].max() == pytest.approx(1.05) and p[:, 0].min() == pytest.approx(-1.05)
    assert p[:, 1].max() == pytest.approx(3.0)


def test_clear_tunnel_has_no_low_object_alarm(tunnel):
    frame, _, _ = tunnel
    res = _run(frame, 8)
    assert not res.obstacle, [d.to_dict() for d in res.detections]
    assert not any(c.kind == "low" for c in res.candidates)


RAIL_HEAD_Z = FLOOR_Z + 0.18    # synthetic rails are 0.18 m tall


@pytest.mark.parametrize("distance,lateral", [(10.0, -0.8), (16.0, 0.8), (20.0, -0.75)])
def test_organizers_minimum_object_on_a_rail(distance, lateral):
    """300 x 300 x 100 mm lying on a rail head: 0.1 m above the rail-head plane, below the
    0.12 m polygon bottom - found by the low-object stage (bumps above the learned bed)."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=lateral, base_z=RAIL_HEAD_Z)
    res = _run(_scene([spec]))
    assert res.obstacle, [(c.kind, c.distance, c.size.round(2).tolist()) for c in res.candidates]
    d = res.detections[0]
    assert abs(d.distance - distance) < 0.6 and abs(d.lateral - lateral) < 0.3


@pytest.mark.parametrize("distance,lateral", [(12.0, 0.0), (20.0, 0.4), (28.0, -0.3)])
def test_minimum_object_below_the_rail_head_is_a_policy(distance, lateral):
    """The same object lying on the bed between the rails stays below the rail head: by default
    (``lowobj.min_top`` = 0.0: the object's top must reach the rail-head plane) it is not an alarm - the metro bed carries fixtures of that size
    every few tens of metres (1 350 alarm events on the 20-minute ride with the bed-level policy,
    EXPERIMENTS.md §1d); ``min_top: -1`` with ``min_point_top: -1`` reports any bump above the bed."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=lateral, base_z=FLOOR_Z)
    assert not _run(_scene([spec])).obstacle
    cfg = DetectorConfig()
    cfg.lowobj.min_top = cfg.lowobj.min_point_top = -1.0     # the bed-level policy
    res = _run(_scene([spec]), cfg=cfg)
    assert res.obstacle and res.detections[0].kind == "low"
    assert abs(res.detections[0].distance - distance) < 0.6


@pytest.mark.parametrize("distance,lateral", [(25.0, -0.8), (40.0, 0.8), (50.0, -0.8)])
def test_object_lying_across_a_rail_is_found_whole(distance, lateral):
    """v0.6.2: shaped like the organizers' object in ``doubleT_obstacle`` - standing on the bed
    across a rail, its top 0.13 m above the rail head, most of it below the rail head. The
    point-wise low stage sees only the slice between 3 cm and the 0.12 m envelope floor and the
    corridor stage the top centimetre; the straddle clustering takes it whole."""
    spec = ObstacleSpec(kind="box", size=(0.4, 0.6, 0.31), distance=distance, lateral=lateral, base_z=FLOOR_Z)
    res = _run(_scene([spec]), n=8)
    assert res.obstacle, [(c.kind, c.distance, c.size.round(2).tolist()) for c in res.candidates]
    d = res.detections[0]
    assert d.kind == "low" and abs(d.distance - distance) < 0.8 and abs(d.lateral - lateral) < 0.4


def _sparse_object_across_a_rail(tunnel_frame: Frame, x0: float, top: float, seed: int = 0) -> Frame:
    """The point layout measured on the organizers' object at 56 m (23.09, EXPERIMENTS.md §1d):
    ~21 returns, 16 below 3 cm above the rail head, 2 between 3 cm and the 0.12 m envelope floor,
    3 above the floor up to ``top``; lying across the right rail (the synthetic axis is at
    y = 0.25, the rails at +-0.8 from it)."""
    rng = np.random.default_rng(seed)
    lo = 0.121 if top > 0.121 else top - 0.02          # a fitting that stays below the floor: its top 3 points
    hs = np.concatenate([rng.uniform(-0.15, 0.02, 16), rng.uniform(0.03, min(0.10, top), 2), rng.uniform(lo, top, 3)])
    n = hs.size
    dy = np.concatenate([rng.uniform(-1.1, -0.88, n // 2), rng.uniform(-0.72, -0.5, n - n // 2)])
    pts = np.stack([rng.uniform(x0, x0 + 0.4, n), 0.25 + dy, RAIL_HEAD_Z + hs], axis=1).astype(np.float32)
    return Frame(xyz=np.concatenate([tunnel_frame.xyz, pts]),
                 intensity=np.concatenate([tunnel_frame.intensity, np.full(n, 20.0, np.float32)]))


def test_sparse_object_straddling_the_envelope_floor(tunnel):
    """v0.6.2 regression: neither the point-wise low stage (2 points) nor the corridor stage
    (3 points) confirms the real object's layout; the straddle clustering does, and a fitting of
    the same layout whose top stays 6 cm above the rail head is not reported."""
    frame, _, _ = tunnel
    obj = _sparse_object_across_a_rail(frame, 45.0, top=0.135)
    cfg = DetectorConfig()
    cfg.lowobj.straddle_enabled = False
    assert not _run(obj, 8, cfg).obstacle
    res = _run(obj, 8)
    assert res.obstacle and res.detections[0].kind == "low", [(c.kind, c.distance) for c in res.candidates]
    assert abs(res.detections[0].distance - 45.0) < 0.8
    assert not _run(_sparse_object_across_a_rail(frame, 45.0, top=0.06), 8).obstacle


def test_low_object_stage_can_be_switched_off():
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=15.0, lateral=0.8, base_z=RAIL_HEAD_Z)
    assert _run(_scene([spec])).obstacle
    cfg = DetectorConfig()
    cfg.lowobj.enabled = False
    assert not _run(_scene([spec]), cfg=cfg).obstacle


@pytest.mark.parametrize("distance,lateral,name", [(25.0, 0.0, "cable"), (40.0, 0.3, "cable"),
                                                   (30.0, -0.2, "cable_low")])
def test_hanging_cable_in_the_envelope_is_an_obstacle(distance, lateral, name):
    spec = catalogue_spec(name, distance, lateral, reflectivity=25.0)
    res = _run(_scene([spec]))
    assert res.obstacle, [(c.distance, c.zone, c.reason, c.size.round(2).tolist()) for c in res.candidates]
    assert abs(res.nearest_distance - distance) < 1.0


def test_object_outside_the_envelope_is_advisory():
    """A person 1.35 m off the axis: inside the v0.5 polygon (1.40 m), outside the 1.05 m envelope."""
    spec = catalogue_spec("person", 35.0, 1.35, reflectivity=30.0)
    res = _run(_scene([spec]))
    assert not res.obstacle
    assert res.warning


def test_person_in_the_envelope_still_alarms():
    spec = catalogue_spec("person", 60.0, 0.2, reflectivity=30.0)
    res = _run(_scene([spec]))
    assert res.obstacle and abs(res.nearest_distance - 60.0) < 1.0


def test_wall_face_cluster_does_not_break_later_low_clusters():
    """Regression (v0.6 review): the wall-face rule used a local variable named ``low`` that
    shadowed the low-candidate flags of find_clusters, so a wall face followed by more
    clusters in the same frame raised IndexError on the extended ride."""
    from resense.clustering import find_clusters
    from resense.config import ClusterConfig, LowObjectConfig
    rng = np.random.default_rng(0)

    def blob(x, y, z, L, W, H, n):
        return np.stack([rng.uniform(x, x + L, n), rng.uniform(y - W / 2, y + W / 2, n), rng.uniform(z, z + H, n)], 1)

    face = blob(15.0, 1.0, 0.55, 0.3, 1.3, 2.4, 3000)       # wall face at the edge, nearest (clusters run in voxel order)
    other = [blob(30.0 + 5 * k, 0.0, 0.3, 0.5, 0.5, 0.5, 400) for k in range(4)]
    pts = np.concatenate([face] + other).astype(np.float32)
    dy, h = pts[:, 1].astype(np.float64), pts[:, 2].astype(np.float64)
    low = np.zeros(pts.shape[0], bool)
    low[-50:] = True
    out = find_clusters(pts, np.full(pts.shape[0], 30.0, np.float32), dy, h, np.abs(dy) < 1.05, ClusterConfig(),
                        low=low, low_cfg=LowObjectConfig())
    assert len(out) >= 4
