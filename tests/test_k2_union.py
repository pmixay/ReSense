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


def test_union_curve_range_is_held_over_a_hidden_boundary_and_decays():
    """A frame whose far boundaries are hidden (every return beyond 70 m removed) keeps the previous curve range less
    20 m per period instead of dropping to the shortened reach; the full scene restores the reach."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    cfg, m = TrackConfig(**UNION), None
    for _ in range(8):
        m = estimate_track(xyz, cfg, prev=m)
    before = m.curve.axis_valid
    cut = xyz[xyz[:, 0] < 70.0]
    hidden = estimate_track(cut, cfg, prev=m)
    fresh = estimate_track(cut, cfg, prev=None)                     # positive control: what the cut alone supports
    for _ in range(7):
        fresh = estimate_track(cut, cfg, prev=fresh)
    assert fresh.curve is None or fresh.curve.axis_valid < before - 20.0
    assert hidden.curve is not None and hidden.curve.axis_valid == before - 20.0
    again = estimate_track(xyz, cfg, prev=hidden)
    assert again.curve is not None and again.curve.axis_valid >= before - 20.0


def test_union_missing_bed_fit_adds_nothing_and_keeps_the_base_hold():
    """Review R5 (20.10): a frame without a bed fit (only returns high on the walls) must not release anything. With
    the union the output is exactly the estimator without the joint fit (which holds its prior) and no curve is
    carried, so the second gauge adds nothing on that frame; the next full frame brings the curve back."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    off, un = _run_track(xyz, OFF), _run_track(xyz, UNION)
    high = xyz[xyz[:, 2] > 1.0]
    a = estimate_track(high, TrackConfig(**OFF), prev=off[-1])
    b = estimate_track(high, TrackConfig(**UNION), prev=un[-1])
    assert _same(a, b) and _same(a, off[-1]) and b.curve is None       # the hold is the base estimator's own
    c = estimate_track(xyz, TrackConfig(**UNION), prev=b)
    assert c.curve is not None


def test_union_curve_seen_track_is_released_when_the_opinion_rises(tmp_path):
    """Revision 1 (marked platform object 23, frames 106-112): a track that matched a cluster of the curve gauge is
    asked again every withheld frame, so an earlier doubtful onset cannot withhold it past the frame where the
    opinion rises; the same track without a curve cluster keeps the sticky rule (positive control)."""
    from resense.config import TrackingConfig
    from resense.tracking import Tracker
    from tests.test_track_opinion import _cl, _stump
    m = _stump(tmp_path, "rise.json", 75.5, 5.0, -5.0)          # p low beyond 75.5 m, high within
    kw = dict(doubt_model=m, doubt_extra_hits=6, doubt_near=30.0, doubt_sticky=True)

    def run(curve):
        tr, out = Tracker(TrackingConfig(**kw)), []
        for k in range(14):
            c = _cl(80.0 - k)
            if curve:
                c.curve = True
            tr.update([c], ego_shift=1.0, frame_dt=0.1)
            t = [t for t in tr.tracks if t.id == 1][0]
            out.append((t.reported, t.zone))
        return out
    sticky, loose = run(False), run(True)
    first = next(i for i, (r, z) in enumerate(loose) if r)
    first = next(i for i in range(first, 14) if sticky[i][0] and sticky[i][1] == "warning")
    assert sticky[first + 1] == (True, "warning")                      # sticky: still withheld
    assert loose[first] == (True, "warning") and loose[first + 1] == (True, "gauge")


def test_union_added_cluster_keeps_the_base_observation_and_lateral():
    """Revision 1: an added curve obstacle that replaces a base advisory cluster carries that cluster's lateral and
    opinion record; one that replaces nothing carries its own record with the base lateral of its points."""
    from resense.opinion import observation
    from tests.test_k1_k2_axis import _cluster
    cfg = DetectorConfig()
    det = Detector(replace(cfg, track=replace(cfg.track, **UNION)))
    adv = _cluster(90.0, 90.5, 1.0, 1.5, "warning", "beyond_axis")
    adv.lateral = 1.25
    lone = _cluster(120.0, 120.5, 0.0, 0.5)
    lone.points_idx = np.array([0, 1, -1])
    curve = [_cluster(90.0, 90.5, 1.0, 1.5), lone]
    curve[0].lateral = 0.4
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                           curvature=0.0, curve=TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]),
                                                           floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                                                           curvature=2e-4, axis_valid=150.0))
    det._dy_rail = np.array([1.9, 2.1, 0.0])
    det._corridor = lambda xyz, inten: (np.zeros(1), None, None, None, (150.0, 150.0, 100.0))
    det._cluster = lambda *a, **k: curve
    out = det._curve_clusters(np.zeros((3, 3), np.float32), np.zeros(3, np.float32), [adv])
    assert out[0] is curve[0] and out[0].lateral == 1.25 and out[0].obs_as == observation(adv) and out[0].curve
    assert out[1] is lone and abs(lone.lateral - 2.0) < 1e-9 and lone.obs_as[1] == lone.lateral


def test_union_overlap_is_tested_in_the_vehicle_frame():
    """Revision 1: the laterals of the two gauges are measured from different axes (1.8 m apart at 60 m on the
    roundT_doubleT curve); the same box with laterals 0.0 (base) and 1.8 (curve) is one object, not two."""
    from tests.test_k1_k2_axis import _cluster
    from resense.detector import _overlap, _overlap_xy
    a, b = _cluster(60.0, 60.5, -0.3, 0.3), _cluster(60.0, 60.5, -0.3, 0.3)
    a.lateral, b.lateral = 0.0, 1.8
    assert _overlap_xy(a, b) and not _overlap(a, b)                   # positive control: the lateral test misses it
    c = _cluster(60.0, 60.5, 1.0, 1.6)
    assert not _overlap_xy(a, c)


def test_union_revision2_adds_only_what_the_base_gauge_cannot_judge():
    """Revision 2 (ride false STOPs of eb8b7aa): a curve obstacle whose returns lie inside the base strict envelope
    within the base trusted range is not added (the base's verdict stands); the same object beyond the base trusted
    range, or with no return in the base envelope, is; nothing is added before ``curve.curve_from``."""
    from tests.test_k1_k2_axis import _cluster

    def run(base_in, base_valid, curve_from=0.0):
        cfg = DetectorConfig()
        det = Detector(replace(cfg, track=replace(cfg.track, **UNION)))
        k = _cluster(90.0, 90.5, 1.0, 1.5)
        k.points_idx = np.array([0, 1, 2])
        cv = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                        curvature=2e-4, axis_valid=150.0, curve_from=curve_from)
        det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                               curvature=0.0, curve=cv)
        det._base_in = np.array(base_in)
        det._corridor = lambda xyz, inten: (np.zeros(1), None, None, None, (150.0, 150.0, 100.0))
        det._cluster = lambda *a, **kw: [k]
        return det._curve_clusters(np.zeros((3, 3), np.float32), np.zeros(3, np.float32), [], base_valid)
    assert run([False, True, False], 120.0) == []                    # judged by the base gauge
    assert len(run([False, True, False], 80.0)) == 1                 # beyond the base trusted range
    assert len(run([False, False, False], 120.0)) == 1               # no return in the base envelope
    assert run([False, False, False], 120.0, curve_from=95.0) == []  # a boundary still follows the base axis there


def test_union_curve_from_is_the_base_axis_followed_reach():
    """On the curve entry the base axis is followed by a boundary to some X short of the curve's trusted range."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    m = _run_track(xyz, UNION)[-1]
    assert m.curve is not None and 0.0 < m.curve.curve_from < m.curve.axis_valid
