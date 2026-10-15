"""track.axis_wall_drift (15.10, judge 13.10 problem 4): the monitored range ends where a near
tunnel boundary, followed outward from the rail range, comes ``axis_wall_drift`` nearer the axis
than it runs there. At a curve entry the quadratic axis lags the transition and the outer wall
crosses the corridor diagonally: an object on the track beyond is outside the corridor, and the
reported range must not reach past the crossing. The corridor and the decision are unchanged."""

from dataclasses import replace
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig, TrackConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.health import HealthMonitor
from resense.track import TrackModel, estimate_track, wall_drift_range

ROOT = Path(__file__).resolve().parents[1]


def test_wall_drift_defaults_in_code_and_both_parameter_files():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        t = cfg.track
        assert (t.axis_wall_drift, t.axis_wall_drift_max_offset, t.axis_wall_drift_bins) == (0.8, 3.5, 2)


def _straight(**kw) -> TrackModel:
    return TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(4.0, 100.0), center=0.0, yaw=0.0,
                      curvature=0.0, **kw)


def _bins(offsets, x0=8.0, step=4.0):
    x = x0 + step * np.arange(len(offsets))
    return x, np.asarray(offsets, dtype=np.float64)


def test_wall_drift_range_rules():
    cfg = TrackConfig()
    m = _straight()
    flat = [2.6] * 30
    assert wall_drift_range({"left": _bins(flat)}, m, cfg) == 1e9
    # a boundary closing in from 52 m by 0.1 m per bin: drift > 0.8 m from 84 m (2.6 - 0.9), two bins in a row
    closing = [2.6] * 12 + [2.6 - 0.1 * i for i in range(1, 19)]
    x, y = _bins(closing)
    got = wall_drift_range({"left": (x, y)}, m, cfg)
    first = float(x[np.flatnonzero(y < 2.6 - 0.8)[0]])
    assert got == first - 0.5 * cfg.walls_bin
    # the same on the right side (negative Y), and the nearer of two sides wins
    assert wall_drift_range({"right": (x, -y)}, m, cfg) == got
    assert wall_drift_range({"left": (x, y), "right": _bins([-2.6] * 30)}, m, cfg) == got
    # one bin alone is not a drift (a cabinet, a sign): axis_wall_drift_bins consecutive bins
    dip = [2.6] * 12 + [2.3, 2.0, 1.75, 2.0, 2.3] + [2.6] * 13
    assert wall_drift_range({"left": _bins(dip)}, m, cfg) == 1e9
    assert wall_drift_range({"left": _bins(dip)}, m, replace(cfg, axis_wall_drift_bins=1)) == 8.0 + 4 * 14 - 2.0
    # a boundary moving away says nothing (a niche, a hall, a diverging tunnel)
    assert wall_drift_range({"left": _bins([2.6] * 12 + [2.6 + 0.2 * i for i in range(18)])}, m, cfg) == 1e9
    # a structure edge (a gate, a platform screen: 1 m nearer within one bin) is no drift; the
    # boundary drifting on from its new level is
    assert wall_drift_range({"left": _bins([2.6] * 10 + [1.6] * 20)}, m, cfg) == 1e9
    stepped = [2.6] * 10 + [1.6] * 6 + [1.6 - 0.1 * i for i in range(1, 15)]
    x, y = _bins(stepped)
    assert wall_drift_range({"left": (x, y)}, m, cfg) == float(x[np.flatnonzero(y < 1.6 - 0.8)[0]]) - 2.0
    # a boundary converging on the axis already in the rail range is not parallel to the rails: no reference
    assert wall_drift_range({"left": _bins([2.6 - 0.15 * i for i in range(6)] + [1.85 - 0.1 * i for i in range(24)])},
                            m, cfg) == 1e9
    # a far boundary (double-track tunnel, hall) is no reference
    far = [3.8] * 12 + [3.8 - 0.2 * i for i in range(1, 19)]
    assert wall_drift_range({"left": _bins(far)}, m, cfg) == 1e9
    assert wall_drift_range({"left": _bins(far)}, m, replace(cfg, axis_wall_drift_max_offset=4.0)) < 1e9
    # a boundary lost for more than three bins (occluded) gives no evidence beyond the gap
    x, y = _bins(closing)
    keep = (x < 56) | (x > 76)
    assert wall_drift_range({"left": (x[keep], y[keep])}, m, cfg) == 1e9
    # an inconsistent near field is no reference; fewer than three near bins neither
    noisy = [2.6, 1.9, 3.3, 2.0, 3.2, 2.1] + closing[6:]
    assert wall_drift_range({"left": _bins(noisy)}, m, cfg) == 1e9
    assert wall_drift_range({"left": _bins(closing[5:], x0=28.0)}, m, cfg) == 1e9
    # measured against the given model's axis: the same wall around a curved axis that follows it
    k = 1.0 / 1500.0
    xc, yc = _bins([2.6] * 30)
    curved = _straight()
    curved.curvature = k
    walls = {"left": (xc, yc + 0.5 * k * xc * xc), "right": (xc, -yc + 0.5 * k * xc * xc)}
    assert wall_drift_range(walls, curved, cfg) == 1e9
    assert wall_drift_range(walls, m, cfg) < 1e9          # vs a straight axis the inner (right) wall closes in
    assert wall_drift_range({"left": walls["left"]}, m, cfg) == 1e9      # the outer one moves away


