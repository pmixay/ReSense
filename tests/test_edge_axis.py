"""The envelope measured from the sensor axis as well as from the rails (``gauge.axis_union``, 26.09;
docs/evidence/results/p3_edge_axis_2026-09-26.json).

The organizers place their edge-test objects from the sensor's X axis, which in
``cloud_with_fake_obj`` runs at -0.24 deg to the rails; the detector measures the envelope from the
rails. With the option on, a point is inside when it is inside either envelope, only in the near field
on straight track where the two axes are within ``axis_union_max_offset`` of each other.
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.config import DetectorConfig, GaugeConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.gauge import axis_union_coordinates, axis_union_offset, axis_union_strict, point_in_polygon
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.track import TrackModel


def _track(center=0.0, yaw_deg=0.3, curvature=0.0, rail_slabs=3):
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(0.0, 100.0), center=center,
                      yaw=np.radians(yaw_deg), curvature=curvature, rail_slabs=rail_slabs)


def _gauge(mode):
    g = GaugeConfig()
    g.axis_union = mode
    return g


def test_off_by_default():
    assert DetectorConfig().gauge.axis_union == 0
    X = np.linspace(3.0, 60.0, 50)
    assert axis_union_offset(X, _track(), GaugeConfig()) is None
    dy = np.linspace(-2.0, 2.0, 50)
    assert axis_union_coordinates(X, dy, _track(), GaugeConfig()) is dy


@pytest.mark.parametrize("track", [_track(curvature=5e-4), _track(rail_slabs=0)])
def test_not_on_a_curve_or_without_the_rail_pair(track):
    X = np.linspace(3.0, 60.0, 50)
    assert axis_union_offset(X, track, _gauge(2)) is None


def test_union_coordinate_is_the_union_and_continuous():
    """Candidate B: |dy'| <= W exactly when inside the rail or the sensor-axis envelope; monotone and
    continuous in dy; the rail coordinate on the other side and beyond the region."""
    g = _gauge(2)
    tr = _track(center=0.02, yaw_deg=0.3)           # rail axis left of the sensor axis: c(X) > 0
    W = 1.05
    for x in (10.0, 30.0, 49.0):
        dy = np.linspace(-2.5, 2.5, 5001)
        X = np.full(dy.size, x)
        c = float(tr.center_y(np.array([x]))[0])
        out = axis_union_coordinates(X, dy, tr, g)
        assert np.all(np.diff(out) > 0)                          # monotone
        assert np.max(np.abs(np.diff(out))) < 2 * (dy[1] - dy[0])  # continuous
        union = (np.abs(dy) <= W + 1e-9) | (np.abs(dy + c) <= W + 1e-9)
        assert np.array_equal(np.abs(out) <= W + 1e-9, union)
        assert np.array_equal(out[dy >= 0], dy[dy >= 0])        # the side where the axis envelope is narrower
        far = dy < -(W + c)
        assert np.allclose(out[far], dy[far] + c)               # beyond the union edge: from the sensor axis
    X = np.array([60.0, 60.0])                                  # beyond axis_union_range
    dy = np.array([-1.2, 1.2])
    assert np.array_equal(axis_union_coordinates(X, dy, tr, g), dy)


def test_union_strict_membership():
    """Candidate A: the strict membership measured from the sensor axis within the region only."""
    g = _gauge(1)
    tr = _track(center=0.0, yaw_deg=0.3)
    X = np.array([30.0, 30.0, 30.0, 70.0])
    c = float(tr.center_y(np.array([30.0]))[0])                 # 0.157 m
    dy = np.array([-0.95 - c, 0.95 - c, -1.3 - c, -0.95 - 0.37])
    h = np.full(4, 1.0)
    ax = axis_union_strict(X, dy, h, tr, g)
    assert ax.tolist() == [True, True, False, False]
    assert not point_in_polygon(dy[:1], h[:1], g.profile)[0]    # outside the rail envelope


FLOOR_Z = -1.5


def _yawed_scene(yaw_deg, specs, seed=5):
    """The ray-cast straight tunnel (track axis on the sensor axis) seen by a sensor yawed by
    ``yaw_deg`` against the rails: the rails run at +yaw_deg in the sensor frame."""
    frame, _, _ = synthetic_tunnel_frame(axis_y=0.0, rng=np.random.default_rng(seed), specs=specs)
    t = np.radians(yaw_deg)
    R = np.array([[np.cos(t), -np.sin(t), 0.0], [np.sin(t), np.cos(t), 0.0], [0.0, 0.0, 1.0]])
    return Frame(xyz=(frame.xyz.astype(np.float64) @ R.T).astype(np.float32), intensity=frame.intensity)


def _run(frame, mode, n=6):
    cfg = DetectorConfig()
    cfg.gauge.axis_union = mode
    det = Detector(cfg)
    return [det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k)) for k in range(n)]


@pytest.mark.synthetic
def test_object_at_the_axis_referenced_edge():
    """Sensor yawed 0.5 deg against straight rails (0.26 m at 30 m): a 0.5 x 0.6 x 1.0 m box at 30 m
    whose inner face is 0.2 m inside the envelope measured from the sensor axis and ~0.06 m outside
    the one measured from the rails. Rails only: advisory; the union (A and B): STOP. The empty
    tunnel stays clear."""
    box = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=-1.41)
    frame = _yawed_scene(0.5, [box])
    off = _run(frame, 0)
    assert not any(r.obstacle for r in off) and off[-1].warning
    for mode in (1, 2):
        res = _run(frame, mode)
        assert res[-1].obstacle, (mode, [(c.distance, c.lateral, c.zone, c.reason) for c in res[-1].candidates])
        assert abs(res[-1].detections[0].distance - 30.0) < 0.6
    empty = _yawed_scene(0.5, [])
    for mode in (1, 2):
        assert not any(r.obstacle or r.warning for r in _run(empty, mode))


@pytest.mark.synthetic
def test_not_where_the_axes_diverge():
    """Yawed 1.0 deg (0.5 m apart at 30 m, beyond axis_union_max_offset): the same placement from the
    sensor axis stays advisory with the union on."""
    box = ObstacleSpec(kind="box", size=(0.5, 0.6, 1.0), distance=30.0, lateral=-1.67)
    frame = _yawed_scene(1.0, [box])
    for mode in (1, 2):
        res = _run(frame, mode)
        assert not any(r.obstacle for r in res) and res[-1].warning
