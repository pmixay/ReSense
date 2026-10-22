"""Reviewer's extended analytic first-return caster (own code; geometry follows
docs/evidence/f1a_b1_2026-10-20/raycast.py: lining R 2.7 m centred at (AY, AZ), bed at FLOOR, benches, two rails with a
0.07 m flat head and vertical faces, range noise 1 cm * (1 + r/100), Pandar128 grid from resense.sensor).

Additions (all off by default, so frame(...) with defaults reproduces raycast.frame bit for bit, checked by the caller):
  * per-rail head height functions (cant / one-sided rises): rail_top_l(x), rail_top_r(x) added to FLOOR + 0.18
  * horizontal curve: lateral offset yc(x) = x^2 / (2 R) of rails, bed edge, benches and lining (fixed-point solve)
  * convex polyhedral objects given as half-spaces (n . p <= c): yawed boxes, wedges, prisms, polygonal cylinders
  * per-ring azimuth offsets (deg), as a real Pandar128 has per-channel horizontal angle corrections
  * a custom ray set (e.g. a Falcon raster)
"""
from __future__ import annotations

import numpy as np

from resense.frame import Frame
from resense.sensor import AZIMUTH_FOV_DEG, AZIMUTH_STEP_DEG, RING_ELEVATION_DEG

R, AY, AZ, FLOOR = 2.7, 0.25, 0.8, -1.5


def rays(az_offsets_deg=None, fov=AZIMUTH_FOV_DEG, az_step=AZIMUTH_STEP_DEG, elev=RING_ELEVATION_DEG):
    az = np.arange(fov[0], fov[1] + 1e-9, az_step)
    el = np.asarray(elev, float)
    off = np.zeros(el.size) if az_offsets_deg is None else np.asarray(az_offsets_deg, float)
    A = np.radians(az[None, :] + off[:, None])
    E = np.radians(np.broadcast_to(el[:, None], A.shape))
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], axis=-1)
    return d.reshape(-1, 3)


def falcon_rays():
    """Seyond Falcon-like raster: outside-ROI grid 0.18 x 0.235 deg over +-60 x (-12.5..+12.5), ROI 0.088 x 0.06 over
    +-20 x (-3.98..+0.72) (resense.sensor FALCON_*). Mounted as the Hesai here (same height): geometry only."""
    out = []
    for (a0, a1, da), (e0, e1, de) in (((-60, 60, 0.18), (-12.5, 12.5, 0.235)), ((-20, 20, 0.088), (-3.98, 0.72, 0.06))):
        az = np.radians(np.arange(a0, a1 + 1e-9, da))
        el = np.radians(np.arange(e0, e1 + 1e-9, de))
        A, E = np.meshgrid(az, el)
        out.append(np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], -1).reshape(-1, 3))
    return np.concatenate(out)


def _surface_t(d, zfun, iters=6):
    t = np.full(d.shape[0], np.inf)
    down = d[:, 2] < -1e-6
    dd = d[down]
    tt = zfun(np.zeros(dd.shape[0])) / dd[:, 2]
    for _ in range(iters):
        tt = zfun(np.clip(dd[:, 0] * tt, -1e3, 1e3)) / dd[:, 2]
    t[down] = np.where(tt > 0, tt, np.inf)
    return t


def _plane_y_t(d, yfun, iters=6):
    """First t with d_y t = yfun(d_x t) (a vertical surface y = yfun(x)), fixed point from the straight solution."""
    with np.errstate(divide="ignore", invalid="ignore"):
        t = yfun(np.zeros(d.shape[0])) / d[:, 1]
        for _ in range(iters):
            t = yfun(np.clip(d[:, 0] * t, -1e3, 1e3)) / d[:, 1]
    return np.where(np.isfinite(t) & (t > 0), t, np.inf)


def poly_t(d, planes):
    """Entry t of rays from the origin into the convex polytope {p : n.p <= c} (planes: list of (n, c)); slab method."""
    tmin = np.full(d.shape[0], -np.inf)
    tmax = np.full(d.shape[0], np.inf)
    for n, c in planes:
        dn = d @ np.asarray(n, float)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = c / dn
        tmax = np.where(dn > 0, np.minimum(tmax, t), tmax)
        tmin = np.where(dn < 0, np.maximum(tmin, t), tmin)
        tmax = np.where((dn == 0) & (c < 0), -np.inf, tmax)
    ok = (tmax >= tmin) & (tmin > 0)
    return np.where(ok, tmin, np.inf)


def box_planes(x0, x1, y0, y1, z0, z1, yaw_deg=0.0):
    """Box (axis-aligned when yaw 0), yawed about its vertical centre axis."""
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    hx, hy = 0.5 * (x1 - x0), 0.5 * (y1 - y0)
    a = np.radians(yaw_deg)
    u = np.array([np.cos(a), np.sin(a), 0.0])
    v = np.array([-np.sin(a), np.cos(a), 0.0])
    c = np.array([cx, cy, 0.0])
    return [(u, u @ c + hx), (-u, -(u @ c) + hx), (v, v @ c + hy), (-v, -(v @ c) + hy),
            ((0, 0, 1), z1), ((0, 0, -1), -z0)]


def wedge_planes(x0, x1, y0, y1, z0, z_near, z_far):
    """Prism over [x0,x1]x[y0,y1] from z0 with a sloped top from z_near (at x0) to z_far (at x1)."""
    s = (z_far - z_near) / (x1 - x0)
    n = np.array([-s, 0.0, 1.0])
    c = z_near - s * x0          # z <= z_near + s (x - x0)  <=>  -s x + z <= z_near - s x0
    return [((1, 0, 0), x1), ((-1, 0, 0), -x0), ((0, 1, 0), y1), ((0, -1, 0), -y0), ((0, 0, -1), -z0), (n, c)]


