"""N3 diffuse-return guard (resense/dust_guard.py, ``dust.enabled``)."""
from dataclasses import replace
import math

import numpy as np
import pytest

from resense.config import DetectorConfig, DustGuardConfig
from resense.detector import Detector
from resense.dust_guard import DustGuard, degraded_health, required_support, support_radius


CFG = DustGuardConfig(enabled=True)


def poisson_tail(lam, k):
    return 1.0 - sum(math.exp(-lam) * lam ** j / math.factorial(j) for j in range(k))


@pytest.mark.parametrize("lam", [0.0, 0.01, 0.137, 0.5, 1.37, 3.0, 8.0])
def test_required_support_is_the_smallest_rare_count(lam):
    k = int(required_support(np.array([lam]), CFG)[0])
    assert CFG.min_support <= k <= CFG.max_support
    if k < CFG.max_support:
        assert poisson_tail(lam, k) <= CFG.false_support
    if k > CFG.min_support:
        assert poisson_tail(lam, k - 1) > CFG.false_support


def test_required_support_grows_with_density():
    ks = required_support(np.array([0.0, 0.1, 0.5, 1.0, 2.0, 4.0]), CFG)
    assert np.all(np.diff(ks) >= 0) and ks[0] == CFG.min_support and ks[-1] > ks[0]


def interior_frame(rng, density, x=(5.0, 60.0)):
    """A diffuse field filling the guard's interior volume; dy / h are given directly."""
    vol = (x[1] - x[0]) * 2.0 * 2.4
    n = rng.poisson(vol * density)
    xyz = np.column_stack([rng.uniform(*x, n), rng.uniform(-1, 1, n), rng.uniform(0.3, 2.7, n)])
    return xyz, xyz[:, 1].copy(), xyz[:, 2].copy()


def test_inactive_on_empty_interior_and_active_on_diffuse_field():
    rng = np.random.default_rng(1)
    g = DustGuard(CFG)
    xyz = np.array([[30.0, 3.5, 1.0]])
    assert not g.assess(xyz, xyz[:, 1], xyz[:, 2])["active"]
    xyz, dy, h = interior_frame(rng, 1.0)
    st = g.assess(xyz, dy, h)
    assert st["active"] and st["isolated_density"] > 0.7 and st["isolated_spread"] > 0.5
    assert 0.8 < st["field_density"] < 1.3


def test_concentrated_isolated_returns_do_not_switch_it_on():
    # a thinly sampled structure in one corner: dense enough in count, not spread
    rng = np.random.default_rng(2)
    n = 400
    xyz = np.column_stack([rng.uniform(20, 25, n), rng.uniform(0.5, 1.0, n), rng.uniform(2.1, 2.7, n)])
    g = DustGuard(CFG)
    st = g.assess(xyz, xyz[:, 1], xyz[:, 2])
    assert st["isolated_spread"] < CFG.on_spread and not st["active"]


def test_hysteresis_holds_then_releases():
    rng = np.random.default_rng(3)
    g = DustGuard(CFG)
    xyz, dy, h = interior_frame(rng, 1.0)
    assert g.assess(xyz, dy, h)["active"]
    empty = np.zeros((0, 3))
    for _ in range(CFG.hold_frames):
        assert g.assess(empty, empty[:, 1], empty[:, 2])["active"]
    assert not g.assess(empty, empty[:, 1], empty[:, 2])["active"]
    g.reset()
    assert not g.active and g.last is None


def surface(distance, width=0.6, height=1.5, step_deg=(0.1, 0.125), y0=0.0, z0=0.5):
    """Returns of a flat face at ``distance`` sampled at the given angular steps."""
    ys = np.arange(-width / 2, width / 2, distance * math.radians(step_deg[0])) + y0
    zs = np.arange(0, height, distance * math.radians(step_deg[1])) + z0
    Y, Z = np.meshgrid(ys, zs)
    return np.column_stack([np.full(Y.size, distance), Y.ravel(), Z.ravel()])


@pytest.mark.parametrize("level", [1.0, 10.0])
@pytest.mark.parametrize("distance", [10.0, 30.0, 55.0, 90.0])
def test_solid_face_inside_dust_keeps_all_returns_dust_mostly_goes(level, distance):
    rng = np.random.default_rng(4)
    dust, _, _ = interior_frame(rng, level)
    face = surface(distance)
    xyz = np.concatenate([face, dust])
    g = DustGuard(CFG)
    assert g.assess(xyz, xyz[:, 1], xyz[:, 2])["active"]
    keep = g.supported(xyz, np.arange(len(xyz)), xyz[:, 1], xyz[:, 2])
    if level <= 1:
        assert keep[:len(face)].all()
    else:
        # a dense field raises the required count: the face's rim may go, its body stays
        rim = ((np.abs(face[:, 1]) > face[:, 1].max() - 0.3) | (face[:, 2] < face[:, 2].min() + 0.3)
               | (face[:, 2] > face[:, 2].max() - 0.3))
        assert keep[:len(face)][~rim].all() and keep[:len(face)].mean() > 0.6
    assert keep[len(face):].mean() < (0.01 if level <= 1 else 0.05)