def _entry_scene(j: float, x0: float = 30.0, wall: float = 2.2, seed: int = 0, inner_to: float = 160.0):
    """Bed, the near rails (4-60 m) and two vertical walls following a track that is straight to
    ``x0`` and then enters a transition curve: curvature ``j (x - x0)`` (1/m), a clothoid in the
    small-angle approximation; the inner wall (the side the track turns to) is seen to ``inner_to``
    only (it hides itself beyond, as in roundT_pressureGate_roundT). Returns the cloud and the track's
    lateral y(x)."""
    rng = np.random.default_rng(seed)

    def yt(X):
        d = np.clip(X - x0, 0.0, None)
        return -0.1 + j * d ** 3 / 6.0
    parts = []
    X = 3 + 117 * rng.random(40000) ** 0.5
    parts.append(np.stack([X, yt(X) + rng.uniform(-1.2, 1.2, X.size), -1.5 + rng.normal(0, 0.01, X.size)], 1))
    for s in (-1, 1):
        Xr = 3 + 57 * rng.random(12000) ** 0.5
        parts.append(np.stack([Xr, yt(Xr) + s * 0.795 + rng.uniform(-0.03, 0.03, Xr.size),
                               -1.15 + rng.normal(0, 0.005, Xr.size)], 1))
    for s in (-1, 1):
        Xw = rng.uniform(3, 160 if s * j <= 0 else inner_to, 30000)
        parts.append(np.stack([Xw, yt(Xw) + s * wall + rng.normal(0, 0.02, Xw.size),
                               rng.uniform(-1.4, 3.3, Xw.size)], 1))
    return np.concatenate(parts).astype(np.float32), yt


def _settle(xyz, cfg: TrackConfig, n: int = 8) -> TrackModel:
    m = None
    for _ in range(n):
        m = estimate_track(xyz, cfg, prev=m)
    return m


