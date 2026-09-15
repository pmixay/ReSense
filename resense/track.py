"""Per-frame track model: floor profile z_floor(X), rail head level and track axis Y_c(X).

* The floor profile absorbs sensor pitch and track grade (metro grades reach 4 %), which
  otherwise shifts the gauge by metres at 100+ m.
* The lateral axis and the rail-head height are self-calibrated from the two rail ridges
  seen in the near range (4-30 m), so the pipeline does not depend on the sensor mounting
  (the hackathon bags come from at least two different mounts).
* Yaw/curvature of the axis beyond the rail range is, in v0, a configured constant;
  estimating it from the tunnel walls is the main open research item (docs/RESEARCH.md).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from resense.config import TrackConfig


@dataclass
class TrackModel:
    floor_coef: np.ndarray           # polynomial coefficients (np.polyval order) of z_floor(X)
    floor_range: tuple               # (x_min, x_max) where the fit is supported by data
    center: float                    # lateral offset of the track axis at X=0 (m, + left)
    yaw: float                       # rad, corridor yaw
    curvature: float                 # 1/m
    rail_offset: float = 0.35        # rail head height above the floor (bed) reference
    rail_score: float = 0.0          # ridge prominence of the last rail detection (m)
    wall_quality: float = -1.0       # rms of the boundary fit that gave yaw/curvature (m)
    axis_valid: float = 1e9          # X up to which the axis is supported by observed boundaries
    n_bins: int = 0                  # number of floor bins used
    residual: float = 0.0            # rms residual of the floor fit (m)

    def floor_z(self, X) -> np.ndarray:
        """Bed reference height at along-track coordinate X, linearly extrapolated beyond
        the supported range (a quadratic extrapolated to 250 m is not trustworthy)."""
        X = np.asarray(X, dtype=np.float64)
        x0, x1 = self.floor_range
        Xc = np.clip(X, x0, x1)
        z = np.polyval(self.floor_coef, Xc)
        slope = np.polyval(np.polyder(self.floor_coef), Xc)
        return z + slope * (X - Xc)

    def rail_z(self, X) -> np.ndarray:
        """Rail head level (UGR) at X."""
        return self.floor_z(X) + self.rail_offset

    def center_y(self, X) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        return self.center + np.tan(self.yaw) * X + 0.5 * self.curvature * X * X

    def to_dict(self) -> dict:
        return {
            "floor_coef": [float(c) for c in self.floor_coef],
            "floor_range": [float(self.floor_range[0]), float(self.floor_range[1])],
            "center": round(float(self.center), 3), "yaw": float(self.yaw),
            "curvature": float(self.curvature), "rail_offset": round(float(self.rail_offset), 3),
            "rail_score": round(float(self.rail_score), 3), "wall_quality": round(float(self.wall_quality), 3),
            "axis_valid": round(float(min(self.axis_valid, 9999.0)), 1),
            "n_bins": int(self.n_bins),
            "residual": round(float(self.residual), 3),
        }


def default_track_model(cfg: TrackConfig, sensor_height: float = 1.5) -> TrackModel:
    return TrackModel(
        floor_coef=np.array([0.0, 0.0, -sensor_height]),
        floor_range=(cfg.floor_fit_range[0], cfg.floor_fit_range[1]),
        center=cfg.lateral_center, yaw=np.radians(cfg.yaw_deg), curvature=cfg.curvature,
        rail_offset=cfg.rail_offset_default,
    )


def _fit_floor(xyz: np.ndarray, cfg: TrackConfig, prior: TrackModel):
    """Robust per-bin percentile fit of the track bed. Returns (coef, range, n_bins, rms).

    Two stages: a line through the dense near bins (< 40 m), then far bins are accepted
    only if they agree with that line within ``floor_max_residual``; a quadratic is fitted
    only when enough consistent far bins exist. This avoids the quadratic blowing up when
    the bed is hidden at range (platforms, switches) and structure points take its place.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.floor_fit_range
    dy = Y - prior.center_y(X)
    band = (X >= x0) & (X < x1) & (np.abs(dy) < cfg.floor_halfwidth)
    Xb, Zb = X[band], Z[band]
    if Xb.size < cfg.floor_min_points * 3:
        return None
    # bins grow with range (2 m near, 2.5x beyond 40 m) so that the sparse far bed still fills them
    edges = np.concatenate([np.arange(x0, min(40.0, x1), cfg.floor_bin),
                            np.arange(max(40.0, x0), x1 + 2.5 * cfg.floor_bin, 2.5 * cfg.floor_bin)])
    idx = np.digitize(Xb, edges) - 1
    order = np.argsort(idx, kind="stable")
    idx_s, Z_s = idx[order], Zb[order]
    bounds = np.flatnonzero(np.diff(idx_s)) + 1
    starts = np.concatenate([[0], bounds])
    ends = np.concatenate([bounds, [idx_s.size]])
    xs, zs, ws = [], [], []
    for s, e in zip(starts, ends):
        n = e - s
        b = idx_s[s]
        if n < cfg.floor_min_points or b < 0 or b >= edges.size - 1:
            continue
        xs.append(0.5 * (edges[b] + edges[b + 1]))
        zs.append(np.percentile(Z_s[s:e], cfg.floor_percentile))
        ws.append(min(n, 200))
    if len(xs) < 3:
        return None
    xs, zs, ws = np.array(xs), np.array(zs), np.sqrt(np.array(ws, dtype=np.float64))
    near = xs < 40.0
    if near.sum() < 3:
        near = np.ones_like(near)
    line = np.polyfit(xs[near], zs[near], 1, w=ws[near])
    res = zs - np.polyval(line, xs)
    keep = np.abs(res) < cfg.floor_max_residual
    line = np.polyfit(xs[keep], zs[keep], 1, w=ws[keep]) if keep.sum() >= 3 else line
    res = zs - np.polyval(line, xs)
    keep = np.abs(res) < cfg.floor_max_residual
    xs, zs, ws = xs[keep], zs[keep], ws[keep]
    far_bins = int((xs > 40.0).sum())
    if cfg.floor_poly_degree >= 2 and far_bins >= 4 and xs.size >= 6:
        coef = np.polyfit(xs, zs, 2, w=ws)
        res = zs - np.polyval(coef, xs)
        # a quadratic that bends more than a 1500 m vertical curve is not a track profile
        if abs(coef[0]) > 1.0 / (2 * 1500.0):
            coef = np.concatenate([[0.0], np.polyfit(xs, zs, 1, w=ws)])
            res = zs - np.polyval(coef, xs)
    else:
        coef = np.concatenate([[0.0], np.polyfit(xs, zs, 1, w=ws)])
        res = zs - np.polyval(coef, xs)
    rms = float(np.sqrt(np.mean(res ** 2))) if res.size else 0.0
    return coef, (float(xs.min()), float(xs.max())), int(xs.size), rms


