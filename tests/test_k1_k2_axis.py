"""K1 / K2 (19.10): the joint rail + boundary axis fit with a curvature step (track.axis_joint_fit) and the
per-distance axis smoothing (track.walls_smoothing_distance). Both are off by default; off, nothing changes."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from resense import _native
from resense.config import DetectorConfig, TrackConfig
from resense.track import RailsFit, TrackModel, estimate_track, joint_axis_fit, rotate_track_model
from tests.test_wall_drift import _entry_scene

ROOT = Path(__file__).resolve().parents[1]
JOINT = dict(axis_joint_fit=True)
# every switch of this module off (the shipped defaults have K2 variant B on since 19.10): the tests build each
# variant from this base, so they keep testing the code paths, not the current defaults
OFF = dict(axis_joint_fit=False, axis_joint_range=True, axis_joint_min_curvature=0.0, axis_joint_reach_cap=False,
           walls_smoothing_distance=0.0)


def _cfg(**kw) -> TrackConfig:
    return TrackConfig(**{**OFF, **kw})


def test_shipped_variant_b_in_code_and_both_parameter_files():
    """The captain's decision of 19.10: K2 on as variant B (v5b without K1): the joint axis shape on curves only,
    the base trusted-range policy, the reach cap; K1's per-distance smoothing off."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        t = cfg.track
        assert t.axis_joint_fit is True and t.walls_smoothing_distance == 0.0 and t.axis_joint_range is False
        assert t.axis_joint_min_curvature == pytest.approx(1e-4) and t.axis_joint_reach_cap is True   # v5b
        assert (t.axis_joint_knot, t.axis_joint_step_sigma, t.axis_joint_tolerance) == (60.0, 1e-3, 0.3)


def _model(**kw) -> TrackModel:
    kw = {"curvature": 0.0, **kw}
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0, **kw)


def test_center_y_with_a_curvature_step_and_the_native_guard():
    m = _model(curvature=1e-4, curv_step=-2e-3, curv_knot=60.0)
    assert m.bent and not _model().bent
    X = np.array([0.0, 30.0, 60.0, 90.0, 150.0])
    want = 0.5e-4 * X * X - 1e-3 * np.maximum(X - 60.0, 0.0) ** 2
    assert np.allclose(m.center_y(X), want, atol=1e-12)
    assert m.to_dict()["curv_step"] == -2e-3 and "curv_step" not in _model().to_dict()
    # a rotation by the identity keeps the shape
    r = rotate_track_model(m, np.eye(3))
    assert np.allclose(r.center_y(X), m.center_y(X), atol=1e-6) and r.curv_knot == 60.0


def _curve_obs(k=-0.0025, step=0.0, knot=60.0, sides=((2.6, 160.0), (-2.7, 45.0)), noise=0.03, seed=0):
    """Rail-pair slab midpoints at 8.3 / 17 / 25.7 m and per-side boundary bins (4 m) of a track
    y = t0 x + k x^2/2 [+ step (x - knot)^2/2]; each side at a lateral offset, seen to its reach."""
    rng = np.random.default_rng(seed)
    t0 = 0.01

    def yt(x):
        return t0 * x + 0.5 * k * x * x + 0.5 * step * np.maximum(x - knot, 0.0) ** 2
    xm = np.array([8.33, 17.0, 25.67])
    rails = RailsFit(score=0.1, center=0.0, rail_offset=0.35, n_slabs=3, tan_yaw=None, xm=xm,
                     mids=yt(xm) + rng.normal(0, 0.01, 3), wts=np.ones(3))
    bounds = {}
    for (off, reach), name in zip(sides, ("left", "right")):
        x = np.arange(8.0, reach + 1e-6, 4.0)
        bounds[name] = (x, yt(x) + off + rng.normal(0, noise, x.size))
    return rails, bounds, yt