def test_curve_entry_wall_drift_marks_where_the_axis_leaves_the_track():
    """A transition starting at 30 m (R 600 m reached at 130 m), the inner wall seen to 70 m: the
    axis, a quadratic held to the rails' tangent and to the inner wall's near part, lags the track
    (1.5 m at 120 m, as on roundT_pressureGate_roundT); the outer wall comes axis_wall_drift nearer
    the axis and the drift range is set where the axis is about that far off the track. A straight
    tunnel and a constant curve (R 800 m) have none."""
    cfg = TrackConfig()
    xyz, yt = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    m = _settle(xyz, cfg)
    assert m.wall_drift < 1e9, m.to_dict()
    err = abs(float(m.center_y(m.wall_drift + 0.5 * cfg.walls_bin)) - float(yt(m.wall_drift + 0.5 * cfg.walls_bin)))
    assert cfg.axis_wall_drift - 0.3 < err < cfg.axis_wall_drift + 0.6, (m.wall_drift, err)
    errs = [abs(float(m.center_y(x)) - float(yt(x))) for x in np.arange(10.0, m.wall_drift - 10.0, 5.0)]
    assert max(errs) < cfg.axis_wall_drift, errs            # nearer, the axis is within the drift
    assert m.to_dict()["wall_drift"] == round(m.wall_drift, 1)
    off = _settle(xyz, replace(cfg, axis_wall_drift=0.0))
    assert off.wall_drift == 1e9 and "wall_drift" not in off.to_dict()
    assert {k: v for k, v in m.to_dict().items() if k != "wall_drift"} == off.to_dict()   # the axis is unchanged
    for R in (1e9, 800.0):
        k = 1.0 / R
        straight, _ = _entry_scene(j=0.0)
        if R < 1e9:   # a constant curve from the vehicle on
            straight[:, 1] += 0.5 * k * straight[:, 0].astype(np.float64) ** 2
        assert _settle(straight, cfg).wall_drift == 1e9, R


def test_wall_drift_caps_the_monitored_range_only():
    """End to end: the health's monitored range and clear_distance stop at the drift range and the
    output names it; detections, decision inputs and the corridor are those of the detector
    without the rule."""
    xyz, _ = _entry_scene(j=1.0 / 60000.0, inner_to=70.0)
    inten = np.full(len(xyz), 10.0, np.float32)
    out = {}
    for drift in (0.8, 0.0):
        cfg = DetectorConfig()
        cfg.track.axis_wall_drift = drift
        det = Detector(cfg)
        res = None
        for i in range(8):
            res = det.process(Frame(xyz=xyz, intensity=inten, ring=None, stamp=0.1 * i, meta={}))
        out[drift] = res
    on, off = out[0.8], out[0.0]
    assert on.track.wall_drift < 1e9
    assert on.health["wall_drift"] == round(on.track.wall_drift, 1)
    assert on.health["monitored_range"] <= on.track.wall_drift + 0.05 < off.health["monitored_range"]
    assert on.clear_distance <= on.track.wall_drift + 0.05
    assert "wall_drift" not in off.health
    assert (on.obstacle, on.warning, on.nearest_distance) == (off.obstacle, off.warning, off.nearest_distance)
    assert [c.distance for c in on.candidates] == [c.distance for c in off.candidates]
    assert np.array_equal(on.corridor_idx, off.corridor_idx)
    assert on.health["level"] == off.health["level"] and on.health["decision_level"] == off.health["decision_level"]


def test_health_monitor_wall_drift_argument():
    from resense.config import GaugeConfig, HealthConfig
    hm = HealthMonitor(HealthConfig())
    rng = np.random.default_rng(1)
    x = rng.uniform(5, 200, 30000)
    xyz = np.stack([x, x * np.tan(np.radians(rng.uniform(-35, 35, x.size))), rng.uniform(-1, 2, x.size)], 1)
    xyz = np.concatenate([xyz, np.stack([np.linspace(5, 200, 500), np.zeros(500), np.zeros(500)], 1)])
    xyz = xyz.astype(np.float32)
    track = _straight(rail_score=1.0)
    base = hm.update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None)
    capped = HealthMonitor(HealthConfig()).update(xyz, {}, track, GaugeConfig(), 150.0, 0.05, None, wall_drift=72.0)
    assert "wall_drift" not in base and capped["wall_drift"] == 72.0
    assert base["monitored_range"] == 150.0 and capped["monitored_range"] == 72.0 == capped["clear_distance"]
    assert {k: v for k, v in capped.items() if k not in ("wall_drift", "monitored_range", "clear_distance")} == \
        {k: v for k, v in base.items() if k not in ("monitored_range", "clear_distance")}