def _fit_side(xb: np.ndarray, yb: np.ndarray, cfg: TrackConfig, mean_abs_dy: float = 0.0):
    """Robust quadratic through one boundary; returns (c1, c2, rms, mean_abs_dy) or None."""
    if xb.size < cfg.walls_min_bins:
        return None
    coef = np.polyfit(xb, yb, 2)
    for _ in range(2):
        res = yb - np.polyval(coef, xb)
        keep = np.abs(res) < cfg.walls_max_residual
        if keep.sum() < cfg.walls_min_bins:
            return None
        coef = np.polyfit(xb[keep], yb[keep], 2)
        xb, yb = xb[keep], yb[keep]
    res = yb - np.polyval(coef, xb)
    rms = float(np.sqrt(np.mean(res ** 2)))
    if rms > cfg.walls_max_rms:
        return None
    return float(coef[1]), float(coef[0]), rms, float(mean_abs_dy), float(xb.max())


def estimate_axis_from_walls(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig):
    """Yaw (tan) and curvature of the track from the left/right tunnel boundaries.

    Walls, column rows and cable ducts run parallel to the track, so their curvature is the
    track's curvature (Shen et al. 2024 "parallel references"). Per along-track bin the
    boundary of each side is a high percentile of |dy| in a height band above the platform
    level; each side is fitted with a robust quadratic and the two are averaged by fit quality.
    Returns (tan_yaw, curvature, quality) or None.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.walls_range
    h = Z - model.rail_z(X)
    band = (X > x0) & (X < x1) & (h > cfg.walls_band[0]) & (h < cfg.walls_band[1])
    if band.sum() < 50:
        return None
    Xb, Yb = X[band], Y[band]
    dy = Yb - model.center_y(Xb)
    edges = np.arange(x0, x1 + cfg.walls_bin, cfg.walls_bin)
    idx = np.digitize(Xb, edges) - 1
    sides = {}
    for name, sel in (("left", dy > 0), ("right", dy < 0)):
        xs, ys, ds = [], [], []
        ii, yy, dd = idx[sel], Yb[sel], np.abs(dy[sel])
        order = np.argsort(ii, kind="stable")
        ii, yy, dd = ii[order], yy[order], dd[order]
        bounds = np.flatnonzero(np.diff(ii)) + 1
        for s_, e_ in zip(np.concatenate([[0], bounds]), np.concatenate([bounds, [ii.size]])):
            b = ii[s_]
            if e_ - s_ < cfg.walls_min_points or b < 0 or b >= edges.size - 1:
                continue
            q = np.percentile(dd[s_:e_], cfg.walls_percentile)
            # boundary in absolute Y: the point whose |dy| is closest to the percentile
            j = s_ + int(np.argmin(np.abs(dd[s_:e_] - q)))
            xs.append(0.5 * (edges[b] + edges[b + 1]))
            ys.append(yy[j])
            ds.append(dd[j])
        fit = _fit_side(np.array(xs), np.array(ys), cfg, float(np.mean(ds)) if ds else 0.0)
        if fit is not None:
            sides[name] = fit
    if not sides:
        return None
    # Prefer the boundary that runs closest to the track: near structures (column rows,
    # cable ducts, the near wall) are constrained by the gauge to be parallel to the track,
    # far walls are not (caverns, stations, diverging tunnels).
    if len(sides) == 2 and abs(sides["left"][1] - sides["right"][1]) > 1.0 / 3000.0:
        nearer = min(sides, key=lambda k: sides[k][3])
        sides = {nearer: sides[nearer]}
    w = np.array([1.0 / (f[2] ** 2 + 1e-4) for f in sides.values()])
    c1 = float(np.sum(w * [f[0] for f in sides.values()]) / w.sum())
    c2 = float(np.sum(w * [f[1] for f in sides.values()]) / w.sum())
    c1 = float(np.clip(c1, -cfg.walls_max_yaw, cfg.walls_max_yaw))
    c2 = float(np.clip(c2, -0.5 / cfg.walls_min_radius, 0.5 / cfg.walls_min_radius))
    quality = float(min(f[2] for f in sides.values()))
    x_valid = float(max(f[4] for f in sides.values()))
    return c1, c2, quality, x_valid


def estimate_rails(xyz: np.ndarray, floor: TrackModel, cfg: TrackConfig,
                   prior_center: float) -> Tuple[float, float, float]:
    """Find the two rail-head ridges in the lateral height profile of the near range.

    Returns (score, center, rail_head_height). ``score`` is the ridge prominence (m) of the
    weaker rail; a negative score means nothing plausible was found.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.rails_range
    half, step = cfg.rails_search_halfwidth, cfg.rails_bin
    h = Z - floor.floor_z(X)
    sel = (X > x0) & (X < x1) & (np.abs(Y - prior_center) < half) & (h > -0.4) & (h < 0.8)
    if sel.sum() < 200:
        return -1.0, prior_center, floor.rail_offset
    y, hh = Y[sel], h[sel]
    edges = np.arange(prior_center - half, prior_center + half + step, step)
    nb = edges.size - 1
    idx = np.clip(np.digitize(y, edges) - 1, 0, nb - 1)
    order = np.argsort(idx, kind="stable")
    idx_s, h_s = idx[order], hh[order]
    bounds = np.flatnonzero(np.diff(idx_s)) + 1
    starts = np.concatenate([[0], bounds])
    ends = np.concatenate([bounds, [idx_s.size]])
    prof = np.full(nb, np.nan)
    for s, e in zip(starts, ends):
        if e - s >= 8:
            prof[idx_s[s]] = np.percentile(h_s[s:e], cfg.rails_percentile)
    yc = edges[:-1] + step / 2
    k = max(1, int(round(0.25 / step)))
    ridge = np.full(nb, np.nan)
    ridge[k:nb - k] = prof[k:nb - k] - 0.5 * (prof[:nb - 2 * k] + prof[2 * k:])
    half_sp = int(round(0.5 * cfg.rails_spacing / step))
    lo, hi = cfg.rails_head_height
    best = (-1.0, prior_center, floor.rail_offset)
    for b in range(half_sp, nb - half_sp):
        bl, br = b - half_sp, b + half_sp
        rl, rr = ridge[bl], ridge[br]
        if not (np.isfinite(rl) and np.isfinite(rr)):
            continue
        if not (lo < prof[bl] < hi and lo < prof[br] < hi):
            continue
        sc = float(min(rl, rr))
        if sc > best[0]:
            best = (sc, float(yc[b]), float(0.5 * (prof[bl] + prof[br])))
    return best