def test_joint_fit_recovers_the_curve_from_a_too_straight_prior():
    """roundT_doubleT: the prior says straight while the track is R 400 m; the old tangent (a line through the
    slab midpoints with the prior curvature held) is the tangent at ~17 m, the joint fit is not biased."""
    rails, bounds, yt = _curve_obs()
    cfg = _cfg(**JOINT)
    j = joint_axis_fit(rails, bounds, _model(), cfg)
    assert abs(j["t"] - 0.01) < 0.003 and abs(j["k"] - (-0.0025)) < 2e-4, j
    old_t = np.polyfit(rails.xm, rails.mids, 1)[0]
    assert abs(old_t - 0.01) > 0.03                       # the bias the joint fit removes
    for x in (60.0, 100.0, 140.0):
        y = j["c"] + j["t"] * x + 0.5 * j["k"] * x * x + 0.5 * j["step"] * max(x - j["knot"], 0) ** 2
        assert abs(y - yt(x)) < 0.4, (x, y, yt(x))
    assert j["x_max"]["left"] >= 156 and j["x_max"]["right"] <= 45


def test_joint_fit_follows_a_transition_with_the_step():
    rails, bounds, yt = _curve_obs(k=0.0, step=-0.002, sides=((2.6, 140.0), (-2.6, 140.0)))
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    assert j["step"] < -0.0012, j
    for x in (80.0, 120.0):
        y = j["c"] + j["t"] * x + 0.5 * j["k"] * x * x + 0.5 * j["step"] * max(x - j["knot"], 0) ** 2
        assert abs(y - yt(x)) < 0.5, (x, y, yt(x))
    # no data beyond the knot: no step
    rails, bounds, _ = _curve_obs(k=0.0, step=-0.002, sides=((2.6, 56.0), (-2.6, 56.0)))
    assert joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))["step"] == pytest.approx(0.0, abs=1e-9)


def test_structure_edge_starts_a_new_segment_and_converging_walls_are_dropped():
    rails, bounds, yt = _curve_obs(k=0.0, sides=((2.6, 120.0), (-2.6, 120.0)), noise=0.01)
    x, y = bounds["left"]
    y = y + np.where(x > 30, -0.6, 0.0)                    # a niche / gate edge at 30 m
    bounds["left"] = (x, y)
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    assert abs(j["k"]) < 5e-5 and abs(j["step"]) < 1e-4, j
    # a platform wall converging 0.04 per metre inside the rail range does not turn the tangent
    rails, bounds, _ = _curve_obs(k=0.0, sides=((2.6, 120.0), (-2.6, 120.0)), noise=0.01)
    x, y = bounds["right"]
    bounds["right"] = (x[x < 40], (y + 0.04 * x)[x < 40])
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    assert "right" not in j["x_max"] and abs(j["t"] - 0.01) < 0.002, j


def _settle(xyz, cfg, n=8):
    m = None
    for _ in range(n):
        m = estimate_track(xyz, cfg, prev=m)
    return m


def test_estimate_track_off_never_bends_on_follows_the_transition():
    """The wall-drift test's curve entry (transition from 30 m, inner wall to 70 m): with the joint fit the
    axis stays within 0.5 m of the track to 120 m, where the quadratic lags by more."""
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    off = _settle(xyz, _cfg())
    on = _settle(xyz, _cfg(**JOINT))
    assert off.curv_step == 0.0 and not off.bent
    e_off = abs(float(off.center_y(120.0)) - float(yt(120.0)))
    e_on = abs(float(on.center_y(120.0)) - float(yt(120.0)))
    assert e_on < 0.5 < e_off, (e_on, e_off)
    for x in (10.0, 30.0, 60.0):
        assert abs(float(on.center_y(x)) - float(yt(x))) < 0.25, x


@pytest.mark.skipif(not _native.enabled(), reason="native kernels not built")
def test_bent_model_uses_the_numpy_paths_with_the_same_result():
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    m = _settle(xyz, _cfg(**JOINT))
    assert m.bent
    from resense.gauge import corridor_coordinates
    dy, h = corridor_coordinates(xyz, m)
    X = xyz[:, 0].astype(np.float64)
    assert np.allclose(dy, xyz[:, 1] - m.center_y(X)) and np.allclose(h, xyz[:, 2] - m.rail_z(X))


