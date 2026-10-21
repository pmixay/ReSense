"""K2 union (21.10, ``track.axis_joint_union``): on a curve frame the joint rail + boundary shape is a second gauge that
can only add obstacles. The track model every stage reads stays the estimate without the joint fit. Off by default."""

from dataclasses import replace
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig, TrackConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.track import TrackModel, estimate_track, rotate_track_model
from tests.test_wall_drift import _entry_scene

ROOT = Path(__file__).resolve().parents[1]
OFF = dict(axis_joint_fit=False, axis_joint_range=True, axis_joint_min_curvature=0.0, axis_joint_reach_cap=False,
           axis_joint_reach_dual=0.0, axis_joint_union=False, walls_smoothing_distance=0.0)
UNION = dict(OFF, axis_joint_fit=True, axis_joint_range=False, axis_joint_min_curvature=1e-4, axis_joint_union=True)
_STATE = ("center", "yaw", "curvature", "curv_step", "curv_knot", "floor_range", "rail_offset", "axis_valid",
          "axis_valid_both", "axis_valid_bent", "axis_sides", "wall_quality", "far_support_run", "disagree_left",
          "axis_straight", "wall_drift", "floor_verified", "age", "rail_score", "rail_slabs")


def _same(a: TrackModel, b: TrackModel) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in _STATE) and np.array_equal(a.floor_coef, b.floor_coef)


def _run_track(xyz, kw, n=8):
    cfg, out, m = TrackConfig(**kw), [], None
    for _ in range(n):
        m = estimate_track(xyz, cfg, prev=m)
        out.append(m)
    return out


def _person(yt, x0, lat=0.0, n=600, seed=1):
    """A 0.5 x 0.5 m box from the rail head (-1.15 m) to 0.6 m on the track at x0 (+ lat)."""
    r = np.random.default_rng(seed)
    X = x0 + 0.5 * r.random(n)
    return np.stack([X, yt(x0) + lat + r.uniform(-0.25, 0.25, n), r.uniform(-1.15, 0.6, n)], 1).astype(np.float32)


def _detect(kw, xyz, n=12):
    cfg = DetectorConfig()
    det = Detector(replace(cfg, track=replace(cfg.track, **kw)))
    return [det.process(Frame(xyz=xyz, intensity=np.full(len(xyz), 30.0, np.float32), stamp=0.1 * k))
            for k in range(n)]


def _rows(results, track=True):
    """Every decision-relevant field of a run, frame by frame (no timing)."""
    return [(r.obstacle, r.warning, r.nearest_distance, r.clear_distance, r.track.to_dict() if track else None,
             [(d.id, round(d.distance, 6), round(d.lateral, 6), d.zone, d.reason, d.kind) for d in r.detections],
             [(d.id, round(d.distance, 6), round(d.lateral, 6), d.zone, d.reason, d.kind) for d in r.warnings])
            for r in results]


def test_union_default_off_in_code_and_both_parameter_files():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.track.axis_joint_union is False


def test_union_output_is_the_estimate_without_the_joint_fit_and_the_curve_rides_along():
    """On the curve entry every output model equals the estimator without the joint fit, field for field and frame by
    frame (nothing of the joint shape feeds back, review R5's feedback path included); the joint shape is carried as
    ``curve`` (not serialised), much nearer the track at 120 m than the output, trusted to its walls' reach."""
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    off, un = _run_track(xyz, OFF), _run_track(xyz, UNION)
    for a, b in zip(off, un):
        assert _same(a, b) and a.to_dict() == b.to_dict()
    cv = un[-1].curve
    assert cv is not None and cv.curve is None and cv.base is None
    e_curve = abs(float(cv.center_y(120.0)) - float(yt(120.0)))
    e_base = abs(float(un[-1].center_y(120.0)) - float(yt(120.0)))
    assert e_curve < 0.5 < e_base, (e_curve, e_base)
    assert 60.0 < cv.axis_valid <= 160.0 + TrackConfig().axis_valid_margin
    assert "curve" not in un[-1].to_dict()


def test_union_straight_track_has_no_curve():
    xyz, _ = _entry_scene(j=0.0)
    for a, b in zip(_run_track(xyz, OFF), _run_track(xyz, UNION)):
        assert _same(a, b) and b.curve is None


def test_union_rotation_keeps_the_curve_and_its_range():
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    m = _run_track(xyz, UNION)[-1]
    r = rotate_track_model(m, np.eye(3))
    assert r.curve is not None and r.curve.axis_valid == m.curve.axis_valid
    X = np.array([20.0, 80.0, 140.0])
    assert np.allclose(r.curve.center_y(X), m.curve.center_y(X), atol=1e-6)


def test_union_detector_adds_the_person_on_the_curve_and_changes_nothing_else():
    """A person on the track at 130 m of the curve entry: the base axis is ~1.9 m off the track there and no gauge
    obstacle is reported (positive control); with the union it is a STOP at its distance. A person at 60 m, inside the
    base gauge, gives the same frames with the switch on and off; so does the empty straight tunnel."""
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    far = np.concatenate([xyz, _person(yt, 130.0)])
    off, un = _detect(OFF, far), _detect(UNION, far)
    assert not any(r.obstacle for r in off)
    assert un[-1].obstacle and abs(un[-1].detections[0].distance - 130.0) < 2.0
    near = np.concatenate([xyz, _person(yt, 60.0)])
    a, b = _detect(OFF, near), _detect(UNION, near)
    assert a[-1].obstacle and _rows(a, track=False) == _rows(b, track=False)
    # the published model follows the curve on its frames and says so; elsewhere it is the track model itself
    assert un[-1].track.joint_used is True and un[-1].track.to_dict()["joint_used"] is True
    assert abs(float(un[-1].track.center_y(120.0)) - float(yt(120.0))) < 0.5
    xs, _ = _entry_scene(j=0.0)
    assert _rows(_detect(OFF, xs)) == _rows(_detect(UNION, xs))


def test_union_never_replaces_a_base_obstacle():
    """Unit: a curve obstacle overlapping a base obstacle is not added; one overlapping only a base advisory cluster
    takes its place; one overlapping nothing is added."""
    from tests.test_k1_k2_axis import _cluster
    cfg = DetectorConfig()
    det = Detector(replace(cfg, track=replace(cfg.track, **UNION)))
    base = [_cluster(50.0, 50.5, -0.3, 0.3), _cluster(90.0, 90.5, 1.0, 1.5, "warning", "")]
    curve = [_cluster(50.1, 50.6, -0.2, 0.4), _cluster(90.0, 90.5, 1.0, 1.5), _cluster(120.0, 120.5, 0.0, 0.5),
             _cluster(140.0, 140.5, 0.0, 0.5, "warning", "beyond_axis")]
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                           curvature=0.0, curve=TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]),
                                                           floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                                                           curvature=2e-4, axis_valid=150.0))
    det._corridor = lambda xyz, inten: (np.zeros(1), None, None, None, (150.0, 150.0, 100.0))
    det._cluster = lambda *a, **k: curve
    out = det._curve_clusters(np.zeros((1, 3), np.float32), np.zeros(1, np.float32), list(base))
    assert out[0] is base[0]
    assert [c.distance for c in out] == [50.0, 90.0, 120.0]
    assert out[1] is curve[1] and out[2] is curve[2]
