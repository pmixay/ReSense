"""Optional native (C++) kernels for the per-frame hot spots, loaded with ctypes.

The shared library ``resense/_resense_native*.so`` is built from ``native/resense_native.cpp``
by ``pip install`` (``setup.py``, an optional extension: without a compiler the package installs
and runs on numpy alone) or in a source checkout by ``scripts/build_native.sh``. Every kernel
returns bit-identical results to the numpy code it replaces (``tests/test_native.py``); the
numpy code stays in place as the fallback.

``RESENSE_NATIVE=0`` in the environment forces the numpy code; :func:`set_enabled` switches at
run time (tests, A/B timing). Each wrapper returns ``None`` when the native path does not apply
(library missing or disabled, an input type it does not handle, an array too small to be worth
the call), and the caller then runs its numpy code.
"""
from __future__ import annotations

import ctypes
import glob
import math
import os
from typing import Optional

import numpy as np

_ABI = 2
MIN_SIZE = 2048          # below this the numpy code is as fast (ctypes call ~ a few microseconds)

_c_double_p = ctypes.POINTER(ctypes.c_double)
_c_int64_p = ctypes.POINTER(ctypes.c_int64)
_c_float_p = ctypes.POINTER(ctypes.c_float)


class _Cond(ctypes.Structure):
    _fields_ = [("data", ctypes.c_void_p), ("stride", ctypes.c_int64), ("is_f64", ctypes.c_int32),
                ("absval", ctypes.c_int32), ("lo_op", ctypes.c_int32), ("hi_op", ctypes.c_int32),
                ("lo", ctypes.c_double), ("hi", ctypes.c_double)]


def _load():
    here = os.path.dirname(os.path.abspath(__file__))
    for path in sorted(glob.glob(os.path.join(here, "_resense_native*.so"))
                       + glob.glob(os.path.join(here, "_resense_native*.pyd"))):
        try:
            lib = ctypes.CDLL(path)
            if lib.rs_abi_version() != _ABI:
                continue
        except (OSError, AttributeError):
            continue
        i64, dbl, vp = ctypes.c_int64, ctypes.c_double, ctypes.c_void_p
        lib.rs_bin_percentile.restype = ctypes.c_int
        lib.rs_bin_percentile.argtypes = [_c_double_p, _c_int64_p, i64, i64, dbl, i64, _c_double_p,
                                          _c_double_p, _c_int64_p, _c_double_p]
        lib.rs_floor_z.restype = None
        lib.rs_floor_z.argtypes = [vp, i64, i64, ctypes.c_int, dbl, dbl, dbl, dbl, dbl, _c_double_p]
        lib.rs_center_y.restype = None
        lib.rs_center_y.argtypes = [vp, i64, i64, ctypes.c_int, dbl, dbl, dbl, _c_double_p]
        lib.rs_corridor_coordinates.restype = None
        lib.rs_corridor_coordinates.argtypes = [_c_float_p, i64, dbl, dbl, dbl, dbl, dbl, dbl, dbl, dbl, dbl,
                                                _c_double_p, _c_double_p]
        lib.rs_visibility.restype = dbl
        lib.rs_visibility.argtypes = [_c_float_p, i64, dbl, dbl, dbl, dbl, i64]
        flt = ctypes.c_float
        lib.rs_floor_band.restype = i64
        lib.rs_floor_band.argtypes = [_c_float_p, i64, flt, flt, dbl, dbl, dbl, dbl, _c_double_p, i64,
                                      _c_double_p, _c_int64_p, _c_int64_p]
        lib.rs_rails_band.restype = i64
        lib.rs_rails_band.argtypes = [_c_float_p, _c_double_p, i64, flt, flt, ctypes.c_int, dbl, dbl, dbl, dbl,
                                      _c_double_p, _c_double_p, _c_double_p]
        lib.rs_walls_band.restype = i64
        lib.rs_walls_band.argtypes = [_c_float_p, _c_double_p, i64, dbl, flt, flt, dbl, dbl, dbl, dbl, dbl,
                                      _c_float_p, _c_float_p, _c_double_p]
        lib.rs_verify_profile.restype = None
        lib.rs_verify_profile.argtypes = [_c_float_p, _c_double_p, i64, flt, flt, dbl, dbl, dbl, dbl, dbl,
                                          _c_double_p, i64, _c_int64_p, _c_double_p, _c_int64_p, _c_int64_p]
        lib.rs_select.restype = i64
        lib.rs_select.argtypes = [i64, ctypes.POINTER(_Cond), ctypes.c_int32, _c_int64_p]
        return lib, path
    return None, None