def test_distance_smoothing_exponent_and_rate_limits():
    """K1: at standstill (travel 0) the axis EMA uses walls_smoothing ** walls_smoothing_min_k and the rate
    limits scale the same way; unknown travel and the switch off keep the per-period behaviour."""
    xyz, _ = _entry_scene(j=0.0)
    base = _cfg()
    prev = _settle(xyz, base)
    prev = replace(prev, yaw=prev.yaw + 0.002, curvature=prev.curvature + 5e-5)   # a noisy previous fit
    a = estimate_track(xyz, base, prev=prev)
    assert estimate_track(xyz, base, prev=prev, travel=0.0).yaw == a.yaw               # off: travel ignored
    on = replace(base, walls_smoothing_distance=1.5)
    assert estimate_track(xyz, on, prev=prev, travel=None).yaw == a.yaw                # unknown speed
    assert estimate_track(xyz, on, prev=prev, travel=1.5).yaw == a.yaw                 # one period's travel
    s = estimate_track(xyz, on, prev=prev, travel=0.0)
    # the standing frame stays near the previous model: weight 0.6 ** 0.05 = 0.975 (rate limits 5 % as well)
    assert abs(s.yaw - prev.yaw) < 0.2 * abs(a.yaw - prev.yaw)
    assert abs(s.curvature - prev.curvature) <= 0.05 * base.axis_max_curvature_rate + 1e-12


def test_joint_fit_follows_a_curve_that_ends_beyond_the_reach():
    """A wall that bends to the knot and then runs straighter (as at the far end of squareT_platform): the far
    bins join and the axis at 140 m follows the straighter continuation (the step), not the extrapolated curve."""
    rails, bounds, yt = _curve_obs(k=2e-4, step=-2e-4, sides=((2.4, 56.0), (-2.3, 148.0)), noise=0.02)
    j = joint_axis_fit(rails, bounds, _model(curvature=2e-4), _cfg(**JOINT))
    assert j["x_max"]["right"] >= 140, j
    y = j["c"] + j["t"] * 140 + 0.5 * j["k"] * 140 ** 2 + 0.5 * j["step"] * (140 - j["knot"]) ** 2
    assert abs(y - yt(140.0)) < 0.5, (y, yt(140.0))


def test_a_diverging_far_segment_is_not_admitted():
    """A far structure after a gap that diverges from the track (a hall wall, 0.08 m per metre) does not join:
    no shape with a curvature step explains it within the tolerance together with the rest."""
    rails, bounds, yt = _curve_obs(k=0.0, sides=((2.4, 120.0), (-2.3, 84.0)), noise=0.02)
    xf = np.arange(104.0, 152.1, 4.0)
    x, y = bounds["right"]
    bounds["right"] = (np.r_[x, xf], np.r_[y, yt(xf) - 2.3 - 0.08 * (xf - 104.0)])
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    assert j["x_max"]["right"] <= 84.0, j
    assert abs(j["k"]) < 5e-5 and abs(j["step"]) < 5e-5, j


def test_review_converging_structure_at_the_start_does_not_bend_the_axis():
    """Review finding 1: a short converging structure at 28-44 m (3-4 bins) must not enter the first fit and bend
    the shared curvature on straight track; the real wall keeps its reach."""
    rails, bounds, yt = _curve_obs(k=0.0, sides=((2.4, 120.0), (-2.3, 120.0)), noise=0.01)
    x, y = bounds["right"]
    conv = (x >= 28) & (x <= 44)
    y = np.where(conv, y + 0.12 * (x - 28.0), y)              # 0.12 per metre towards the axis
    xs = np.r_[x[x < 28], x[conv], x[x > 44]]
    ys = np.r_[y[x < 28], y[conv], y[x > 44]]
    bounds["right"] = (xs, ys)
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    y100 = j["c"] + j["t"] * 100 + 0.5 * j["k"] * 100 ** 2 + 0.5 * j["step"] * max(100 - j["knot"], 0) ** 2
    assert abs(y100 - yt(100.0)) < 0.3, j
    assert j["x_max"].get("left", 0) >= 116, j


