"""The frame the envelope is measured from (``gauge.reference``, 27.09, P1 edge objects; off by default).

The organizers place their test objects from the sensor's X axis; the detector measures the envelope
from the rails, which run at about -0.25 deg to the sensor axis on the recordings. ``gauge.reference``
1 measures the strict membership and the shape rules from the sensor axis where it agrees with the
rails (straight track, rail pair locked, near field, the two axes within ``reference_max_offset``);
2 clamps the offset to ``reference_max_offset`` instead of switching back to the rails. It is a
replacement, not a union: an object inside the rail envelope but outside the sensor-axis one is not
a STOP (the trade-off these tests pin down). The candidate set, the reported lateral and the bed /
low-object stages keep the rails.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig, GaugeConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.gauge import reference_offset
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.track import TrackModel

ROOT = Path(__file__).resolve().parents[1]


def _track(center=-0.02, yaw_deg=-0.25, curvature=0.0, rail_slabs=3):
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(0.0, 100.0), center=center,
                      yaw=np.radians(yaw_deg), curvature=curvature, rail_slabs=rail_slabs)


def _gauge(mode, **kw):
    g = GaugeConfig()
    g.reference = mode
    for k, v in kw.items():
        setattr(g, k, v)
    return g


def test_off_by_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.gauge.reference == 0 and cfg.gauge.reference_edge_margin == 1.0
    assert reference_offset(np.linspace(0.0, 100.0, 11), _track(), _gauge(0)) is None


def test_region_and_offset():
    """Mode 1: the offset (rail axis minus sensor axis) where |c| <= max_offset and X <= range, 0 and
    not ``ok`` elsewhere; mode 2: clipped to +- max_offset within the range (continuous), ``ok`` still
    marks where the sensor axis itself is the reference."""
    X = np.linspace(0.0, 150.0, 1501)
    tr = _track()
    c = tr.center_y(X)
    ok, c1 = reference_offset(X, tr, _gauge(1, reference_range=60.0, reference_max_offset=0.2))
    want = (X <= 60.0) & (np.abs(c) <= 0.2)
    assert np.array_equal(ok, want)
    assert np.allclose(c1[want], c[want]) and np.all(c1[~want] == 0.0)
    ok2, c2 = reference_offset(X, tr, _gauge(2, reference_range=250.0, reference_max_offset=0.2))
    assert np.array_equal(ok2, np.abs(c) <= 0.2)
    assert np.allclose(c2, np.clip(c, -0.2, 0.2))
    assert np.max(np.abs(np.diff(c2))) < 1e-3                  # no jump where the clamp starts
    _, c3 = reference_offset(X, tr, _gauge(2, reference_range=100.0, reference_max_offset=0.2))
    assert np.all(c3[X > 100.0] == 0.0)


@pytest.mark.parametrize("track", [_track(curvature=5e-4), _track(rail_slabs=0)])
def test_not_on_a_curve_or_without_the_rail_pair(track):
    for mode in (1, 2):
        assert reference_offset(np.linspace(3.0, 60.0, 20), track, _gauge(mode)) is None


def _yawed_scene(yaw_deg, specs, seed=5):
    """The ray-cast straight tunnel (track axis on y = 0 of the tunnel) seen by a sensor yawed by
    ``yaw_deg`` against the rails: the rails run at +yaw_deg in the sensor frame (c(X) > 0)."""
    frame, _, _ = synthetic_tunnel_frame(axis_y=0.0, rng=np.random.default_rng(seed), specs=specs)
    t = np.radians(yaw_deg)
    R = np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])
    return Frame(xyz=(frame.xyz.astype(np.float64) @ R.T).astype(np.float32), intensity=frame.intensity)


def _run(frame, mode, n=6, **gauge):
    cfg = DetectorConfig()
    cfg.gauge.reference = mode
    cfg.gauge.reference_max_offset = 0.3
    for k, v in gauge.items():
        setattr(cfg.gauge, k, v)
    det = Detector(cfg)
    return [det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k)) for k in range(n)]


@pytest.mark.synthetic
def test_inside_from_the_sensor_axis_only():
    """Sensor yawed 0.5 deg (the rail axis 0.26 m left of the sensor axis at 30 m): a 0.5 x 0.6 x 1.0 m
    box at 30 m whose inner face is 0.2 m inside the envelope measured from the sensor axis and 0.06 m
    outside the one from the rails. Rails: advisory; the sensor-axis reference (1 and 2): STOP, at the
    right distance, reported with its lateral from the rails."""
    box = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=-1.41)
    frame = _yawed_scene(0.5, [box])
    off = _run(frame, 0)
    assert not any(r.obstacle for r in off) and off[-1].warning
    lat_rail = off[-1].warnings[0].lateral
    for mode in (1, 2):
        res = _run(frame, mode)
        assert res[-1].obstacle, (mode, [(c.distance, c.lateral, c.zone, c.reason) for c in res[-1].candidates])
        d = res[-1].detections[0]
        assert abs(d.distance - 30.0) < 0.6
        assert abs(d.lateral - lat_rail) < 0.05                 # the reported lateral: from the rails
    for mode in (1, 2):
        assert not any(r.obstacle or r.warning for r in _run(_yawed_scene(0.5, []), mode))


@pytest.mark.synthetic
def test_not_a_union():
    """The other side (the trade-off): a box whose inner face is 0.2 m inside the envelope measured from
    the rails and 0.06 m outside the one from the sensor axis STOPs with the rails and is advisory with
    the sensor-axis reference: the organizers' 'outside' objects stay outside, an object inside the
    rails' envelope near its edge is reported later (here: advisory at 30 m)."""
    box = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=1.15)
    frame = _yawed_scene(0.5, [box])
    assert _run(frame, 0)[-1].obstacle
    for mode in (1, 2):
        res = _run(frame, mode)
        assert not any(r.obstacle for r in res) and res[-1].warning


