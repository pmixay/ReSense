"""19.10 Falcon long range (``farrange``): off for Pandar, on only through the Falcon profiles;
the far straight axis accepts straight boundaries and rejects curves; far confirmation."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))

from resense.config import DetectorConfig, FarRangeConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.farline import FarAxisTracker, FarConfirm, measure  # noqa: E402
from resense.track import TrackModel  # noqa: E402
from resense_ros.sensor_profiles import apply_sensor_profile  # noqa: E402


def test_default_and_pandar_profiles_leave_farrange_off():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    assert cfg.farrange.enabled is False and cfg.sensor.max_range == 250.0
    for name in ("manual", "pandar128"):
        resolved, _ = apply_sensor_profile(cfg, name)
        assert resolved.farrange.enabled is False
        assert resolved.sensor.max_range == resolved.gauge.range_max == resolved.track.floor_verify_max_range == 250.0
    det = Detector(cfg)
    assert det.far is None and det.far_confirm is None
    resolved, _ = apply_sensor_profile(cfg, "falcon_ros")
    det = Detector(resolved)
    assert det.far is not None and det.far_confirm is None          # far confirmation is off by default


def test_falcon_profiles_enable_farrange_and_the_long_crop():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    for name in ("falcon_ros", "falcon_native"):
        resolved, model = apply_sensor_profile(cfg, name)
        assert model == "falcon_prime" and resolved.farrange.enabled is True
        assert resolved.sensor.max_range == resolved.gauge.range_max == resolved.track.floor_verify_max_range == 400.0
        assert cfg.farrange.enabled is False                    # the input config is not modified
    cfg.farrange.with_falcon_profile = False                    # explicit opt-out keeps the old Falcon behaviour
    resolved, _ = apply_sensor_profile(cfg, "falcon_ros")
    assert resolved.farrange.enabled is False and resolved.sensor.max_range == 250.0


def test_farrange_section_loads_from_yaml_dict():
    cfg = DetectorConfig.from_dict({"farrange": {"enabled": True, "axis_join": 60.0}})
    assert cfg.farrange.enabled and cfg.farrange.axis_join == 60.0


def _model():
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.95]), floor_range=(5.0, 90.0), center=0.0,
                      yaw=0.0, curvature=0.0, rail_offset=0.2)


def _walls(curv=0.0, slope=0.0005, x1=260.0, seed=0):
    rng = np.random.default_rng(seed)
    X = np.repeat(np.arange(52.0, x1, 1.0), 6)
    Y = 1.9 + slope * X + 0.5 * curv * (X - 50.0) ** 2 + rng.normal(0, 0.03, X.size)
    Z = -1.75 + rng.uniform(1.1, 2.6, X.size)
    return np.stack([X, Y, Z], axis=1).astype(np.float32)


def test_far_axis_measures_a_straight_boundary_and_rejects_a_curve():
    cfg = FarRangeConfig(enabled=True)
    m = measure(_walls(), _model(), cfg, 400.0)
    assert m is not None and abs(m[0] - 0.0005) < 2e-4 and m[2] > 250.0
    assert measure(_walls(curv=1.0 / 3000.0), _model(), cfg, 400.0) is None      # R 3 km: bow over 200 m
    assert measure(_walls(x1=110.0), _model(), cfg, 400.0) is None                # too short a span


def test_far_axis_tracker_confirms_offsets_and_bounds_the_trust():
    cfg = FarRangeConfig(enabled=True)
    tr = FarAxisTracker(cfg)
    model = _model()
    out = [tr.update(_walls(seed=k), model, 400.0) for k in range(cfg.axis_confirm_frames)]
    assert all(o is None for o in out[:-1]) and out[-1] is not None
    far = out[-1]
    assert far.sides == 1 and 200.0 < far.valid < 215.0          # one side: the 0.003 rad divergence allowance bounds sigma 0.5 m at ~209 m
    X = np.array([10.0, 50.0, 150.0, 200.0, 300.0])
    off = far.offset(X, model)
    assert off[0] == 0.0 and off[1] == 0.0 and abs(off[3] - far.slope * 150.0) < 1e-9
    assert off[4] == 0.0                                   # beyond the trusted range: the near model as before
    s = far.sigma(X)
    assert s[0] == 0.0 and s[2] >= cfg.axis_sigma0 and s[3] > s[2] and s[4] == 0.0
    for k in range(cfg.axis_hold_frames + 1):              # no boundary: held, then dropped
        res = tr.update(np.zeros((0, 3), np.float32), model, 400.0)
    assert res is None


def _tracks(ds, tid=7):
    return [SimpleNamespace(id=tid, misses=0, last=SimpleNamespace(distance=d)) for d in ds]


def test_far_confirm_needs_consistent_range_history():
    cfg = FarRangeConfig(enabled=True, confirm_enabled=True)
    fc = FarConfirm(cfg)
    for d in (260.0, 259.9, 259.8, 259.7):
        fc.update(_tracks([d]))
    assert not fc.ok(7)                                    # four hits: not yet
    fc.update(_tracks([259.6]))
    assert fc.ok(7)                                        # a steady approach
    hop = FarConfirm(cfg)
    for d in (250.0, 262.0, 248.0, 270.0, 255.0, 266.0):
        hop.update(_tracks([d]))
    assert not hop.ok(7)                                   # returns hopping along the ray
    fc.update([])                                          # the track is gone: its history too
    assert not fc.ok(7)


# 19.10 independent review B1: curves starting beyond the join, an occluded inner wall and a single
# diverging wall. Wherever the far axis claims trust (up to ``valid``), its error must stay within
# sigma + 0.3 m; rejecting the frame is always acceptable.

def _centre(X, xc, radius):
    return np.where(X > xc, 0.5 * (X - xc) ** 2 / radius, 0.0)


def _curved_walls(xc, radius, seed, occlude_inner=False):
    rng = np.random.default_rng(seed)
    out = []
    for s in (1.0, -1.0):
        X = np.repeat(np.arange(52.0, 400.0, 1.0), 6)
        Y = _centre(X, xc, radius) + s * 1.9 + rng.normal(0, 0.03, X.size)
        Z = -1.75 + rng.uniform(1.1, 2.6, X.size)
        keep = ~((s < 0) & (X > xc + 20)) if occlude_inner else np.ones(X.size, bool)
        out.append(np.stack([X, Y, Z], 1)[keep])
    return np.concatenate(out).astype(np.float32)


def _check_within_sigma(far, model, truth):
    X = np.arange(60.0, far.valid + 1.0, 5.0)
    err = np.abs(far.offset(X, model) - truth(X))
    assert np.all(err <= far.sigma(X) + 0.3), (far.to_dict(), float(err.max()), float(X[err.argmax()]))


def test_far_axis_never_trusts_a_curve_beyond_its_support():
    cfg = FarRangeConfig(enabled=True)
    model = _model()
    for occl in (False, True):
        for xc in (120.0, 160.0, 200.0, 240.0):
            for radius in (300.0, 600.0, 1000.0, 3000.0):
                tr = FarAxisTracker(cfg)
                far = None
                for k in range(8):
                    far = tr.update(_curved_walls(xc, radius, k, occl), model, 400.0)
                if far is not None:
                    _check_within_sigma(far, model, lambda X: _centre(X, xc, radius))


def test_far_axis_single_diverging_wall_is_rejected_or_covered():
    cfg = FarRangeConfig(enabled=True)
    model = _model()
    for slope in (0.003, 0.006, 0.009):
        for other_end in (52.0, 120.0):
            tr = FarAxisTracker(cfg)
            far = None
            for k in range(8):
                rng = np.random.default_rng(k)
                pts = []
                for side, sl, x1 in ((1.0, slope, 350.0), (-1.0, 0.0, other_end)):
                    if x1 <= 52.0:
                        continue
                    X = np.repeat(np.arange(52.0, x1, 1.0), 6)
                    pts.append(np.stack([X, side * 1.9 + sl * (X - 50) + rng.normal(0, 0.03, X.size),
                                         -1.75 + rng.uniform(1.1, 2.6, X.size)], 1))
                far = tr.update(np.concatenate(pts).astype(np.float32), model, 400.0)
            if far is not None:
                _check_within_sigma(far, model, lambda X: np.zeros_like(X))


def test_far_axis_straight_control_is_accepted_and_declared_map_extends_trust():
    model = _model()
    cfg = FarRangeConfig(enabled=True)
    tr = FarAxisTracker(cfg)
    for k in range(8):
        far = tr.update(_curved_walls(1e6, 1e9, k), model, 400.0)
    assert far is not None and far.sides == 2 and far.join < far.valid <= far.support + cfg.axis_margin
    _check_within_sigma(far, model, lambda X: np.zeros_like(X))
    cfg2 = FarRangeConfig(enabled=True, declared_straight_to=450.0)
    tr2 = FarAxisTracker(cfg2)
    for k in range(8):
        far2 = tr2.update(_walls(seed=k, x1=200.0), model, 400.0)
    assert far2 is not None and far2.sides == 1 and far2.valid > 200.0 and np.all(far2.sigma(np.arange(60.0, far2.valid, 5.0)) <= 0.5)


def test_buffer_cleared_when_far_axis_switches(monkeypatch):
    """Review B4: buffered laterals belong to the axis of their frame; a switch clears the buffer."""
    from resense.frame import Frame

    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
    resolved, _ = apply_sensor_profile(cfg, "falcon_ros")
    det = Detector(resolved)

    class Fake:
        def __init__(self, y):
            self.y_join, self.slope, self.join, self.valid = y, 0.0, 50.0, 60.0

        def offset(self, X, model):
            return np.zeros(np.shape(X))

        def sigma(self, X):
            return np.zeros(np.shape(X))

    seq = [None, Fake(0.0), Fake(0.05), Fake(1.0), Fake(1.0), None]
    expect = [False, True, False, True, False, True]
    monkeypatch.setattr(det.far, "update", lambda *a, **k: seq.pop(0))
    calls = []
    real_clear = det.buffer.clear
    monkeypatch.setattr(det.buffer, "clear", lambda: (calls.append(1), real_clear()))
    rng = np.random.default_rng(0)
    for i, want in enumerate(expect):
        calls.clear()
        xyz = np.c_[rng.uniform(5, 60, 3000), rng.uniform(-3, 3, 3000), rng.uniform(-1.8, 1.0, 3000)].astype(np.float32)
        det.process(Frame(xyz=xyz, intensity=np.zeros(3000, np.float32), stamp=0.1 * i), ego_speed=5.0)
        assert bool(calls) == want, (i, calls)