def test_review_rotation_keeps_the_step_far_out():
    m = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 55.0), center=0.0, yaw=0.0,
                   curvature=1e-4, curv_step=-1e-3, curv_knot=60.0)       # the bed ends before the knot
    r = rotate_track_model(m, np.eye(3))
    assert abs(float(r.center_y(150.0)) - float(m.center_y(150.0))) < 0.05


def test_review_non_finite_bins_are_ignored():
    rails, bounds, _ = _curve_obs(k=0.0, sides=((2.4, 120.0), (-2.3, 120.0)))
    x, y = bounds["left"]
    y = y.copy()
    y[5] = np.nan
    bounds["left"] = (x, y)
    j = joint_axis_fit(rails, bounds, _model(), _cfg(**JOINT))
    assert j is not None and all(np.isfinite([j["c"], j["t"], j["k"], j["step"]]))


def test_review_straight_track_keeps_the_native_quadratic():
    """Review finding 4: without data beyond the knot the step is exactly 0, the model is not bent."""
    xyz, _ = _entry_scene(j=0.0, inner_to=50.0)
    xyz = xyz[xyz[:, 0] < 58.0]
    m = _settle(xyz, _cfg(**JOINT))
    assert m.curv_step == 0.0 and not m.bent


def test_shape_only_mode_keeps_the_axis_shape_and_the_old_range_policy():
    """v4 (axis_joint_range off): the axis shape is the joint fit's (identical to v3's), the trusted range comes
    from the per-side fits as without the joint fit."""
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    v3 = _settle(xyz, _cfg(**JOINT))
    v4 = _settle(xyz, _cfg(axis_joint_fit=True, axis_joint_range=False))
    X = np.array([30.0, 80.0, 120.0])
    assert np.allclose(v3.center_y(X), v4.center_y(X), atol=1e-9)
    assert abs(float(v4.center_y(120.0)) - float(yt(120.0))) < 0.5


# --- v5 (axis_joint_min_curvature, axis_joint_reach_cap): the joint shape on curves only -------------------------
V4 = dict(axis_joint_fit=True, axis_joint_range=False)
V5 = dict(V4, axis_joint_min_curvature=1e-4)
_SHAPE = ("center", "yaw", "curvature", "curv_step", "curv_knot")
_STATE = _SHAPE + ("floor_range", "rail_offset", "axis_valid", "axis_valid_both", "axis_valid_bent", "axis_sides",
                   "wall_quality", "far_support_run", "disagree_left", "axis_straight", "wall_drift", "floor_verified", "age")


def _same(a: TrackModel, b: TrackModel, fields=_STATE) -> bool:
    return all(getattr(a, f) == getattr(b, f) for f in fields) and np.array_equal(a.floor_coef, b.floor_coef)


def _run(xyz, cfg, n=8):
    out, m = [], None
    for _ in range(n):
        m = estimate_track(xyz, cfg, prev=m)
        out.append(m)
    return out


