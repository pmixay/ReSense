"""The optional native kernels (resense/_native.py, native/resense_native.cpp) against the numpy
code they replace: every result must be bit-identical, and the detector's output with and
without them must be the same.

Skipped when the library is not built (``pip install`` builds it; a source checkout:
``scripts/build_native.sh``); CI sets RESENSE_REQUIRE_SYNTHETIC=1, which turns that skip into a
failure, so the shipped path is always the tested one.
"""
from __future__ import annotations

import contextlib

import numpy as np
import pytest

from resense import _native
from resense.track import TrackModel, bin_percentile

pytestmark = pytest.mark.skipif(not _native.AVAILABLE, reason="native kernels not built (scripts/build_native.sh)")


@contextlib.contextmanager
def native(on: bool):
    prev = _native.set_enabled(on)
    try:
        yield
    finally:
        _native.set_enabled(prev)


def both(fn):
    """fn() with the native kernels, then with numpy."""
    with native(True):
        a = fn()
    with native(False):
        b = fn()
    return a, b


def bits_equal(a, b) -> bool:
    """Same shape, dtype and bits (NaN == NaN)."""
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        return False
    if a.dtype.kind == "f":
        a, b = np.ascontiguousarray(a).reshape(-1), np.ascontiguousarray(b).reshape(-1)
        u = np.dtype(f"u{a.dtype.itemsize}")
        return bool(np.all((np.isnan(a) & np.isnan(b)) | (a.view(u) == b.view(u))))
    return bool(np.array_equal(a, b))


def test_status_line():
    assert _native.enabled() in (True, False)
    assert "native" in _native.status() or "numpy" in _native.status()


@pytest.mark.parametrize("percentile", [0.0, 10.0, 50.0, 90.0, 95.0, 100.0, 33.3])
@pytest.mark.parametrize("min_points", [1, 4, 8])
def test_bin_percentile_identical(percentile, min_points):
    rng = np.random.default_rng(int(percentile * 10) + min_points)
    n, nb = 20000, 300
    values = np.round(rng.normal(0.0, 0.3, n), 2)          # many ties
    values[rng.integers(0, n, 50)] = np.nan                 # NaN sorts last, as in numpy
    values[rng.integers(0, n, 50)] = -0.0
    bins = rng.integers(0, nb + 5, n)                        # some beyond nb: ignored by both
    bins[bins % 17 == 3] = 7                                 # one crowded bin
    payload = rng.normal(0.0, 1.0, n)
    a, b = both(lambda: bin_percentile(values, bins, nb, percentile, min_points))
    assert all(bits_equal(x, y) for x, y in zip(a, b))
    a, b = both(lambda: bin_percentile(values, bins, nb, percentile, min_points, payload=payload))
    assert len(a) == 3 and all(bits_equal(x, y) for x, y in zip(a, b))


def test_bin_percentile_fallbacks():
    rng = np.random.default_rng(3)
    values = rng.normal(size=500)
    bins = rng.integers(0, 10, 500)
    bins[4] = -1                                             # numpy raises; the native path must not hide it
    with native(True), pytest.raises(ValueError):
        bin_percentile(values, bins, 10, 50.0)
    small = both(lambda: bin_percentile(values[:10], np.abs(bins[:10]), 10, 50.0))   # below the native size
    assert all(bits_equal(x, y) for x, y in zip(*small))
    empty = both(lambda: bin_percentile(np.zeros(0), np.zeros(0, int), 4, 50.0, payload=np.zeros(0)))
    assert all(bits_equal(x, y) for x, y in zip(*empty))


def _model():
    return TrackModel(floor_coef=np.array([1.3e-4, -0.021, -1.62]), floor_range=(4.0, 83.7), center=0.137,
                      yaw=np.radians(0.41), curvature=-1.7e-4, rail_offset=0.172)


def _cloud(n=50000, seed=0):
    rng = np.random.default_rng(seed)
    xyz = np.stack([rng.uniform(-30, 220, n), rng.uniform(-8, 8, n), rng.uniform(-3, 5, n)], axis=1)
    return xyz.astype(np.float32)


def test_floor_z_center_y_identical():
    m = _model()
    xyz = _cloud()
    for X in (xyz[:, 0], xyz[:, 0].astype(np.float64), xyz[::3, 0], np.float64(55.0), 12.5, xyz[:100, 0]):
        a, b = both(lambda: m.floor_z(X))
        assert bits_equal(a, b)
        a, b = both(lambda: m.center_y(X))
        assert bits_equal(a, b)
        a, b = both(lambda: m.rail_z(X))
        assert bits_equal(a, b)
    m2 = TrackModel(floor_coef=np.array([0.0, -1.5]), floor_range=(4.0, 80.0), center=0.0, yaw=0.0, curvature=0.0)
    a, b = both(lambda: m2.floor_z(xyz[:, 0]))              # not a quadratic: numpy's polyval path
    assert bits_equal(a, b)


def test_corridor_coordinates_and_visibility_identical():
    from resense.gauge import corridor_coordinates
    from resense.health import visibility_along_track
    m = _model()
    xyz = _cloud(80000, 1)
    a, b = both(lambda: corridor_coordinates(xyz, m))
    assert bits_equal(a[0], b[0]) and bits_equal(a[1], b[1])
    a, b = both(lambda: corridor_coordinates(xyz.astype(np.float64), m))    # float64 cloud: numpy path
    assert bits_equal(a[0], b[0]) and bits_equal(a[1], b[1])
    for k in (1, 20, 10 ** 6):
        a, b = both(lambda: visibility_along_track(xyz, m.center_y, k=k))
        assert a == b and type(a) is type(b)
    behind = xyz.copy()
    behind[:, 0] = -np.abs(behind[:, 0]) - 1.0
    a, b = both(lambda: visibility_along_track(behind, m.center_y))
    assert a == b == 0.0


def _frames(tunnel, n=6):
    """The clear synthetic tunnel with a 0.5 m box of points approaching in the gauge."""
    frame, _, gt = tunnel
    from resense.frame import Frame
    rng = np.random.default_rng(7)
    out = []
    for i in range(n):
        d = 60.0 - 2.0 * i
        box = rng.uniform(0, 0.5, (400, 3)) + np.array([d, gt.center - 0.25, float(gt.rail_z(d)) + 0.1])
        xyz = np.concatenate([frame.xyz, box.astype(np.float32)])
        out.append(Frame(xyz=xyz, intensity=np.concatenate([frame.intensity, np.full(400, 30.0, np.float32)]),
                         stamp=0.1 * i))
    return out


def _strip(d: dict) -> dict:
    d = dict(d)
    d.pop("timing_ms")
    d["health"] = {k: v for k, v in d["health"].items() if k not in ("latency_p95_ms", "level", "messages")}
    return d


def test_detector_output_identical(tunnel):
    from resense.config import DetectorConfig
    from resense.detector import Detector
    frames = _frames(tunnel)
    cfg = DetectorConfig.from_yaml("configs/default.yaml")

    def run():
        det = Detector(cfg)
        return [_strip(det.process(f).to_dict()) for f in frames]

    a, b = both(run)
    assert a == b
    assert any(r["obstacle"] or r["warning"] for r in a)     # the box is reported: the comparison is not vacuous
