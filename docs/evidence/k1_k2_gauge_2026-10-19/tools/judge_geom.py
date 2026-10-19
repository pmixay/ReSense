"""Detector-independent geometry helpers for the jury scripts (vehicle frame X fwd, Y left, Z up)."""
import numpy as np


def fit_rails(xyz, x_range=(6.0, 30.0)):
    """Rail lines in the near field without the detector: scan yaw (-3..3 deg, 0.05) and a 0.15 m height
    band, take the y - tan(yaw) x histogram pair 1.59 +- 0.06 m apart with the most points in its weaker
    ridge; rail-head height as a line in x (80th percentile of the ridge points per 2 m).
    Returns dict(axis=f(x)->Y of the centre line, zr=f(x)->rail-head Z, yaw_deg, spacing, score) or None."""
    m = (xyz[:, 0] > x_range[0]) & (xyz[:, 0] < x_range[1]) & (np.abs(xyz[:, 1]) < 3)
    p = xyz[m]
    if len(p) < 500:
        return None
    z20 = np.percentile(p[:, 2], 20)
    best = (-1, 0, 0, 0, 0)
    bins = np.arange(-3, 3, 0.04)
    c = 0.5 * (bins[1:] + bins[:-1])
    for zlo in np.arange(z20 - 0.3, z20 + 0.5, 0.1):
        b = p[(p[:, 2] > zlo) & (p[:, 2] < zlo + 0.15)]
        if len(b) < 50:
            continue
        for yaw in np.arange(-3, 3, 0.1):
            t = np.tan(np.radians(yaw))
            h, _ = np.histogram(b[:, 1] - t * b[:, 0], bins=bins)
            # pairs i, i+k with c[i+k]-c[i] ~ 1.59 (k = 39 or 40 at 0.04 m bins)
            for k in (39, 40):
                s = np.minimum(h[:-k], h[k:])
                mid = 0.5 * (c[:-k] + c[k:])
                s = np.where(np.abs(mid) < 1.0, s, -1)
                j = int(np.argmax(s))
                if s[j] > best[0]:
                    best = (int(s[j]), yaw, zlo, c[j], c[j + k])
    if best[0] < 5:
        return None
    sc, yaw, zlo, yl, yr = best
    t = np.tan(np.radians(yaw))
    yp = p[:, 1] - t * p[:, 0]
    rh = p[((np.abs(yp - yl) < 0.05) | (np.abs(yp - yr) < 0.05)) & (p[:, 2] > zlo - 0.2) & (p[:, 2] < zlo + 0.35)]
    xs, zs = [], []
    for x0 in np.arange(x_range[0], x_range[1], 2.0):
        q = rh[(rh[:, 0] >= x0) & (rh[:, 0] < x0 + 2)]
        if len(q) > 3:
            xs.append(x0 + 1)
            zs.append(np.percentile(q[:, 2], 80))
    if len(xs) < 3:
        return None
    a, b = np.polyfit(xs, zs, 1)
    yc0 = 0.5 * (yl + yr)
    return {"axis": (lambda x: yc0 + t * np.asarray(x)), "zr": (lambda x: a * np.asarray(x) + b),
            "yaw_deg": float(yaw), "y0": float(yc0), "spacing": float(yr - yl), "score": sc,
            "z0": float(b), "pitch_slope": float(a)}
