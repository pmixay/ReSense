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
    assert far.valid <= 260.0 + cfg.axis_margin and far.valid > 250.0
    X = np.array([10.0, 50.0, 150.0, 300.0])
    off = far.offset(X, model)
    assert off[0] == 0.0 and off[1] == 0.0 and abs(off[3] - far.slope * 250.0) < 1e-9
    s = far.sigma(X)
    assert s[0] == 0.0 and s[2] >= cfg.axis_sigma0 and s[3] > s[2]
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
