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
import os
from typing import Optional

import numpy as np

_ABI = 1
MIN_SIZE = 2048          # below this the numpy code is as fast (ctypes call ~ a few microseconds)

_c_double_p = ctypes.POINTER(ctypes.c_double)
_c_int64_p = ctypes.POINTER(ctypes.c_int64)
_c_float_p = ctypes.POINTER(ctypes.c_float)


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
            and bins.dtype.kind in "iu" and values.size >= 64):
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