_lib, LIBRARY = _load()
AVAILABLE = _lib is not None
_enabled = AVAILABLE and os.environ.get("RESENSE_NATIVE", "1").strip().lower() not in ("0", "false", "no", "off")


def enabled() -> bool:
    """True when the native kernels are loaded and switched on."""
    return _enabled


def set_enabled(on: bool) -> bool:
    """Switch the native kernels on or off at run time (a no-op without the library); returns
    the previous state."""
    global _enabled
    prev = _enabled
    _enabled = bool(on) and AVAILABLE
    return prev


def status() -> str:
    """One line for logs: which path the per-frame kernels take."""
    if not AVAILABLE:
        return "numpy (native kernels not built)"
    return f"native ({os.path.basename(LIBRARY)})" if _enabled else "numpy (RESENSE_NATIVE=0)"


def _ptr(a: np.ndarray, t):
    return a.ctypes.data_as(t)


def _vector(X):
    """(array, is_f64, byte stride) for a 1-D float32 / float64 array worth a native call."""
    if not (_enabled and isinstance(X, np.ndarray) and X.ndim == 1 and X.size >= MIN_SIZE):
        return None
    if X.dtype == np.float64:
        f64 = 1
    elif X.dtype == np.float32:
        f64 = 0
    else:
        return None
    if X.strides[0] <= 0:
        return None
    return X, f64, X.strides[0]


def _cloud(xyz) -> Optional[np.ndarray]:
    if not (_enabled and isinstance(xyz, np.ndarray) and xyz.dtype == np.float32 and xyz.ndim == 2
            and xyz.shape[1] == 3 and xyz.flags.c_contiguous and xyz.shape[0] >= MIN_SIZE):
        return None
    return xyz


def bin_percentile(values, bins, nb: int, percentile: float, min_points: int, payload=None):
    """``resense.track.bin_percentile`` or None."""
    if not (_enabled and isinstance(values, np.ndarray) and values.dtype == np.float64 and values.ndim == 1
            and isinstance(bins, np.ndarray) and bins.ndim == 1 and bins.size == values.size
            and bins.dtype.kind in "iu" and values.size >= 64 and 0.0 <= float(percentile) <= 100.0):
        return None
    if payload is not None and not (isinstance(payload, np.ndarray) and payload.dtype == np.float64
                                    and payload.shape == values.shape):
        return None
    nb = int(nb)
    v = np.ascontiguousarray(values)
    b = np.ascontiguousarray(bins, dtype=np.int64)
    prof = np.full(nb, np.nan)
    counts = np.zeros(nb, dtype=np.int64)
    pay = np.ascontiguousarray(payload) if payload is not None else None
    pout = np.full(nb, np.nan) if payload is not None else None
    rc = _lib.rs_bin_percentile(_ptr(v, _c_double_p), _ptr(b, _c_int64_p), v.size, nb, float(percentile),
                                max(1, int(min_points)), None if pay is None else _ptr(pay, _c_double_p),
                                _ptr(prof, _c_double_p), _ptr(counts, _c_int64_p),
                                None if pout is None else _ptr(pout, _c_double_p))
    if rc != 0:
        return None
    counts = counts.astype(np.intp, copy=False)
    return (prof, counts, pout) if payload is not None else (prof, counts)


def floor_z(X, floor_range, coef) -> Optional[np.ndarray]:
    """``TrackModel.floor_z`` for a quadratic ``coef`` or None."""
    v = _vector(X)
    if v is None:
        return None
    arr, f64, stride = v
    a2, a1, a0 = (float(c) for c in coef)
    out = np.empty(arr.size, dtype=np.float64)
    _lib.rs_floor_z(arr.ctypes.data, arr.size, stride, f64, float(floor_range[0]), float(floor_range[1]),
                    a2, a1, a0, _ptr(out, _c_double_p))
    return out


