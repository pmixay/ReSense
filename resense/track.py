"""Per-frame track model: floor profile z_floor(X), rail head level and track axis Y_c(X).

* The floor profile absorbs sensor pitch and track grade (metro grades reach 4 %), which
  otherwise shifts the gauge by metres at 100+ m.
* The lateral axis and the rail-head height are self-calibrated from the two rail ridges
  seen in the near range (4-30 m), so the pipeline does not depend on the sensor mounting
  (the hackathon bags come from at least two different mounts). The ridge profile is built
  in the lateral coordinate of the previous axis (its yaw and curvature removed), so that in
  a curve the rails are straight lines in the profile instead of a 0.5 m smear (v0.5).
* The yaw of the axis at the vehicle comes from the same rail pair measured per along-track
  slab (v0.5): the rails are the sharpest parallel reference there is. The tunnel boundaries
  (walls, column rows, ducts) then contribute the curvature only; a free quadratic through a
  diverging or interrupted boundary traded yaw against curvature and jittered by up to a
  degree per frame on the organizer bags (docs/EXPERIMENTS.md section 1b). Yaw and
  curvature are rate-limited frame to frame.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

import numpy as np

from resense import _native
from resense.config import TrackConfig


@dataclass
class TrackModel:
    floor_coef: np.ndarray           # polynomial coefficients (np.polyval order) of z_floor(X)
    floor_range: tuple               # (x_min, x_max) where the fit is supported by data
    center: float                    # lateral offset of the track axis at X=0 (m, + left)
    yaw: float                       # rad, corridor yaw
    curvature: float                 # 1/m (1/R, + = left)
    rail_offset: float = 0.35        # rail head height above the floor (bed) reference
    rail_score: float = 0.0          # ridge prominence of the last rail detection (m)
    wall_quality: float = -1.0       # rms of the boundary fit that gave the curvature (m)
    axis_valid: float = 1e9          # X up to which the axis is supported by observed boundaries
    n_bins: int = 0                  # number of floor bins used
    residual: float = 0.0            # rms residual of the floor fit (m)
    floor_verified: float = 0.0      # X up to which the extrapolated bed is confirmed by the side-structure base
    rail_slabs: int = 0              # v0.5: near-range slabs in which the rail pair was found (yaw support)
    axis_sides: int = 0              # v0.5: tunnel boundaries fitted this frame (0, 1 or 2)
    age: int = 0                     # v0.6: frames since the model was seeded (rate limits apply after the warm-up)
    floor_shadow: float = 0.0        # 25.09: X where a near occluder's shadow starts in the bed band (0 = none; floor_shadow_height)
    floor_held: bool = False         # 25.09: the bed profile was held from the previous frame (too little bed in front of the shadow)
    far_support_run: int = 0         # 25.09: consecutive frames with the walls_min_far_support condition (not reported)
    axis_valid_both: float = 1e9     # 25.09: X up to which BOTH fitted boundaries support the axis (= axis_valid with one or none); read only with cluster.far_axis_both_sides 1, not serialised
    axis_valid_bent: float = 1e9     # 25.09: the same without the straight bonus, on a bent axis with two boundaries only (1e9 otherwise); cluster.far_axis_both_sides 2, not serialised

    def floor_z(self, X) -> np.ndarray:
        """Bed reference height at along-track coordinate X, linearly extrapolated beyond
        the supported range (a quadratic extrapolated to 250 m is not trustworthy)."""
        c = np.asarray(self.floor_coef, dtype=np.float64)
        if c.size == 3 and _native.enabled():     # the same arithmetic in one pass (resense/_native.py)
            z = _native.floor_z(X, self.floor_range, c)
            if z is not None:
                return z
        X = np.asarray(X, dtype=np.float64)
        x0, x1 = self.floor_range
        Xc = np.clip(X, x0, x1)
        if c.size == 3:                           # the common case, written out (2x faster than polyval)
            a2, a1, a0 = c
            return (a2 * Xc + a1) * Xc + a0 + (2.0 * a2 * Xc + a1) * (X - Xc)
        z = np.polyval(c, Xc)
        slope = np.polyval(np.polyder(c), Xc)
        return z + slope * (X - Xc)

    def rail_z(self, X) -> np.ndarray:
        """Rail head level (UGR) at X."""
        return self.floor_z(X) + self.rail_offset

    def center_y(self, X) -> np.ndarray:
        if _native.enabled():
            y = _native.center_y(X, *self.center_coefs())
            if y is not None:
                return y
        X = np.asarray(X, dtype=np.float64)
        return self.center + np.tan(self.yaw) * X + 0.5 * self.curvature * X * X

    def center_coefs(self) -> tuple:
        """(c, t, k2) with ``center_y(X) = c + t X + k2 X X``, exactly as ``center_y`` rounds them."""
        return float(self.center), float(np.tan(self.yaw)), float(0.5 * self.curvature)

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
            "floor_verified": round(float(self.floor_verified), 1),
            "rail_slabs": int(self.rail_slabs),
            "axis_sides": int(self.axis_sides),
            "age": int(self.age),
            # 25.09 (additive, only in a frame with a shadow: the output is unchanged otherwise)
            **({"floor_shadow": round(float(self.floor_shadow), 1), "floor_held": bool(self.floor_held)}
               if self.floor_shadow > 0 else {}),
        }


def default_track_model(cfg: TrackConfig, sensor_height: float = 1.5) -> TrackModel:
    return TrackModel(
        floor_coef=np.array([0.0, 0.0, -sensor_height]),
        floor_range=(cfg.floor_fit_range[0], cfg.floor_fit_range[1]),
        center=cfg.lateral_center, yaw=np.radians(cfg.yaw_deg), curvature=cfg.curvature,
        rail_offset=cfg.rail_offset_default,
    )


def bin_percentile(values: np.ndarray, bins: np.ndarray, nb: int, percentile: float, min_points: int = 1,
                   payload: Optional[np.ndarray] = None):
    """Per-bin percentile of ``values`` (linear interpolation, as ``np.percentile``), vectorised:
    one sort instead of a Python loop with a percentile call per bin. Returns (prof, counts)
    with ``prof`` NaN where a bin holds fewer than ``min_points`` values; with ``payload`` the
    payload of the value at the percentile rank is returned as a third array (nearest rank)."""
    if _native.enabled():                          # counting sort + selection, the same values (resense/_native.py)
        res = _native.bin_percentile(values, bins, nb, percentile, min_points, payload)
        if res is not None:
            return res
    prof = np.full(nb, np.nan)
    counts = np.bincount(bins, minlength=nb)[:nb]
    if values.size == 0:
        return (prof, counts, np.full(nb, np.nan)) if payload is not None else (prof, counts)
    order = np.lexsort((values, bins))
    v = values[order]
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    ok = counts >= max(1, int(min_points))
    pos = percentile / 100.0 * (counts[ok] - 1)
    lo = np.floor(pos).astype(int)
    frac = pos - lo
    i0 = starts[ok] + lo
    i1 = np.minimum(i0 + 1, starts[ok] + counts[ok] - 1)
    prof[ok] = v[i0] * (1.0 - frac) + v[i1] * frac
    if payload is not None:
        out = np.full(nb, np.nan)
        out[ok] = payload[order][np.where(frac > 0.5, i1, i0)]
        return prof, counts, out
    return prof, counts


def _floor_shadow(xs: np.ndarray, zs: np.ndarray, ref: TrackModel, cfg: TrackConfig):
    """The shadow of a large near object in the bed band (25.09, ``floor_shadow_height``).

    An object that fills the band (the organizers' 2 x 2 m box) hides the bed behind it: the
    bins there hold only the tunnel roof, 3-4 m above the bed, and once they outnumber the bed
    bins in front the line through the near bins tilts (set O, box at 9-26 m: the rail head at
    20 m 0.8-3.5 m off). The shadow starts at the first populated bin within ``floor_shadow_range``
    that lies more than ``floor_shadow_height`` above the previous frame's bed and is followed
    by another such bin. Then only bins within ``floor_max_residual`` of the previous bed are
    fitted, never the populated bin just before the shadow (the object's face, whose low
    percentile can still look like bed); with fewer than ``floor_shadow_min_bins`` of them in
    front of the shadow the previous bed is held. The object's face is the first bin before the
    shadow that is not bed (more than ``floor_max_residual`` off; an object raised above the bed
    lets the bed show under it for a few metres), else that populated bin just before the
    shadow. Returns (keep mask or None, shadow start X or 0, lower edge X of the face bin or 0,
    hold)."""
    d = zs - ref.floor_z(xs)
    high = d > cfg.floor_shadow_height
    start = np.flatnonzero(high[:-1] & high[1:] & (xs[:-1] < cfg.floor_shadow_range))
    if start.size == 0:
        return None, 0.0, 0.0, False
    s = int(start[0])
    x_s = float(xs[s] - 0.5 * cfg.floor_bin)                 # lower edge of the first shadowed bin
    keep = np.abs(d) < cfg.floor_max_residual
    off = np.flatnonzero(~keep[:s])
    f = int(off[0]) if off.size else s - 1
    x_face = float(xs[f] - 0.5 * cfg.floor_bin) if f >= 0 else x_s - cfg.floor_bin
    keep[max(s - 1, 0):s + 1] = False
    return keep, x_s, x_face, int((keep & (xs < x_s)).sum()) < cfg.floor_shadow_min_bins


FAR_LOW_BAND = 0.2            # m above a far bin's level: its low points
FAR_STANDING = (0.3, 1.5)     # m above the level: points standing on the low points (an object's face)
FAR_STANDING_MARGIN = 0.2     # m, lateral tolerance of "on the low points"


def _narrow_far_bins(xyz: np.ndarray, cfg: TrackConfig, prior: TrackModel, edges: np.ndarray,
                     prof: np.ndarray) -> np.ndarray:
    """Far bed bins that are the foot of an object, not the bed (25.09, ``floor_far_min_width``).

    Beyond ~90 m the real bed stops returning and the base of an object standing there can fill a
    bin: the fit then lengthens to it and the far curvature follows (EXPERIMENTS §2d). A bin whose
    centre lies at or beyond ``floor_far_from`` is dropped when its low points (at most
    ``FAR_LOW_BAND`` above the bin's level) span less than ``floor_far_min_width`` laterally and
    at least ``floor_far_min_standing`` points stand on them (``FAR_STANDING`` above the level,
    within ``FAR_STANDING_MARGIN`` of their lateral extent; 0 = every narrow far bin is dropped).
    A narrow far bin with nothing on it (a rail head or a patch of bed near the axis, the common
    real case) is kept. The band is recomputed here in numpy on the far points only, so the
    native and numpy paths agree. Returns the indices of the bins to drop."""
    centres = 0.5 * (edges[:-1] + edges[1:])
    far = np.flatnonzero(np.isfinite(prof) & (centres >= cfg.floor_far_from))
    if far.size == 0:
        return far
    X = xyz[:, 0]
    sel = (X >= edges[far[0]]) & (X < min(float(edges[far[-1] + 1]), cfg.floor_fit_range[1]))
    P = xyz[sel]
    Xs = P[:, 0].astype(np.float64)
    dy = P[:, 1] - prior.center_y(Xs)
    band = np.abs(dy) < cfg.floor_halfwidth
    Xs, dy, Z = Xs[band], dy[band], P[band, 2].astype(np.float64)
    idx = np.digitize(Xs, edges) - 1
    drop = []
    for b in far:
        inb = idx == b
        z, d = Z[inb], dy[inb]
        level = float(prof[b])
        low = z <= level + FAR_LOW_BAND
        if not low.any():
            continue
        lo, hi = float(d[low].min()), float(d[low].max())
        if hi - lo >= cfg.floor_far_min_width:
            continue                                  # spans the bed: the bed (or the bed with something on it)
        if cfg.floor_far_min_standing > 0:
            up = ((z > level + FAR_STANDING[0]) & (z < level + FAR_STANDING[1])
                  & (d >= lo - FAR_STANDING_MARGIN) & (d <= hi + FAR_STANDING_MARGIN))
            if int(up.sum()) < cfg.floor_far_min_standing:
                continue                              # narrow, nothing standing on it: a rail head or a bed patch
        drop.append(b)
    return np.asarray(drop, dtype=np.intp)


def _fit_floor(xyz: np.ndarray, cfg: TrackConfig, prior: TrackModel,
               shadow_ref: Optional[TrackModel] = None, info: Optional[dict] = None):
    """Robust per-bin percentile fit of the track bed. Returns (coef, range, n_bins, rms).

    Two stages: a line through the dense near bins (< 40 m), then far bins are accepted
    only if they agree with that line within ``floor_max_residual``; a quadratic is fitted
    only when enough consistent far bins exist. This avoids the quadratic blowing up when
    the bed is hidden at range (platforms, switches) and structure points take its place.
    With ``shadow_ref`` (the previous frame's model; ``floor_shadow_height`` > 0) the bins in
    the shadow of a large near object are left out first, or ``shadow_ref``'s bed is returned
    unchanged (:func:`_floor_shadow`); ``info`` then receives ``shadow``, ``face`` and ``hold``.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.floor_fit_range
    # bins grow with range (2 m near, 2.5x beyond 40 m) so that the sparse far bed still fills them
    edges = np.concatenate([np.arange(x0, min(40.0, x1), cfg.floor_bin),
                            np.arange(max(40.0, x0), x1 + 2.5 * cfg.floor_bin, 2.5 * cfg.floor_bin)])
    nb = edges.size - 1
    fast = (_native.floor_band(xyz, x0, x1, prior.center_coefs(), cfg.floor_halfwidth, edges)
            if _native.enabled() else None)                 # the band below in one pass (resense/_native.py)
    if fast is not None:
        n_band, Zin, idx_in = fast
    else:
        dy = Y - prior.center_y(X)
        band = (X >= x0) & (X < x1) & (np.abs(dy) < cfg.floor_halfwidth)
        Xb, Zb = X[band], Z[band]
        n_band = Xb.size
        idx = np.digitize(Xb, edges) - 1
        inb = (idx >= 0) & (idx < nb)
        Zin, idx_in = Zb[inb].astype(np.float64), idx[inb]
    if n_band < cfg.floor_min_points * 3:
        return None
    prof, counts = bin_percentile(Zin, idx_in, nb, cfg.floor_percentile, cfg.floor_min_points)
    if cfg.floor_far_min_width > 0:
        drop = _narrow_far_bins(xyz, cfg, prior, edges, prof)
        if drop.size:
            prof = np.array(prof, dtype=np.float64)
            prof[drop] = np.nan
    ok = np.isfinite(prof)
    if ok.sum() < 3:
        return None
    xs = 0.5 * (edges[:-1] + edges[1:])[ok]
    zs = prof[ok]
    ws = np.sqrt(np.minimum(counts[ok], 200).astype(np.float64))
    if shadow_ref is not None:
        keep, x_s, x_face, hold = _floor_shadow(xs, zs, shadow_ref, cfg)
        if info is not None:
            info["shadow"], info["face"], info["hold"] = x_s, x_face, hold
        if hold:
            return (np.array(shadow_ref.floor_coef, dtype=np.float64), tuple(shadow_ref.floor_range),
                    int(shadow_ref.n_bins), float(shadow_ref.residual))
        if keep is not None:
            xs, zs, ws = xs[keep], zs[keep], ws[keep]
    near = xs < 40.0
    if near.sum() < 3:
        near = np.ones_like(near)
    line = np.polyfit(xs[near], zs[near], 1, w=ws[near])
    res = zs - np.polyval(line, xs)
    keep = np.abs(res) < cfg.floor_max_residual
    line = np.polyfit(xs[keep], zs[keep], 1, w=ws[keep]) if keep.sum() >= 3 else line
    res = zs - np.polyval(line, xs)
    keep = np.abs(res) < cfg.floor_max_residual
    if keep.sum() < 3:
        return None                               # no consistent bed (an inverted or blinded cloud): keep the prior
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


# ---------------------------------------------------------------------------
# tunnel boundaries -> curvature (and yaw when the rails give none)
# ---------------------------------------------------------------------------

def _quad(xb: np.ndarray, yb: np.ndarray, t_fixed: Optional[float]):
    """Least squares of ``y = a + t x + k x^2 / 2`` (``k`` = curvature 1/R); with ``t_fixed``
    the tangent is given (by the rails) and only ``a`` and ``k`` are free. Returns (a, t, k)."""
    if t_fixed is None:
        coef = np.polyfit(xb, yb, 2)                  # y = c0 x^2 + c1 x + c2
        return float(coef[2]), float(coef[1]), 2.0 * float(coef[0])
    A = np.stack([np.ones_like(xb), 0.5 * xb * xb], axis=1)
    sol, *_ = np.linalg.lstsq(A, yb - t_fixed * xb, rcond=None)
    return float(sol[0]), float(t_fixed), float(sol[1])


def _fit_side(xb: np.ndarray, yb: np.ndarray, cfg: TrackConfig, mean_abs_dy: float = 0.0,
              t_fixed: Optional[float] = None):
    """Robust quadratic through one boundary; returns (t, k, rms, mean_abs_dy, x_max, n_far,
    n_far_in) or None. ``k`` is the curvature 1/R of the boundary (the track's, when it is
    parallel). Bins further than ``walls_max_residual`` from the fit are dropped in two passes.
    With the tangent fixed by the rails, a boundary that is not parallel to the track (a
    diverging tunnel, a platform hall wall) cannot be fitted within ``walls_max_rms`` and is
    rejected instead of bending the axis. ``n_far`` / ``n_far_in``: the boundary bins beyond the
    rail range (``rails_range[1]``) and how many of them lie within ``walls_max_residual`` of the
    final fit (the far support of the fitted curvature, used by ``walls_min_far_support``)."""
    if xb.size < cfg.walls_min_bins:
        return None
    x_all, y_all = xb, yb
    a, t, k = _quad(xb, yb, t_fixed)
    for _ in range(2):
        res = yb - (a + t * xb + 0.5 * k * xb * xb)
        keep = np.abs(res) < cfg.walls_max_residual
        if keep.sum() < cfg.walls_min_bins:
            return None
        xb, yb = xb[keep], yb[keep]
        a, t, k = _quad(xb, yb, t_fixed)
    res = yb - (a + t * xb + 0.5 * k * xb * xb)
    rms = float(np.sqrt(np.mean(res ** 2)))
    if rms > cfg.walls_max_rms:
        return None
    far = x_all > cfg.rails_range[1]
    far_in = far & (np.abs(y_all - (a + t * x_all + 0.5 * k * x_all * x_all)) < cfg.walls_max_residual)
    return t, k, rms, float(mean_abs_dy), float(xb.max()), int(far.sum()), int(far_in.sum())


def _far_supported_side(sides: dict, cfg: TrackConfig) -> Optional[str]:
    """The side that alone should set the axis shape (``walls_min_far_support``, 25.09), or None.

    A boundary's curvature is extrapolated to the end of the corridor, so it should be carried
    by its bins beyond the rail range (the near 4-30 m, where the rails fix the axis). At a
    station the platform-side boundary can be a near structure (a platform screen, a column
    row) joined by the robust fit to one or two bins of the diverging hall end: the fit is
    within ``walls_max_rms`` but most of its far bins lie off it, and averaged with the other
    side it bent the axis ~0.8 m at 83 m in ``squareT_platform_squareT_switch`` (EXPERIMENTS
    §1h). When both sides are fitted with ``walls_min_bins`` or more far bins each, one keeps at
    least ``walls_min_far_support`` of them within ``walls_max_residual`` and the other does not,
    and the supported side is nearly straight (|k| <= ``walls_far_support_max_curvature``: a
    real R 350-1 000 m curve is never overruled), the supported side is returned."""
    judged = {}
    for name, f in sides.items():
        if f[5] >= cfg.walls_min_bins:
            judged[name] = f[6] >= cfg.walls_min_far_support * f[5]
    if len(judged) != 2 or sum(judged.values()) != 1:
        return None
    good = next(name for name, ok in judged.items() if ok)
    return good if abs(sides[good][1]) <= cfg.walls_far_support_max_curvature else None


def estimate_axis_from_walls(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig,
                             t_fixed: Optional[float] = None, floor_z_all: Optional[np.ndarray] = None,
                             far_support_run: int = 0):
    """Yaw (tan) and curvature of the track from the left/right tunnel boundaries.

    Walls, column rows and cable ducts run parallel to the track, so their curvature is the
    track's curvature (Shen et al. 2024 "parallel references"). Per along-track bin the
    boundary of each side is a high percentile of |dy| in a height band above the platform
    level; each side is fitted with a robust quadratic (tangent fixed to ``t_fixed`` when the
    rails gave one) and the two are averaged by fit quality; when they disagree the nearer
    boundary wins. Returns (tan_yaw, curvature, quality, x_valid, n_sides, disagreement,
    x_valid_min, run) or None; ``disagreement`` is the curvature difference of the two sides
    when both were fitted; ``x_valid`` / ``x_valid_min`` are the last observed bin of the longer
    / shorter side kept; ``run`` counts the consecutive frames (``far_support_run`` of the
    previous frame + 1, or 0) in which the ``walls_min_far_support`` condition held: the rule
    applies from the ``walls_far_support_frames``-th.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.walls_range
    zf = model.floor_z(X) if floor_z_all is None else floor_z_all
    fast = (_native.walls_band(xyz, zf, model.rail_offset, x0, x1, cfg.walls_band[0], cfg.walls_band[1],
                               model.center_coefs()) if _native.enabled() else None)
    if fast is not None:                                   # the band below in one pass (resense/_native.py)
        Xb, Yb, dy = fast
        if Xb.size < 50:
            return None
    else:
        h = Z - (zf + model.rail_offset)
        band = (X > x0) & (X < x1) & (h > cfg.walls_band[0]) & (h < cfg.walls_band[1])
        if band.sum() < 50:
            return None
        Xb, Yb = X[band], Y[band]
        dy = Yb - model.center_y(Xb)
    edges = np.arange(x0, x1 + cfg.walls_bin, cfg.walls_bin)
    nb = edges.size - 1
    idx = np.digitize(Xb, edges) - 1
    inb = (idx >= 0) & (idx < nb)
    centres = 0.5 * (edges[:-1] + edges[1:])
    sides = {}
    for name, sel in (("left", dy > 0), ("right", dy < 0)):
        sel = sel & inb
        if sel.sum() < cfg.walls_min_points:
            continue                                   # nothing on this side (platform hall, missing wall)
        # boundary per bin: the point at the |dy| percentile rank, in absolute Y
        q, counts, yq = bin_percentile(np.abs(dy[sel]), idx[sel], nb, cfg.walls_percentile, cfg.walls_min_points,
                                       payload=Yb[sel].astype(np.float64))
        ok = np.isfinite(q)
        if not ok.any():
            continue
        fit = _fit_side(centres[ok], yq[ok], cfg, float(np.mean(q[ok])), t_fixed)
        if fit is not None:
            sides[name] = fit
    if not sides:
        return None
    n_sides = len(sides)
    disagreement = 0.0
    run = 0
    # Prefer the boundary that runs closest to the track: near structures (column rows,
    # cable ducts, the near wall) are constrained by the gauge to be parallel to the track,
    # far walls are not (caverns, stations, diverging tunnels).
    if n_sides == 2:
        disagreement = abs(sides["left"][1] - sides["right"][1])
        # 25.09 (off by default): a side whose far bins do not follow its own fit does not set
        # the shape when the other side's do and say straight, once that has held for
        # walls_far_support_frames frames; side count and disagreement (the trusted range) stay
        # as fitted, as for the nearer-side rule below
        supported = (_far_supported_side(sides, cfg)
                     if cfg.walls_min_far_support > 0 and t_fixed is not None else None)
        run = far_support_run + 1 if supported is not None else 0
        if supported is not None and run >= cfg.walls_far_support_frames:
            sides = {supported: sides[supported]}
        elif disagreement > 1.0 / 1500.0:
            nearer = min(sides, key=lambda k: sides[k][3])
            sides = {nearer: sides[nearer]}
    w = np.array([1.0 / (f[2] ** 2 + 1e-4) for f in sides.values()])
    c1 = float(np.sum(w * [f[0] for f in sides.values()]) / w.sum())
    c2 = float(np.sum(w * [f[1] for f in sides.values()]) / w.sum())
    c1 = float(np.clip(c1, -cfg.walls_max_yaw, cfg.walls_max_yaw))
    c2 = float(np.clip(c2, -1.0 / cfg.walls_min_radius, 1.0 / cfg.walls_min_radius))
    quality = float(min(f[2] for f in sides.values()))
    x_valid = float(max(f[4] for f in sides.values()))
    x_valid_min = float(min(f[4] for f in sides.values()))
    return c1, c2, quality, x_valid, n_sides, disagreement, x_valid_min, run


def verify_floor_extrapolation(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig,
                               floor_z_all: Optional[np.ndarray] = None) -> float:
    """X up to which the linearly extrapolated bed is confirmed by the base of the side
    structures; ``model.floor_range[1]`` when nothing confirms it.

    The bed itself vanishes beyond ~100 m (grazing incidence, platforms, switches) but the
    walls, benches and cable ducts beside the track are seen to the end of the range, and
    their foot runs at a constant height above the rail head. Per along-track bin the lowest
    side point (minus half a ring spacing: the lowest sample of a vertical face lies up to one
    ring above its foot) is compared with the extrapolated bed; the offset measured in the
    near bins, where the bed fit is supported, is the reference. Walking outward, the
    extrapolation stays verified while the median deviation over the last ``floor_verify_window``
    metres of populated bins is within ``floor_verify_tolerance``. A vertical curve, a platform
    or a transition breaks the agreement and the range stops there, so the check can only
    extend the trusted corridor where the geometry supports it, never shrink it.
    """
    x_fit = float(model.floor_range[1])
    if not cfg.floor_verify_enabled:
        return x_fit
    x0 = 10.0
    X = xyz[:, 0]
    b0, b1 = cfg.floor_verify_band
    edges = np.arange(x0, cfg.floor_verify_max_range + cfg.floor_verify_bin, cfg.floor_verify_bin)
    nb = edges.size - 1
    fast = (_native.verify_profile(xyz, floor_z_all, x0, cfg.floor_verify_max_range, model.center_coefs(), b0, b1,
                                   edges) if _native.enabled() and floor_z_all is not None else None)
    if fast is not None:                                   # the selection and binning below in one pass
        n_sel, n_side, counts, base = fast
        if n_sel < 100 or n_side < 50:
            return x_fit
    else:
        sel = (X > x0) & (X < cfg.floor_verify_max_range)
        if sel.sum() < 100:
            return x_fit
        P = xyz[sel]
        Xs = P[:, 0].astype(np.float64)
        ady = np.abs(P[:, 1] - model.center_y(Xs))
        side = (ady > b0) & (ady < b1)
        if side.sum() < 50:
            return x_fit
        Xs = Xs[side]
        zf = model.floor_z(Xs) if floor_z_all is None else floor_z_all[sel][side]
        hs = P[side, 2] - zf                      # height above the extrapolated bed
        keep = hs > -1.0                          # drop returns from below the bed (noise, drains)
        Xs, hs = Xs[keep], hs[keep]
        b = np.clip(np.digitize(Xs, edges) - 1, 0, nb - 1)
        counts = np.bincount(b, minlength=nb)
        base = np.full(nb, np.inf)
        np.minimum.at(base, b, hs)
    centres = 0.5 * (edges[:-1] + edges[1:])
    valid = (counts >= cfg.floor_verify_min_points) & np.isfinite(base)
    # half a vertical ring spacing (0.125 deg in the fine band) at that range
    base = base - 0.5 * centres * np.radians(0.125)
    near = valid & (centres > 15.0) & (centres < x_fit)
    if near.sum() < 3:
        return x_fit
    ref = float(np.median(base[near]))
    if float(np.median(np.abs(base[near] - ref))) > cfg.floor_verify_tolerance:
        return x_fit                              # the side base is not a stable reference here
    dev = base - ref
    verified = x_fit
    for i in np.flatnonzero(valid & (centres >= x_fit)):
        win = valid & (centres > centres[i] - cfg.floor_verify_window) & (centres <= centres[i])
        if win.sum() < 2:
            break
        if float(np.median(np.abs(dev[win]))) > cfg.floor_verify_tolerance:
            break
        verified = float(edges[i + 1])
    return verified


# ---------------------------------------------------------------------------
# rails -> lateral axis, rail head, and (v0.5) the yaw at the vehicle
# ---------------------------------------------------------------------------

def _height_profile(y: np.ndarray, h: np.ndarray, edges: np.ndarray, percentile: float,
                    min_points: int = 8) -> np.ndarray:
    """Per lateral bin the ``percentile`` of h (NaN where fewer than ``min_points``)."""
    nb = edges.size - 1
    idx = np.clip(np.digitize(y, edges) - 1, 0, nb - 1)
    return bin_percentile(np.asarray(h, dtype=np.float64), idx, nb, percentile, min_points)[0]


def _ridge(prof: np.ndarray, k: int) -> np.ndarray:
    """Prominence of each bin over the mean of its neighbours ``k`` bins away."""
    nb = prof.size
    ridge = np.full(nb, np.nan)
    ridge[k:nb - k] = prof[k:nb - k] - 0.5 * (prof[:nb - 2 * k] + prof[2 * k:])
    return ridge


def _refine_peak(ridge: np.ndarray, b: int) -> float:
    """Sub-bin position of a ridge maximum at bin ``b`` (parabola through its neighbours)."""
    if 0 < b < ridge.size - 1 and np.isfinite(ridge[b - 1]) and np.isfinite(ridge[b + 1]):
        d = ridge[b - 1] - 2 * ridge[b] + ridge[b + 1]
        if d < -1e-9:
            return b + float(np.clip(0.5 * (ridge[b - 1] - ridge[b + 1]) / d, -0.5, 0.5))
    return float(b)


@dataclass
class RailsFit:
    """Result of :func:`estimate_rails`."""
    score: float                       # ridge prominence of the weaker rail (m); < 0 = nothing plausible found
    center: float                      # track axis at X = 0 (m, + left)
    rail_offset: float                 # rail head above the bed reference (m)
    n_slabs: int = 0                   # slabs in which the pair was found again (v0.5)
    tan_yaw: Optional[float] = None    # tangent of the axis at the vehicle from the slab midpoints (None = no yaw)
    xm: Optional[np.ndarray] = None    # slab centres (m along the track)
    mids: Optional[np.ndarray] = None  # rail-pair midpoints per slab (absolute Y, m)
    wts: Optional[np.ndarray] = None   # ridge prominence per slab (m)
    head_left: float = float("nan")    # left rail head above the bed reference (m); NaN = no pair found
    head_right: float = float("nan")   # right rail head above the bed reference (m)

    @property
    def cant(self) -> float:
        """Height of the left rail head over the right one (m): the sensor roll relative to the
        rail plane (plus the track cant in a curve); NaN without a rail pair. Used by the mount
        calibration (``resense.calibration``)."""
        return float(self.head_left - self.head_right)

    def __iter__(self):
        """Backwards compatible unpacking: (score, center, rail_offset)."""
        return iter((self.score, self.center, self.rail_offset))

    def __getitem__(self, i):
        return (self.score, self.center, self.rail_offset)[i]


def estimate_rails(xyz: np.ndarray, floor: TrackModel, cfg: TrackConfig,
                   prior_center: float, prior: Optional[TrackModel] = None,
                   floor_z_all: Optional[np.ndarray] = None) -> RailsFit:
    """Find the two rail-head ridges in the lateral height profile of the near range.

    ``score`` is the ridge prominence (m) of the weaker rail; a negative score means nothing
    plausible was found. The profile is built in the lateral coordinate of the *prior* axis
    (its yaw and curvature removed), so that in a curve the rails at 4-30 m are straight
    lines instead of a 0.5 m smear. The pair is then located again in each of
    ``rails_yaw_slabs`` along-track slabs (v0.5): a line through the slab midpoints (with the
    prior curvature held fixed) gives the axis at X = 0 (``center``) and its tangent
    (``tan_yaw``); with fewer than ``rails_yaw_min_slabs`` slabs the mean midpoint over the
    rail range is the centre and no yaw is reported.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.rails_range
    half, step = cfg.rails_search_halfwidth, cfg.rails_bin
    kap = float(prior.curvature) if prior is not None else 0.0
    fast = (_native.rails_band(xyz, floor_z_all, x0, x1, None if prior is None else prior.center_coefs(),
                               prior_center, half) if _native.enabled() and floor_z_all is not None else None)
    if fast is not None:                                   # the selection below in one pass (resense/_native.py)
        xs, y, hh = fast
    else:
        near = (X > x0) & (X < x1)                # the near range only: the profile needs ~1/3 of the frame
        Xd = X[near].astype(np.float64)
        Yn, Zn = Y[near].astype(np.float64), Z[near]
        h = Zn - (floor.floor_z(Xd) if floor_z_all is None else floor_z_all[near])
        if prior is not None:
            shape = np.tan(prior.yaw) * Xd + 0.5 * prior.curvature * Xd * Xd
            Yp = Yn - shape
        else:
            Yp = Yn
        sel = (np.abs(Yp - prior_center) < half) & (h > -0.4) & (h < 0.8)
        y, hh, xs = Yp[sel], h[sel], Xd[sel]
    if xs.size < 200:
        return RailsFit(-1.0, prior_center, floor.rail_offset)
    edges = np.arange(prior_center - half, prior_center + half + step, step)
    nb = edges.size - 1
    prof = _height_profile(y, hh, edges, cfg.rails_percentile)
    yc = edges[:-1] + step / 2
    k = max(1, int(round(0.25 / step)))
    ridge = _ridge(prof, k)
    half_sp = int(round(0.5 * cfg.rails_spacing / step))
    lo, hi = cfg.rails_head_height
    best = (-1.0, prior_center, floor.rail_offset)
    best_bins = None
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
            best_bins = (bl, br)
    heads = {} if best_bins is None else {"head_left": float(prof[best_bins[1]]), "head_right": float(prof[best_bins[0]])}
    if best_bins is None or best[0] < cfg.rails_min_score or not cfg.rails_yaw_enabled or cfg.rails_yaw_slabs < 2:
        return RailsFit(*best, **heads)
    # per slab: the ridge maximum near each global rail position -> pair midpoint per slab
    n_slabs = int(cfg.rails_yaw_slabs)
    slab_edges = np.linspace(x0, x1, n_slabs + 1)
    dev = max(1, int(round(cfg.rails_yaw_max_dev / step)))
    xm, mids, wts = [], [], []
    for s in range(n_slabs):
        m = (xs >= slab_edges[s]) & (xs < slab_edges[s + 1])
        if m.sum() < 100:
            continue
        p = _height_profile(y[m], hh[m], edges, cfg.rails_percentile, min_points=4)
        r = _ridge(p, k)
        pos = []
        for b0 in best_bins:
            lo_b, hi_b = max(k, b0 - dev), min(nb - k, b0 + dev + 1)
            seg = r[lo_b:hi_b]
            if seg.size == 0 or not np.isfinite(seg).any():
                break
            j = lo_b + int(np.nanargmax(seg))
            if not (np.isfinite(r[j]) and r[j] >= 0.5 * cfg.rails_min_score and lo < p[j] < hi):
                break
            pos.append((float(yc[j]) + (_refine_peak(r, j) - j) * step, float(r[j])))
        if len(pos) == 2:
            mids.append(0.5 * (pos[0][0] + pos[1][0]))
            xm.append(0.5 * (slab_edges[s] + slab_edges[s + 1]))
            wts.append(min(pos[0][1], pos[1][1]))
    if len(mids) < max(2, int(cfg.rails_yaw_min_slabs)):
        return RailsFit(best[0], best[1], best[2], len(mids), **heads)
    xm, mids, wts = np.array(xm), np.array(mids), np.array(wts)
    mids_abs = mids + (np.tan(prior.yaw) * xm + 0.5 * kap * xm * xm if prior is not None else 0.0)
    # line through the absolute midpoints with the prior curvature held fixed:
    # y - k x^2 / 2 = c + t x  ->  c = axis at X = 0, t = tangent at the vehicle
    w = np.sqrt(wts / max(float(wts.max()), 1e-6))
    t, c = np.polyfit(xm, mids_abs - 0.5 * kap * xm * xm, 1, w=w)
    return RailsFit(best[0], float(c), best[2], len(mids), float(t), xm, mids_abs, wts, **heads)


def _check_far_rails(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig, near: RailsFit) -> None:
    """Replace wall-derived curvature that contradicts independently visible rails.

    Station hall walls can look like a gentle curve while the rails remain straight. A
    near rail pair fixes the tangent but cannot validate the walls' curvature at 80 m.
    Use two *independent* slabs beyond the near fit; with no far pair there is no new
    evidence and the existing range policy applies unchanged. Beyond the last rail
    slab the contradictory walls cannot validate the axis, so that range is advisory.
    """
    if (near.n_slabs < cfg.rails_yaw_min_slabs or near.xm is None or model.axis_sides == 0
            or model.axis_valid <= cfg.rails_range[1] + cfg.axis_valid_margin):
        return
    near_end = cfg.rails_range[1]
    far_cfg = replace(cfg, rails_range=(near_end, near_end + 2 * (near_end - cfg.rails_range[0])),
                      rails_yaw_slabs=2, rails_yaw_min_slabs=2)
    if abs(model.curvature) * far_cfg.rails_range[1] ** 2 / 2 <= cfg.rails_yaw_max_dev:
        return  # a wall bend this small cannot displace the far corridor appreciably
    # Remove the unverified curvature from the search coordinates: otherwise the
    # wall's error can make the real far ridges disappear from the rail profile.
    tangent = replace(model, curvature=0.0)
    rails = estimate_rails(xyz, model, far_cfg, model.center, prior=tangent)
    if rails.score < cfg.rails_min_score or rails.n_slabs < 2 or rails.xm is None:
        return
    # The second slab must actually extend to its far end. A short fragment at a
    # switch must not be assigned the centre of an otherwise empty 25 m slab.
    end = far_cfg.rails_range[1]
    tail = xyz[(xyz[:, 0] > end - 5) & (xyz[:, 0] < end)]
    if tail.size == 0:
        return
    height = tail[:, 2] - model.floor_z(tail[:, 0])
    y_tangent = model.center + np.tan(model.yaw) * tail[:, 0]
    lateral = tail[:, 1] - y_tangent
    head = (height > cfg.rails_head_height[0]) & (height < cfg.rails_head_height[1])
    if any(np.count_nonzero(head & (np.abs(lateral - side * cfg.rails_spacing / 2)
                                   < cfg.rails_yaw_max_dev)) < 50 for side in (-1, 1)):
        return
    error = rails.mids - model.center_y(rails.xm)
    # Both slabs must disagree in the same direction, beyond the ridge search's
    # lateral tolerance. A single switch fitting or noisy slab cannot shorten range.
    if (np.all(np.sign(error) == np.sign(error[0]))
            and np.min(np.abs(error)) > 0.5 * cfg.rails_bin
            and np.max(np.abs(error)) > cfg.rails_yaw_max_dev):
        x = np.concatenate([near.xm, rails.xm])
        y = np.concatenate([near.mids, rails.mids])
        w = np.concatenate([near.wts, rails.wts])
        a, t, c = np.polyfit(x, y, 2, w=np.sqrt(w))
        if abs(2 * a) <= 1.0 / cfg.walls_min_radius:
            model.center = float(c)
            model.yaw = float(np.arctan(t))
            model.curvature = float(2 * a)
            model.axis_valid = min(model.axis_valid, end + cfg.axis_valid_margin)


def estimate_track(xyz: np.ndarray, cfg: TrackConfig, prev: Optional[TrackModel] = None) -> TrackModel:
    """Fit floor + rails + boundary-based yaw/curvature for one frame, smoothing against the
    previous model."""
    prior = prev if prev is not None else default_track_model(cfg)
    shadow_ref = (prev if cfg.floor_shadow_height > 0 and prev is not None and prev.age >= cfg.axis_warmup_frames
                  else None)
    info: dict = {}
    fit = _fit_floor(xyz, cfg, prior, shadow_ref=shadow_ref, info=info)
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
        age=(prev.age + 1) if prev is not None else 0,
        floor_shadow=float(info.get("shadow", 0.0)), floor_held=bool(info.get("hold", False)),
    )
    a_r = cfg.rails_smoothing if prev is not None else 0.0
    a_w = cfg.walls_smoothing if prev is not None else 0.0
    t_fixed: Optional[float] = None
    zf = model.floor_z(xyz[:, 0])                  # the bed height of every point, shared by the three steps below
    rails = None
    rcfg, hold_rails = cfg, False
    if info.get("face", 0.0) > 0:
        # a shadow this frame: the rail pair is searched only in front of the object's face; with
        # less than floor_shadow_min_bins bins of track left the previous rail model is held
        rcfg = replace(cfg, rails_range=(cfg.rails_range[0], min(cfg.rails_range[1], float(info["face"]))))
        hold_rails = rcfg.rails_range[1] - rcfg.rails_range[0] < cfg.floor_shadow_min_bins * cfg.floor_bin
    if cfg.rails_enabled and hold_rails:
        model.rail_score, model.rail_slabs = prior.rail_score, prior.rail_slabs
        if cfg.rails_yaw_enabled:
            t_fixed = float(np.clip(np.tan(prior.yaw), -cfg.walls_max_yaw, cfg.walls_max_yaw))
    elif cfg.rails_enabled:
        rails = estimate_rails(xyz, model, rcfg, prior.center, prior, floor_z_all=zf)
        model.rail_score = rails.score
        model.rail_slabs = rails.n_slabs
        if rails.score >= cfg.rails_min_score:
            model.center = a_r * prior.center + (1 - a_r) * rails.center
            model.rail_offset = a_r * prior.rail_offset + (1 - a_r) * rails.rail_offset
            if cfg.rails_yaw_enabled and rails.tan_yaw is not None:
                t_fixed = float(np.clip(rails.tan_yaw, -cfg.walls_max_yaw, cfg.walls_max_yaw))
    if cfg.walls_enabled:
        est = estimate_axis_from_walls(xyz, model, cfg, t_fixed, floor_z_all=zf, far_support_run=prior.far_support_run)
        if est is not None:
            tan_yaw, curv, q, x_valid, n_sides, disagreement, x_valid_min, model.far_support_run = est
            model.yaw = a_w * prior.yaw + (1 - a_w) * np.arctan(tan_yaw)
            model.curvature = a_w * prior.curvature + (1 - a_w) * curv
            model.wall_quality = q
            model.axis_sides = n_sides
            model.axis_valid = x_valid + cfg.axis_valid_margin
            agree = n_sides == 2 and (cfg.axis_sides_max_disagreement <= 0 or disagreement <= cfg.axis_sides_max_disagreement)
            straight = abs(model.curvature) < 1e-4 and q < 0.2 and (agree or cfg.axis_one_side_range <= 0)
            bonus = cfg.axis_valid_straight_bonus if straight else 0.0
            model.axis_valid += bonus
            # 25.09: the range both boundaries support (cluster.far_axis_both_sides); the caps
            # below apply to it through min(axis_valid, ...) where it is read
            model.axis_valid_both = (x_valid_min + cfg.axis_valid_margin + bonus) if n_sides == 2 else model.axis_valid
            if n_sides == 2 and not straight:
                model.axis_valid_bent = x_valid_min + cfg.axis_valid_margin
            if n_sides == 1 and cfg.axis_one_side_range > 0:
                # one boundary alone cannot tell a parallel wall from a diverging one
                model.axis_valid = min(model.axis_valid, cfg.axis_one_side_range)
            if n_sides == 2 and cfg.axis_sides_max_disagreement > 0 and disagreement > cfg.axis_sides_max_disagreement:
                # the two boundaries bend differently (transition, cavern, platform hall):
                # whichever side won, the corridor beyond the disagreement is a guess
                model.axis_valid = min(model.axis_valid, cfg.axis_disagree_range)
        else:
            # no boundary parallel to the track this frame: the rails alone give the tangent,
            # the curvature (unsupported now) decays towards straight and the trusted range
            # shrinks; without rails the corridor keeps its shape (no jump on a bad frame)
            floor_valid = cfg.walls_range[0] + cfg.axis_valid_margin
            if t_fixed is not None:
                model.yaw = a_w * prior.yaw + (1 - a_w) * np.arctan(t_fixed)
                model.curvature = a_w * prior.curvature
                floor_valid = cfg.rails_range[1] + cfg.axis_valid_margin
            model.axis_valid = max(floor_valid, prior.axis_valid - 20.0)
            model.axis_sides = 0            # axis_valid_both keeps its default: no second limit
    else:
        model.yaw = np.radians(cfg.yaw_deg)
        model.curvature = cfg.curvature
        model.axis_valid = 1e9
    if prev is not None and prev.age >= cfg.axis_warmup_frames:
        # the vehicle cannot turn by more than a fraction of a degree per frame, nor can the
        # curvature ahead change faster than along a transition curve: larger jumps are
        # estimator noise (a boundary flipping between two structures) and are clipped.
        # Not during the warm-up after a (re)seed (v0.6): a wrong first-frame estimate (a free
        # wall fit clipped at 5 deg on a cold start mid-ride) would otherwise take 30+ frames
        # to unwind at 0.17 deg per frame.
        if cfg.axis_max_yaw_rate > 0:
            model.yaw = float(np.clip(model.yaw, prev.yaw - cfg.axis_max_yaw_rate, prev.yaw + cfg.axis_max_yaw_rate))
        if cfg.axis_max_curvature_rate > 0:
            model.curvature = float(np.clip(model.curvature, prev.curvature - cfg.axis_max_curvature_rate,
                                            prev.curvature + cfg.axis_max_curvature_rate))
    if cfg.rails_far_check_enabled and rails is not None and cfg.walls_enabled:
        _check_far_rails(xyz, model, cfg, rails)
    model.floor_verified = verify_floor_extrapolation(xyz, model, cfg, floor_z_all=zf)
    return model
