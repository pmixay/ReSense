"""Unit tests that run without the dataset (synthetic tunnel via Open3D ray casting)."""
import numpy as np
import pytest

from resense import Detector, DetectorConfig
from resense.config import SensorConfig
from resense.frame import axis_matrix, frame_from_compact, sensor_to_vehicle
from resense.gauge import point_in_polygon, widened_profile
from resense.pointcloud import COMPACT_DTYPE, structured_to_compact
from resense.sensor import expected_points, ray_directions
from resense.track import TrackModel

o3d = pytest.importorskip("open3d", reason="open3d needed for the synthetic tunnel")
from resense.synthetic import ObstacleSpec, inject_obstacles, synthetic_tunnel_frame  # noqa: E402


def test_axis_matrix_hesai_mapping():
    R = axis_matrix(SensorConfig())
    p = np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]])  # +x, -y, +z sensor
    v = p @ R.T
    assert np.allclose(v[0], [0, 1, 0])   # sensor +x -> left
    assert np.allclose(v[1], [1, 0, 0])   # sensor -y -> forward
    assert np.allclose(v[2], [0, 0, 1])   # sensor +z -> up


def test_axis_matrix_rejects_left_handed():
    with pytest.raises(ValueError):
        axis_matrix(SensorConfig(forward="-y", left="-x", up="+z"))


def test_structured_to_compact_drops_zero_points():
    arr = np.zeros(3, dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"), ("intensity", "f4"), ("ring", "u2")])
    arr["x"] = [1.0, 0.0, np.nan]
    arr["y"] = [2.0, 0.0, 1.0]
    out = structured_to_compact(arr)
    assert out.dtype == COMPACT_DTYPE and out.size == 1


def test_point_in_polygon_rectangle():
    poly = [(-1, 0), (1, 0), (1, 2), (-1, 2)]
    px = np.array([0.0, 2.0, -0.5, 0.0])
    py = np.array([1.0, 1.0, 1.9, 3.0])
    assert point_in_polygon(px, py, poly).tolist() == [True, False, True, False]


def test_widened_profile():
    cfg = DetectorConfig().gauge
    wide = widened_profile(cfg, 0.5)
    prof = np.asarray(cfg.profile)
    assert wide[:, 0].max() == pytest.approx(prof[:, 0].max() + 0.5)
    inner = np.abs(prof[:, 0]) < 0.99 * np.abs(prof[:, 0]).max()
    assert np.allclose(wide[inner, 0], prof[inner, 0])   # low inner zone unchanged


def test_expected_points_decreases_with_range():
    n100 = expected_points(100.0, 0.5, 0.5)
    n200 = expected_points(200.0, 0.5, 0.5)
    assert n100 > n200 > 0
    assert 4 < n100 < 12   # ~6.6 for a 0.5x0.5 target at 100 m


def test_ray_grid_size():
    assert ray_directions().shape == (1001 * 128, 3)


def test_track_model_extrapolates_linearly():
    m = TrackModel(floor_coef=np.array([1e-3, 0.0, -1.5]), floor_range=(0.0, 50.0), center=0.0, yaw=0.0, curvature=0.0)
    z50, z100 = m.floor_z(50.0), m.floor_z(100.0)
    slope = 2 * 1e-3 * 50.0
    assert z100 == pytest.approx(z50 + slope * 50.0)


@pytest.fixture(scope="module")
def tunnel():
    frame, labels, gt = synthetic_tunnel_frame(rng=np.random.default_rng(1))
    return frame, labels, gt


def test_synthetic_tunnel_is_clear(tunnel):
    frame, _, gt = tunnel
    det = Detector(DetectorConfig())
    res = None
    for _ in range(4):
        res = det.process(frame)
    assert not res.obstacle, [d.to_dict() for d in res.detections]
    assert abs(res.track.center - gt.center) < 0.15
    assert abs(res.track.floor_z(10.0) - gt.floor_z(10.0)) < 0.25


@pytest.mark.parametrize("distance,kind,size", [(30.0, "box", (0.6, 0.6, 0.6)), (80.0, "box", (0.6, 0.6, 0.6)),
                                                (150.0, "person", (0.4, 0.5, 1.7))])
def test_injected_box_is_detected(tunnel, distance, kind, size):
    frame, _, gt = tunnel
    spec = ObstacleSpec(kind=kind, size=size, distance=distance, lateral=0.0, reflectivity=60)
    inj = inject_obstacles(frame, gt, [spec], rng=np.random.default_rng(2))
    assert inj.n_added[0] > 0
    det = Detector(DetectorConfig())
    res = None
    for _ in range(4):
        res = det.process(inj.frame)
    assert res.obstacle, "%s at %.0f m not detected" % (kind, distance)
    assert abs(res.nearest_distance - distance) < max(2.0, 0.03 * distance)


def test_object_outside_gauge_is_not_an_obstacle(tunnel):
    frame, _, gt = tunnel
    spec = ObstacleSpec(kind="person", size=(0.4, 0.5, 1.7), distance=40.0, lateral=2.3, reflectivity=60)
    inj = inject_obstacles(frame, gt, [spec], rng=np.random.default_rng(3))
    det = Detector(DetectorConfig())
    res = None
    for _ in range(4):
        res = det.process(inj.frame)
    assert not res.obstacle


def test_injection_occludes_background(tunnel):
    frame, _, gt = tunnel
    spec = ObstacleSpec(kind="box", size=(1.0, 1.0, 1.0), distance=20.0, lateral=0.0)
    inj = inject_obstacles(frame, gt, [spec], rng=np.random.default_rng(4))
    # rays that hit the box no longer reach the floor: the floor is in shadow beyond ~26 m
    X, Y, Z = inj.frame.xyz[:, 0], inj.frame.xyz[:, 1], inj.frame.xyz[:, 2]
    shadow = (X > 27.0) & (X < 60.0) & (np.abs(Y - gt.center) < 0.3) & (Z < gt.floor_z(40.0) + 0.05)
    assert shadow.sum() == 0
    lit = (X > 27.0) & (X < 60.0) & (np.abs(Y - gt.center - 1.5) < 0.3) & (Z < gt.floor_z(40.0) + 0.05)
    assert lit.sum() > 50


def test_frame_from_compact_range_filter():
    arr = np.zeros(2, dtype=COMPACT_DTYPE)
    arr["y"] = [-1.0, -50.0]
    fr = frame_from_compact(arr, SensorConfig(min_range=2.5))
    assert fr.n == 1 and fr.xyz[0, 0] == pytest.approx(50.0)
    assert np.allclose(sensor_to_vehicle(np.array([[0.0, -3.0, 0.0]], np.float32), SensorConfig()), [[3.0, 0.0, 0.0]])