def center_y(X, c: float, t: float, hk: float) -> Optional[np.ndarray]:
    """``TrackModel.center_y`` (``c + t X + hk X X``) or None."""
    v = _vector(X)
    if v is None:
        return None
    arr, f64, stride = v
    out = np.empty(arr.size, dtype=np.float64)
    _lib.rs_center_y(arr.ctypes.data, arr.size, stride, f64, c, t, hk, _ptr(out, _c_double_p))
    return out


def corridor_coordinates(xyz, floor_range, coef, rail_offset: float, c: float, t: float, hk: float):
    """``resense.gauge.corridor_coordinates`` (dy, h) or None."""
    if _cloud(xyz) is None:
        return None
    a2, a1, a0 = (float(x) for x in coef)
    n = xyz.shape[0]
    dy = np.empty(n, dtype=np.float64)
    h = np.empty(n, dtype=np.float64)
    _lib.rs_corridor_coordinates(_ptr(xyz, _c_float_p), n, float(floor_range[0]), float(floor_range[1]),
                                 a2, a1, a0, float(rail_offset), c, t, hk, _ptr(dy, _c_double_p), _ptr(h, _c_double_p))
    return dy, h


def visibility(xyz, c: float, t: float, hk: float, band: float, k: int) -> Optional[float]:
    """``resense.health.visibility_along_track`` or None."""
    if _cloud(xyz) is None:
        return None
    return float(_lib.rs_visibility(_ptr(xyz, _c_float_p), xyz.shape[0], c, t, hk, float(band), int(k)))


# -- selection prologues ------------------------------------------------------------------------

def _f32(v) -> Optional[float]:
    """A threshold that numpy compares with a float32 array in float32 on every numpy version: a
    finite Python float or a small Python int (a numpy float64 scalar compares in float64 on
    numpy 2 but in float32 on numpy 1.x, so it is left to numpy). None when it does not qualify."""
    if type(v) is float and math.isfinite(v) and abs(v) < 1e30:
        return v
    if type(v) is int and abs(v) <= 2 ** 24:
        return float(v)
    return None


def _xyz_zf(xyz, zf) -> bool:
    return (_cloud(xyz) is not None and isinstance(zf, np.ndarray) and zf.dtype == np.float64 and zf.ndim == 1
            and zf.size == xyz.shape[0] and zf.flags.c_contiguous)


def _edges(edges) -> Optional[np.ndarray]:
    e = np.ascontiguousarray(edges, dtype=np.float64)
    if e.ndim != 1 or e.size < 2 or not np.all(e[1:] > e[:-1]):
        return None                   # np.digitize also takes decreasing edges; the kernels do not
    return e


def floor_band(xyz, x0, x1, coefs, halfwidth: float, edges):
    """``_fit_floor``: (band size, Z of the band points in a bin as float64, their bin) or None."""
    lo, hi, e = _f32(x0), _f32(x1), _edges(edges)
    if lo is None or hi is None or e is None or _cloud(xyz) is None:
        return None
    n = xyz.shape[0]
    zb = np.empty(n, dtype=np.float64)
    bins = np.empty(n, dtype=np.int64)
    m = np.zeros(1, dtype=np.int64)
    nband = _lib.rs_floor_band(_ptr(xyz, _c_float_p), n, lo, hi, *coefs, float(halfwidth), _ptr(e, _c_double_p),
                               e.size, _ptr(zb, _c_double_p), _ptr(bins, _c_int64_p), _ptr(m, _c_int64_p))
    k = int(m[0])
    return int(nband), zb[:k].copy(), bins[:k].astype(np.intp, copy=True)


def rails_band(xyz, zf, x0, x1, prior_coefs, center: float, half: float):
    """``estimate_rails``: (X, Y in the prior's curve coordinates, h) of the selected near-range
    points, or None. ``prior_coefs`` is ``prior.center_coefs()`` (None without a prior)."""
    lo, hi = _f32(x0), _f32(x1)
    if lo is None or hi is None or not _xyz_zf(xyz, zf):
        return None
    n = xyz.shape[0]
    t, hk = (0.0, 0.0) if prior_coefs is None else (prior_coefs[1], prior_coefs[2])
    xs, ys, hs = (np.empty(n, dtype=np.float64) for _ in range(3))
    m = _lib.rs_rails_band(_ptr(xyz, _c_float_p), _ptr(zf, _c_double_p), n, lo, hi, int(prior_coefs is not None),
                           t, hk, float(center), float(half), _ptr(xs, _c_double_p), _ptr(ys, _c_double_p),
                           _ptr(hs, _c_double_p))
    return xs[:m].copy(), ys[:m].copy(), hs[:m].copy()


