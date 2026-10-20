"""Numpy stand-in for resense.synthetic.synthetic_tunnel_frame (open3d is not installed here).

Same geometry as the repo's synthetic tunnel (round lining r 2.7 about (axis_y, axis_z), bed top at floor_z,
benches 0.9 m high at +-1.95 m, rails 0.07 wide / 0.18 tall at +-0.8 m), plus
  * ``profile(X)``: vertical offset of bed, rails and benches along X (a grade change),
  * ``rail_raise(X)``: extra height of the rail heads above the bed along X,
  * boxes: list of (x0, x1, y0, y1, z0, z1) in the vehicle frame (z absolute).
Ranges get Gaussian noise sigma * (1 + t / 100), as the repo's generator.
"""
from __future__ import annotations

import numpy as np

from resense.frame import Frame
from resense.sensor import ray_directions

R, AY, AZ, FLOOR = 2.7, 0.25, 0.8, -1.5


def _box_t(o, d, box):
    x0, x1, y0, y1, z0, z1 = box
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / d
        t1 = (np.array([x0, y0, z0]) - o) * inv
        t2 = (np.array([x1, y1, z1]) - o) * inv
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    ok = (tmax >= tmin) & (tmin > 0)
    return np.where(ok, tmin, np.inf)


def _surface_t(d, zfun, iters=6):
    """First t > 0 with d_z t = zfun(d_x t) for a downward ray (fixed point; gentle profiles)."""
    t = np.full(d.shape[0], np.inf)
    down = d[:, 2] < -1e-6
    dd = d[down]
    tt = zfun(np.zeros(dd.shape[0])) / dd[:, 2]
    for _ in range(iters):
        tt = zfun(np.clip(dd[:, 0] * tt, -1e3, 1e3)) / dd[:, 2]
    t[down] = np.where(tt > 0, tt, np.inf)
    return t


def frame(profile=lambda x: 0.0 * x, rail_raise=lambda x: 0.0 * x, boxes=(), seed=0, sigma=0.01,
          stamp=0.0, extra_rails=()):
    rng = np.random.default_rng(seed)
    d = ray_directions().astype(np.float64)
    o = np.zeros(3)
    best = np.full(d.shape[0], np.inf)
    # lining (from inside: the far root)
    a = d[:, 1] ** 2 + d[:, 2] ** 2
    b = -2.0 * (AY * d[:, 1] + AZ * d[:, 2])
    c = AY ** 2 + AZ ** 2 - R ** 2
    disc = b * b - 4 * a * c
    with np.errstate(invalid="ignore", divide="ignore"):
        tc = (-b + np.sqrt(np.maximum(disc, 0))) / (2 * a)
    best = np.minimum(best, np.where((disc > 0) & (tc > 0), tc, np.inf))
    # bed top (within the lining)
    tb = _surface_t(d, lambda x: FLOOR + profile(x))
    yb = d[:, 1] * np.where(np.isfinite(tb), tb, 0)
    best = np.minimum(best, np.where(np.abs(yb - AY) < R, tb, np.inf))
    # bench tops and inner faces
    for side in (-1.0, 1.0):
        tt = _surface_t(d, lambda x: FLOOR + 0.9 + profile(x))
        y = d[:, 1] * np.where(np.isfinite(tt), tt, 0)
        inside = (y - AY) * side > 1.95
        best = np.minimum(best, np.where(inside, tt, np.inf))
        yf = AY + side * 1.95
        with np.errstate(divide="ignore", invalid="ignore"):
            tf = yf / d[:, 1]
        xf, zf = d[:, 0] * tf, d[:, 2] * tf
        okf = (tf > 0) & (zf >= FLOOR + profile(xf)) & (zf <= FLOOR + 0.9 + profile(xf))
        best = np.minimum(best, np.where(okf, tf, np.inf))
    # rails: heads (top surface) and the two vertical faces
    for yr in [AY - 0.8, AY + 0.8] + list(extra_rails):
        top = lambda x: FLOOR + 0.18 + profile(x) + rail_raise(x)
        tt = _surface_t(d, top)
        y = d[:, 1] * np.where(np.isfinite(tt), tt, 0)
        best = np.minimum(best, np.where(np.abs(y - yr) <= 0.035, tt, np.inf))
        for yf in (yr - 0.035, yr + 0.035):
            with np.errstate(divide="ignore", invalid="ignore"):
                tf = yf / d[:, 1]
            xf, zf = d[:, 0] * tf, d[:, 2] * tf
            okf = (tf > 0) & (zf >= FLOOR + profile(xf)) & (zf <= top(xf))
            best = np.minimum(best, np.where(okf, tf, np.inf))
    for box in boxes:
        best = np.minimum(best, _box_t(o, d, box))
    ok = np.isfinite(best) & (best > 2.5) & (best < 210.0)
    t = best[ok] + rng.normal(0.0, sigma, size=int(ok.sum())) * (1.0 + best[ok] / 100.0)
    xyz = (d[ok] * t[:, None]).astype(np.float32)
    inten = np.clip(rng.normal(10.0, 1.0, size=xyz.shape[0]), 0, 255).astype(np.float32)
    return Frame(xyz=xyz, intensity=inten, ring=None, stamp=stamp, frame_id="np_synthetic")


def rail_head_z(x, profile=lambda x: 0.0 * x, rail_raise=lambda x: 0.0 * x):
    return FLOOR + 0.18 + profile(np.asarray(x, dtype=float)) + rail_raise(np.asarray(x, dtype=float))