def test_edge_margin_scale():
    """``reference_edge_margin`` 0: where the sensor axis is the reference the strict test has no
    axis-uncertainty margin (the sensor axis is exact). Rail axis 0.21 m right of the sensor axis at
    60 m: a return 0.05 m inside the sensor-axis envelope's edge (0.16 m outside the rails' one) is
    strict only without the margin (0.09 m at 60 m); one 0.15 m inside the rails' edge on the other
    side (0.06 m outside the sensor-axis one) is strict with the rails only; one 0.10 m beyond the
    rails' advisory corridor (1.40 m) is no candidate in any mode: the candidate set is the rails'."""
    tr = _track(center=0.0, yaw_deg=-0.2)
    X = np.array([60.0, 60.0, 60.0])
    c = float(tr.center_y(np.array([60.0]))[0])
    y = np.array([1.00, -0.90 + c, 1.50 + c])
    z = tr.rail_z(X) + 1.0
    xyz = np.stack([X, y, z], axis=1).astype(np.float32)
    got = {}
    for mode, scale in ((0, 1.0), (1, 1.0), (1, 0.0), (2, 0.0)):
        cfg = DetectorConfig()
        cfg.gauge.reference, cfg.gauge.reference_edge_margin = mode, scale
        det = Detector(cfg)
        det.track = tr
        cand = det._corridor(xyz, np.zeros(3, np.float32))[0]
        got[(mode, scale)] = dict(zip(cand.idx.tolist(), cand.in_gauge.tolist()))
    assert got[(0, 1.0)] == {0: False, 1: True}                # the rails: the second point is inside
    assert got[(1, 1.0)] == {0: False, 1: False}
    assert got[(1, 0.0)] == {0: True, 1: False}
    assert got[(2, 0.0)] == {0: True, 1: False}


@pytest.mark.synthetic
def test_accumulated_points_keep_their_position():
    """The accumulation buffer holds the reference coordinate: merged points are placed back with the
    offset removed, so a centred box approached at 10 m/s from 55 m (merged beyond 40 m) has the same
    width and lateral with the reference as without it."""
    out = {}
    for mode in (0, 1):
        cfg = DetectorConfig()
        cfg.gauge.reference = mode
        det = Detector(cfg)
        res = None
        for k in range(6):
            spec = ObstacleSpec(kind="box", size=(0.5, 0.8, 1.0), distance=55.0 - 1.0 * k, lateral=0.0)
            frame = _yawed_scene(0.25, [spec], seed=k)
            res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k), ego_speed=10.0)
        assert res.n_accumulated > 1
        c = min((c for c in res.candidates if abs(c.distance - 50.0) < 2.0), key=lambda c: abs(c.lateral))
        out[mode] = (float(c.size[1]), c.lateral)
    assert abs(out[1][0] - out[0][0]) < 0.05 and abs(out[1][1] - out[0][1]) < 0.05