def walls_band(xyz, zf, rail_offset: float, x0, x1, b0: float, b1: float, coefs):
    """``estimate_axis_from_walls``: (X, Y as float32, dy) of the band points, or None."""
    lo, hi = _f32(x0), _f32(x1)
    if lo is None or hi is None or not _xyz_zf(xyz, zf):
        return None
    n = xyz.shape[0]
    xb, yb = np.empty(n, dtype=np.float32), np.empty(n, dtype=np.float32)
    dy = np.empty(n, dtype=np.float64)
    m = _lib.rs_walls_band(_ptr(xyz, _c_float_p), _ptr(zf, _c_double_p), n, float(rail_offset), lo, hi,
                           float(b0), float(b1), *coefs, _ptr(xb, _c_float_p), _ptr(yb, _c_float_p),
                           _ptr(dy, _c_double_p))
    return xb[:m].copy(), yb[:m].copy(), dy[:m].copy()


def verify_profile(xyz, zf, x0, x1, coefs, b0: float, b1: float, edges):
    """``verify_floor_extrapolation``: (n_sel, n_side, counts, base) or None."""
    lo, hi, e = _f32(x0), _f32(x1), _edges(edges)
    if lo is None or hi is None or e is None or not _xyz_zf(xyz, zf):
        return None
    nb = e.size - 1
    counts = np.zeros(nb, dtype=np.int64)
    base = np.full(nb, np.inf)
    ns, nd = np.zeros(1, dtype=np.int64), np.zeros(1, dtype=np.int64)
    _lib.rs_verify_profile(_ptr(xyz, _c_float_p), _ptr(zf, _c_double_p), xyz.shape[0], lo, hi, *coefs,
                           float(b0), float(b1), _ptr(e, _c_double_p), e.size, _ptr(counts, _c_int64_p),
                           _ptr(base, _c_double_p), _ptr(ns, _c_int64_p), _ptr(nd, _c_int64_p))
    return int(ns[0]), int(nd[0]), counts.astype(np.intp, copy=False), base


_OPS = {None: 0, ">": 1, ">=": 2, "<": 1, "<=": 2}


def select(n: int, *conds) -> Optional[np.ndarray]:
    """``np.flatnonzero`` of a conjunction of range tests, or None. Each condition is
    ``(array, lo_op, lo, hi_op, hi)`` or with a sixth element ``True`` for ``np.abs(array)``;
    ``lo_op`` is None, '>' or '>=', ``hi_op`` None, '<' or '<='. Arrays are 1-D float32 / float64
    of length ``n`` (any stride). The result does not depend on the order of the conditions; the
    kernel is fastest with the most selective one first."""
    if not _enabled or n < MIN_SIZE:
        return None
    arr = (_Cond * len(conds))()
    keep = []
    for q, c in zip(arr, conds):
        a, lo_op, lo, hi_op, hi = c[:5]
        if not (isinstance(a, np.ndarray) and a.ndim == 1 and a.size == n and a.dtype in (np.float32, np.float64)
                and a.strides[0] > 0) or lo_op not in (None, ">", ">=") or hi_op not in (None, "<", "<="):
            return None
        f64 = a.dtype == np.float64
        if f64:
            lo = None if lo_op is None else float(lo)
            hi = None if hi_op is None else float(hi)
        else:
            lo = None if lo_op is None else _f32(lo)
            hi = None if hi_op is None else _f32(hi)
            if (lo_op is not None and lo is None) or (hi_op is not None and hi is None):
                return None
        keep.append(a)
        q.data, q.stride, q.is_f64, q.absval = a.ctypes.data, a.strides[0], int(f64), int(len(c) > 5 and bool(c[5]))
        q.lo_op, q.hi_op, q.lo, q.hi = _OPS[lo_op], _OPS[hi_op], lo or 0.0, hi or 0.0
    out = np.empty(n, dtype=np.int64)
    m = _lib.rs_select(n, arr, len(conds), _ptr(out, _c_int64_p))
    return out[:m].astype(np.intp, copy=True)