def test_v5_off_unless_the_joint_fit_is_on_and_shape_only():
    """axis_joint_min_curvature alone (joint fit off) or with the v3 range policy changes nothing; no record field."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    for base_kw, kw in (({}, dict(axis_joint_min_curvature=1e-4)), (JOINT, dict(JOINT, axis_joint_min_curvature=1e-4))):
        a, b = _run(xyz, _cfg(**base_kw)), _run(xyz, _cfg(**kw))
        assert all(_same(x, y) and y.base is None and y.joint_used is None for x, y in zip(a, b))
        assert "joint_used" not in b[-1].to_dict()


def test_v5_straight_track_is_exactly_the_estimate_without_the_joint_fit():
    """On a straight track (|k| below the limit every frame) the output is the estimator without the joint fit,
    frame by frame and bit for bit; the record says the joint shape was not used."""
    xyz, _ = _entry_scene(j=0.0)
    off, v5 = _run(xyz, _cfg()), _run(xyz, _cfg(**V5))
    for a, b in zip(off, v5):
        assert abs(a.curvature) < 1e-4
        assert _same(a, b) and b.joint_used is False and not b.bent and b.joint_shape is not None
    assert v5[-1].to_dict()["joint_used"] is False and "joint_used" not in off[-1].to_dict()


def test_v5_curve_follows_the_joint_shape_and_carries_the_unchanged_base_state():
    """On the curve entry the output takes the joint shape (within 0.5 m of the track at 120 m, as v4) while the
    carried base model is, frame by frame, exactly the model of the estimator without the joint fit (which lags):
    the next frame is estimated from it, so nothing of the joint shape feeds back into the base state."""
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    off, v5 = _run(xyz, _cfg()), _run(xyz, _cfg(**V5))
    for a, b in zip(off, v5):
        assert _same(a, b.base) and b.base.base is None
    last = v5[-1]
    assert last.joint_used is True and abs(last.base.curvature) >= 1e-4 and last.bent
    assert (last.center, last.yaw, last.curvature, last.curv_step, last.curv_knot) == last.joint_shape
    assert not _same(last, last.base, _SHAPE)                               # positive control: the shapes differ
    e_v5 = abs(float(last.center_y(120.0)) - float(yt(120.0)))
    e_base = abs(float(last.base.center_y(120.0)) - float(yt(120.0)))
    assert e_v5 < 0.5 < e_base, (e_v5, e_base)
    # the range policy is the base estimator's (v4): trusted range and side count unchanged
    assert (last.axis_valid, last.axis_sides) == (last.base.axis_valid, last.base.axis_sides)
    assert last.to_dict()["joint_used"] is True


def test_v5_threshold_selects_the_shape():
    """A limit above the base curvature keeps the base shape on the same curve; the joint shape state still runs."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    v5 = _run(xyz, _cfg(**V5))
    hi = _run(xyz, _cfg(**dict(V5, axis_joint_min_curvature=abs(v5[-1].base.curvature) * 10)))
    assert hi[-1].joint_used is False and _same(hi[-1], v5[-1].base) and hi[-1].joint_shape == v5[-1].joint_shape


def test_v5b_reach_cap_only_on_joint_frames_and_never_extends():
    """axis_joint_reach_cap: on a joint-shape frame the trusted range is min(base range, farthest boundary reach along
    the output axis + margin); on a straight frame nothing changes."""
    from resense.track import _followed_reach, estimate_axis_from_walls
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    cfg5, cfg5b = _cfg(**V5), _cfg(**dict(V5, axis_joint_reach_cap=True))
    a, b = _run(xyz, cfg5), _run(xyz, cfg5b)
    last, capped = a[-1], b[-1]
    assert _same(last.base, capped.base) and capped.joint_used
    bounds: dict = {}
    estimate_axis_from_walls(xyz, last.base, cfg5, np.tan(last.base.yaw), boundaries=bounds)
    assert capped.axis_valid <= last.axis_valid
    assert capped.axis_valid_both <= last.axis_valid_both
    if capped.axis_valid < last.axis_valid:
        assert capped.joint_reach == capped.axis_valid and capped.to_dict()["joint_reach"] == round(capped.axis_valid, 1)
    reach = [_followed_reach(x, y, capped, cfg5b) for x, y in bounds.values() if len(x)]
    assert max(reach) > 0
    xs, _ = _entry_scene(j=0.0)
    s5, s5b = _run(xs, cfg5)[-1], _run(xs, cfg5b)[-1]
    assert not s5b.joint_used and _same(s5, s5b) and s5b.joint_reach == 0.0


def test_v5_rotation_rotates_the_base_state_and_the_joint_shape():
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    m = _run(xyz, _cfg(**V5))[-1]
    a = np.radians(0.3)
    dR = np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])
    r = rotate_track_model(m, dR)
    assert _same(r.base, rotate_track_model(m.base, dR)) and r.joint_used and r.base.base is None
    assert (r.center, r.yaw, r.curvature, r.curv_step, r.curv_knot) == r.joint_shape
    assert abs(r.axis_valid - m.axis_valid) == 0.0
    X = np.array([40.0, 90.0])
    rot = np.stack([X, m.center_y(X), np.zeros(2)], 1) @ dR.T          # the joint axis, rotated
    assert np.allclose(r.center_y(rot[:, 0]), rot[:, 1], atol=0.02)