def cyl_planes(axis, a0, a1, cy_or_cx, cz, radius, nseg=24):
    """Polygonal cylinder: axis 'x' (lying along the track, centre (y=cy, z=cz)) or 'y' (across, centre (x=cx, z=cz)),
    extent [a0, a1] along the axis."""
    out = []
    for k in range(nseg):
        t = 2 * np.pi * (k + 0.5) / nseg
        if axis == "x":
            n = np.array([0.0, np.cos(t), np.sin(t)])
            out.append((n, n @ np.array([0.0, cy_or_cx, cz]) + radius))
        else:
            n = np.array([np.cos(t), 0.0, np.sin(t)])
            out.append((n, n @ np.array([cy_or_cx, 0.0, cz]) + radius))
    e = np.eye(3)[0 if axis == "x" else 1]
    out += [(e, a1), (-e, -a0)]
    return out


def frame(d=None, profile=lambda x: 0.0 * x, rail_raise=lambda x: 0.0 * x, rail_top_l=None, rail_top_r=None,
          curve_r=0.0, boxes=(), polys=(), seed=0, sigma=0.01, stamp=0.0):
    rng = np.random.default_rng(seed)
    if d is None:
        d = rays()
    d = d.astype(np.float64)
    yc = (lambda x: 0.0 * x) if not curve_r else (lambda x: x * x / (2.0 * curve_r))
    best = np.full(d.shape[0], np.inf)
    # lining (curved: fixed point on the centre's lateral at the hit's x)
    ay = np.full(d.shape[0], AY)
    tc = np.full(d.shape[0], np.inf)
    for _ in range(1 if not curve_r else 6):
        a = d[:, 1] ** 2 + d[:, 2] ** 2
        b = -2.0 * (ay * d[:, 1] + AZ * d[:, 2])
        c = ay ** 2 + AZ ** 2 - R ** 2
        disc = b * b - 4 * a * c
        with np.errstate(invalid="ignore", divide="ignore"):
            tc = (-b + np.sqrt(np.maximum(disc, 0))) / (2 * a)
        tc = np.where((disc > 0) & (tc > 0), tc, np.inf)
        ay = AY + yc(np.clip(d[:, 0] * np.where(np.isfinite(tc), tc, 0), -1e3, 1e3))
    best = np.minimum(best, tc)
    tb = _surface_t(d, lambda x: FLOOR + profile(x))
    xb = d[:, 0] * np.where(np.isfinite(tb), tb, 0)
    yb = d[:, 1] * np.where(np.isfinite(tb), tb, 0)
    best = np.minimum(best, np.where(np.abs(yb - AY - yc(xb)) < R, tb, np.inf))
    for side in (-1.0, 1.0):
        tt = _surface_t(d, lambda x: FLOOR + 0.9 + profile(x))
        x = d[:, 0] * np.where(np.isfinite(tt), tt, 0)
        y = d[:, 1] * np.where(np.isfinite(tt), tt, 0)
        best = np.minimum(best, np.where((y - AY - yc(x)) * side > 1.95, tt, np.inf))
        tf = _plane_y_t(d, lambda x: AY + side * 1.95 + yc(x))
        xf, zf = d[:, 0] * np.where(np.isfinite(tf), tf, 0), d[:, 2] * np.where(np.isfinite(tf), tf, 0)
        okf = np.isfinite(tf) & (zf >= FLOOR + profile(xf)) & (zf <= FLOOR + 0.9 + profile(xf))
        best = np.minimum(best, np.where(okf, tf, np.inf))
    for yr, extra in ((AY - 0.8, rail_top_r), (AY + 0.8, rail_top_l)):
        def top(x, extra=extra):
            z = FLOOR + 0.18 + profile(x) + rail_raise(x)
            return z if extra is None else z + extra(x)
        tt = _surface_t(d, top)
        x = d[:, 0] * np.where(np.isfinite(tt), tt, 0)
        y = d[:, 1] * np.where(np.isfinite(tt), tt, 0)
        best = np.minimum(best, np.where(np.abs(y - yr - yc(x)) <= 0.035, tt, np.inf))
        for off in (-0.035, 0.035):
            tf = _plane_y_t(d, lambda x, off=off, yr=yr: yr + off + yc(x))
            xf, zf = d[:, 0] * np.where(np.isfinite(tf), tf, 0), d[:, 2] * np.where(np.isfinite(tf), tf, 0)
            okf = np.isfinite(tf) & (zf >= FLOOR + profile(xf)) & (zf <= top(xf))
            best = np.minimum(best, np.where(okf, tf, np.inf))
    for bx in boxes:
        best = np.minimum(best, poly_t(d, box_planes(*bx)))
    for pl in polys:
        best = np.minimum(best, poly_t(d, pl))
    ok = np.isfinite(best) & (best > 2.5) & (best < 210.0)
    t = best[ok] + rng.normal(0.0, sigma, size=int(ok.sum())) * (1.0 + best[ok] / 100.0)
    xyz = (d[ok] * t[:, None]).astype(np.float32)
    inten = np.clip(rng.normal(10.0, 1.0, size=xyz.shape[0]), 0, 255).astype(np.float32)
    return Frame(xyz=xyz, intensity=inten, ring=None, stamp=stamp, frame_id="np_synthetic")
