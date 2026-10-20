"""Analytic numpy ray caster (no open3d): rail bed + rails, optional round tunnel,
optional open-air ground/masts, optional own-train body behind the sensor.
Geometry follows resense.synthetic.synthetic_tunnel_frame (floor -1.5, rails +-0.8 about
axis_y 0.25, 0.07 wide x 0.18 tall, tunnel R 2.7 about (0.25, 0.8))."""
import numpy as np
from resense.sensor import RING_ELEVATION_DEG
from resense.frame import Frame


def rays(az_lo=-50.0, az_hi=50.0, az_step=0.1, elev=RING_ELEVATION_DEG):
    az = np.radians(np.arange(az_lo, az_hi + 1e-9, az_step))
    el = np.radians(np.asarray(elev))
    A, E = np.meshgrid(az, el)
    ring = np.repeat(np.arange(len(el)), len(az)).astype(np.uint16)
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], -1).reshape(-1, 3)
    return d, ring


def _box(d, lo, hi):
    with np.errstate(divide="ignore", invalid="ignore"):
        inv = 1.0 / d
        t1 = lo * inv
        t2 = hi * inv
    tmin = np.nanmax(np.minimum(t1, t2), axis=1)
    tmax = np.nanmin(np.maximum(t1, t2), axis=1)
    hit = (tmax >= np.maximum(tmin, 0)) & (tmin > 0)
    return np.where(hit, tmin, np.inf)


def cast(d, tunnel=True, open_air=False, train_behind=False, roof_z=-0.3, floor_z=-1.5,
         axis_y=0.25, masts=True, specs=(), L=250.0):
    t = np.full(len(d), np.inf)
    gid = np.zeros(len(d), int)
    def take(tt, g):
        nonlocal t, gid
        m = tt < t
        t = np.where(m, tt, t)
        gid = np.where(m, g, gid)
    # bed box (top at floor_z), 5.4 m wide like the synthetic slab
    take(_box(d, np.array([-L, axis_y - 2.7, floor_z - 0.3]), np.array([L, axis_y + 2.7, floor_z])), 1)
    for side in (-0.8, 0.8):
        take(_box(d, np.array([-L, axis_y + side - 0.035, floor_z]), np.array([L, axis_y + side + 0.035, floor_z + 0.18])), 2)
    if tunnel:
        for side in (-1.0, 1.0):
            y0 = axis_y + (side * 1.95 if side > 0 else side * 1.95 - 1.2)
            take(_box(d, np.array([-L, y0, floor_z]), np.array([L, y0 + 1.2, floor_z + 0.9])), 3)
        # cylinder about X through (axis_y, 0.8): origin inside -> positive root
        yc, zc, R = axis_y, 0.8, 2.7
        a = d[:, 1] ** 2 + d[:, 2] ** 2
        b = -2 * (d[:, 1] * yc + d[:, 2] * zc)
        c = yc ** 2 + zc ** 2 - R ** 2
        disc = b * b - 4 * a * c
        with np.errstate(invalid="ignore", divide="ignore"):
            tt = (-b + np.sqrt(disc)) / (2 * a)
        tt = np.where(np.isfinite(tt) & (tt > 0) & (np.abs(tt * d[:, 0]) < L), tt, np.inf)
        take(tt, 0)
    if open_air:
        # ground outside the bed 0.3 m lower, out to +-60 m laterally
        take(_box(d, np.array([-L, -60.0, floor_z - 0.6]), np.array([L, 60.0, floor_z - 0.3])), 4)
        if masts:
            for x0 in np.arange(-200.0, 251.0, 60.0):
                for y0 in (axis_y - 3.5, axis_y + 3.5):
                    take(_box(d, np.array([x0 - 0.15, y0 - 0.15, floor_z - 0.3]), np.array([x0 + 0.15, y0 + 0.15, 4.5])), 5)
    if train_behind:
        take(_box(d, np.array([-25.0, -1.5, floor_z + 0.4]), np.array([-0.8, 1.5, roof_z])), 6)
    for k, (x0, y0, w, h) in enumerate(specs):   # standing boxes on the bed: (x, lateral, width, height)
        take(_box(d, np.array([x0, axis_y + y0 - w / 2, floor_z]), np.array([x0 + 0.4, axis_y + y0 + w / 2, floor_z + h])), 10 + k)
    return t, gid


def frame(d, ring, t, gid, stamp=0.0, seed=0, rmin=1.0, rmax=210.0, with_ring=True):
    rng = np.random.default_rng(seed)
    ok = np.isfinite(t) & (t > rmin) & (t < rmax)
    tt = t[ok] + rng.normal(0, 0.01, ok.sum()) * (1 + t[ok] / 100)
    xyz = (d[ok] * tt[:, None]).astype(np.float32)
    inten = np.where(gid[ok] == 0, 12.0, 8.0).astype(np.float32)
    return Frame(xyz=xyz, intensity=inten, ring=ring[ok].copy() if with_ring else None, stamp=stamp,
                 frame_id="synthetic", meta={}), gid[ok]
