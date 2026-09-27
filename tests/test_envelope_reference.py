"""The frame the envelope is measured from (``gauge.reference``, 27.09, P1 edge objects; on by default
since 27.09: mode 2, 60 m, 0.2 m, ``reference_along_rails``).

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


def test_shipped_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        g = cfg.gauge
        assert g.reference == 3 and g.reference_edge_margin == 1.0     # the union (judges' review of 27.09)
        assert (g.reference_range, g.reference_max_offset, g.reference_along_rails) == (60.0, 0.2, True)
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
        cfg.gauge.reference_max_offset = 0.3                     # the 0.21 m offset is beyond the shipped 0.2
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
        cfg.gauge.reference_max_offset = 0.3                     # 0.22 m at 50 m: beyond the shipped 0.2
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


def _edge_line(x0: float, length: float, lateral: float) -> ObstacleSpec:
    """A 30-40 m line along the corridor edge (a hose, cable or pipe), 8 x 10 cm, 0.15 m above the
    rail head (as ``tests/test_edge_axis.py``)."""
    return ObstacleSpec(kind="box", size=(length, 0.08, 0.10), distance=x0, lateral=lateral,
                        base_z=-1.5 + 0.18 + 0.15)


@pytest.mark.synthetic
def test_does_not_drop_an_object_touching_an_edge_line():
    """The safety review's scene of the union (26.09) with the reference: the rail axis 0.25 m left of
    the sensor axis, a 0.5 m box 0.85 m right of the rails approached from 32 to 8 m, touching a 30 m
    line 1.20 m right of them (0.95 m from the sensor axis: inside the envelope measured from it). The
    oversize split's part inside the reference envelope takes the line in and grows past 3 m; it falls
    back to the part inside the rails' envelope (``Candidates.in_rail``), so the box keeps its STOPs
    (19 -> 7 without it; with it every STOP of the rails and one frame earlier)."""
    stops = {}
    for mode in (0, 1, 2, None):                                  # None: the shipped defaults (2, 0.2 m)
        cfg = DetectorConfig()
        if mode is not None:
            cfg.gauge.reference = mode
            cfg.gauge.reference_max_offset = 0.3                 # the 0.25 m offset: mode 1 is the rails at 0.2
        det = Detector(cfg)
        out = []
        for k in range(25):
            d = 32.0 - k
            specs = [ObstacleSpec(kind="box", size=(0.5, 0.5, 0.6), distance=d, lateral=-0.85, base_z=-1.5),
                     _edge_line(max(d - 20.0, 3.0), 30.0, -1.20)]
            fr, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(k % 5), specs=specs, axis_y=0.25)
            out.append(det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k)).obstacle)
        stops[mode] = [k for k, o in enumerate(out) if o]
    assert len(stops[0]) >= 15
    for mode in (1, 2, None):                                    # 19 -> 7 STOP frames without the fallback
        assert set(stops[0]) <= set(stops[mode]), str(stops)


def test_along_track_rules_read_the_rails():
    """``gauge.reference_along_rails``: a 2.5 m long, 0.6 m wide, 0.4 m tall structure along the track
    1.1 m from the rails (0.9 m from the reference axis, 0.2 m to its left) is the 'edge' signature
    (duct / bench fragment along the corridor edge) when the along-track rules read the rails; read
    from the reference it is an obstacle inside the envelope. A compact object at the same place is
    an obstacle either way (the edge rule needs the elongation)."""
    from resense.clustering import find_clusters
    from resense.config import ClusterConfig

    def cluster_of(length, along):
        X, Y, Z = np.meshgrid(np.arange(30.0, 30.0 + length, 0.08), np.arange(0.8, 1.41, 0.08),
                              np.arange(0.1, 0.51, 0.08), indexing="ij")
        xyz = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1).astype(np.float32)
        dy_rail = xyz[:, 1].astype(np.float64)
        dy = dy_rail - 0.2
        h = xyz[:, 2].astype(np.float64)
        g = GaugeConfig()
        g.reference, g.reference_along_rails = 2, along
        in_gauge = np.abs(dy) <= 1.05
        out = find_clusters(xyz, np.zeros(len(xyz), np.float32), dy, h, in_gauge, ClusterConfig(),
                            gauge=g, dy_report=dy_rail)
        assert len(out) == 1
        return out[0]

    long_ref, long_rail = cluster_of(2.5, False), cluster_of(2.5, True)
    assert long_ref.zone == "gauge" and long_ref.reason == ""
    assert long_rail.zone == "warning" and long_rail.reason == "edge"
    assert abs(long_rail.lateral - 1.1) < 0.05                   # reported from the rails either way
    for along in (False, True):
        c = cluster_of(0.4, along)
        assert c.zone == "gauge" and c.reason == ""


def test_union_never_narrows_the_rails_envelope():
    """``gauge.reference`` 3 (27.09, after the judges' review): a point takes the sensor-axis lateral
    only where that is nearer the centre, so a point inside the rails' envelope on either side stays
    inside whatever the sign of the rail-to-sensor offset, and a point inside the sensor-axis envelope
    only (the organizers' placement frame) is inside too."""
    from resense.gauge import union_shift
    half = 1.05
    for c in (0.2, -0.2):
        dy = np.array([-0.9, -0.5, 0.0, 0.5, 0.9])            # inside the rails' envelope, both sides
        u = dy + union_shift(dy, np.full(dy.size, c))
        assert np.all(np.abs(u) <= np.abs(dy) + 1e-12)
        assert np.all(np.abs(u) <= half)
        # just outside the rails' envelope on the side the sensor axis lies: inside by the union
        side = -np.sign(c)
        out = np.array([side * (half + 0.15)])
        assert abs(float((out + union_shift(out, np.array([c])))[0])) <= half
        # outside on the other side: the union does not pull it in
        other = np.array([-side * (half + 0.15)])
        assert float((other + union_shift(other, np.array([c])))[0]) == float(other[0])


@pytest.mark.synthetic
@pytest.mark.parametrize("yaw", [0.5, -0.5])
def test_union_stops_edge_boxes_on_both_sides(yaw):
    """The side-symmetric end-to-end check of the union (27.09, the judges' review): with the sensor
    yawed either way, a box whose inner face is 0.2 m inside the rails' envelope on the side the
    sensor axis leaves (the side modes 1 / 2 give up) STOPs as it does from the rails, and a box 0.2 m
    inside the sensor-axis envelope only (the placement frame's side) STOPs too."""
    s = np.sign(yaw)
    lose = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=1.15 * s)
    gain = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=-1.41 * s)
    lose_f, gain_f = _yawed_scene(yaw, [lose]), _yawed_scene(yaw, [gain])
    assert _run(lose_f, 0)[-1].obstacle and not _run(lose_f, 2)[-1].obstacle
    assert _run(lose_f, 3)[-1].obstacle
    assert _run(gain_f, 3)[-1].obstacle
    assert not any(r.obstacle or r.warning for r in _run(_yawed_scene(yaw, []), 3))