def estimate_track(xyz: np.ndarray, cfg: TrackConfig, prev: Optional[TrackModel] = None) -> TrackModel:
    """Fit floor + rails + boundary-based yaw/curvature for one frame, smoothing against the
    previous model."""
    prior = prev if prev is not None else default_track_model(cfg)
    fit = _fit_floor(xyz, cfg, prior)
    if fit is None:
        return prior
    coef, frange, n_bins, rms = fit
    if prev is not None and cfg.floor_smoothing > 0:
        a = cfg.floor_smoothing
        coef = a * prev.floor_coef + (1 - a) * coef
    model = TrackModel(
        floor_coef=coef, floor_range=frange, center=prior.center, yaw=prior.yaw,
        curvature=prior.curvature, rail_offset=prior.rail_offset, n_bins=n_bins, residual=rms,
        wall_quality=prior.wall_quality, axis_valid=prior.axis_valid,
    )
    if cfg.rails_enabled:
        score, center, rail_h = estimate_rails(xyz, model, cfg, prior.center)
        model.rail_score = score
        if score >= cfg.rails_min_score:
            a = cfg.rails_smoothing if prev is not None else 0.0
            model.center = a * prior.center + (1 - a) * center
            model.rail_offset = a * prior.rail_offset + (1 - a) * rail_h
    if cfg.walls_enabled:
        est = estimate_axis_from_walls(xyz, model, cfg)
        if est is not None:
            tan_yaw, curv, q, x_valid = est
            a = cfg.walls_smoothing if prev is not None else 0.0
            model.yaw = a * prior.yaw + (1 - a) * np.arctan(tan_yaw)
            model.curvature = a * prior.curvature + (1 - a) * curv
            model.wall_quality = q
            model.axis_valid = x_valid + cfg.axis_valid_margin
            if abs(model.curvature) < 1e-4 and q < 0.2:
                model.axis_valid += cfg.axis_valid_straight_bonus
        else:
            # keep previous yaw/curvature (the corridor does not jump on a bad frame) but
            # shrink the trusted range
            model.axis_valid = max(cfg.walls_range[0] + cfg.axis_valid_margin, prior.axis_valid - 20.0)
    else:
        model.yaw = np.radians(cfg.yaw_deg)
        model.curvature = cfg.curvature
        model.axis_valid = 1e9
    return model