@pytest.mark.parametrize("distance", [15.0, 50.0, 120.0])
@pytest.mark.parametrize("vertical", [False, True])
def test_dark_thin_cable_is_supported(distance, vertical):
    """A 2 cm cable seen as one row (horizontal) or one column of returns (vertical);
    intensity plays no role in the guard."""
    rng = np.random.default_rng(5)
    if vertical:
        z = np.arange(0.4, 2.6, distance * math.radians(0.125))
        cable = np.column_stack([np.full(z.size, distance), np.zeros(z.size), z])
    else:
        y = np.arange(-1.0, 1.0, distance * math.radians(0.1))
        cable = np.column_stack([np.full(y.size, distance), y, np.full(y.size, 1.5)])
    dust, _, _ = interior_frame(rng, 1.0)
    xyz = np.concatenate([cable, dust])
    g = DustGuard(CFG)
    g.assess(xyz, xyz[:, 1], xyz[:, 2])
    keep = g.supported(xyz, np.arange(len(xyz)), xyz[:, 1], xyz[:, 2])[:len(cable)]
    # the body of the line is kept; its last one or two returns at each end may lack neighbours
    assert keep[2:-2].all() and keep.sum() >= 4


def test_inactive_guard_keeps_everything_and_accumulated_returns_are_kept():
    g = DustGuard(CFG)
    xyz = np.array([[30.0, 0.0, 1.0], [40.0, 0.5, 2.0]])
    assert g.supported(xyz, np.array([0, 1]), xyz[:, 1], xyz[:, 2]).all()
    rng = np.random.default_rng(6)
    d, dy, h = interior_frame(rng, 1.0)
    g.assess(d, dy, h)
    keep = g.supported(d, np.array([-1, -1, 0]), dy, h)
    assert keep[0] and keep[1]


def test_degraded_health_never_lowers_an_error_and_declines_range():
    for level in ("ok", "warn", "error"):
        out = degraded_health({"level": level, "decision_level": level, "messages": ["x"],
                               "monitored_range": 80.0, "clear_distance": 50.0}, {"active": True}, 7)
        assert out["level"] == ("error" if level == "error" else "warn")
        assert out["decision_level"] == ("error" if level == "error" else "warn")
        assert out["monitored_range"] == 0.0 and out["clear_distance"] == 0.0
        assert out["messages"][0] == "x" and "dust" in out["messages"][-1]
        assert out["dust_guard"]["unsupported_candidate_returns"] == 7


def test_support_radius_scales_with_range():
    r = support_radius(np.array([0.0, 50.0, 100.0]), CFG)
    assert r[0] == pytest.approx(CFG.support_radius) and r[2] > r[1] > r[0]


def test_switch_off_by_default_and_in_both_parameter_files():
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert DetectorConfig().dust.enabled is False and Detector().dust_guard is None
    for p in ("configs/default.yaml", "ros2_ws/src/resense_ros/config/detector.yaml"):
        y = yaml.safe_load((root / p).read_text())["resense"]
        assert y["dust"]["enabled"] is False
        assert DetectorConfig.from_yaml(str(root / p)).dust == DustGuardConfig()


def tunnel_and_dust(level, seed, with_box):
    from resense import dust as gen
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    specs = [ObstacleSpec(kind="box", size=(0.5, 0.6, 0.6), distance=40.0, lateral=0.0,
                          reflectivity=1.0)] if with_box else []
    frame, labels, track = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=specs)
    if level == "clean":
        return frame
    out, _, _ = gen.augment_dust(frame, gen.PRESETS[level], rail_z=float(track.rail_z(np.array([20.0]))[0]),
                                 seed=seed, frame_index=seed)
    return out


@pytest.fixture(scope="module")
def dusty_runs():
    pytest.importorskip("open3d")
    runs = {}
    for level in ("clean", "medium"):
        for guard in (False, True):
            cfg = DetectorConfig()
            cfg.dust.enabled = guard
            cfg.health.latency_budget_ms = 1e9     # wall-clock warnings are not outputs under test
            det = Detector(cfg)
            res = []
            for i in range(12):
                f = tunnel_and_dust(level, i, with_box=True)
                f = replace(f, stamp=0.1 * i)
                res.append(det.process(f))
            runs[level, guard] = res
    return runs


def test_switched_on_guard_is_identical_on_clean_synthetic_tunnel(dusty_runs):
    off, on = dusty_runs["clean", False], dusty_runs["clean", True]
    for a, b in zip(off, on):
        da, db = a.to_dict(), b.to_dict()
        for d in (da, db):
            d.pop("timing_ms", None)
            d["health"].pop("latency_p95_ms", None)
        assert da == db


def test_dark_box_in_medium_dust_is_kept_and_health_is_degraded(dusty_runs):
    on = dusty_runs["medium", True]
    assert all(r.health["decision_level"] in ("warn", "error") for r in on[1:])
    assert all(r.clear_distance == 0.0 for r in on[1:])
    assert on[-1].obstacle and any(abs(d.distance - 40.0) < 1.5 for d in on[-1].detections)
