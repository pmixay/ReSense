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

from dataclasses import dataclass, field, replace
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
    floor_hold_run: int = 0          # 25.09 review: consecutive held frames; past floor_shadow_max_hold it keeps counting while the rule is released (a shadow still found, not applied)
    far_support_run: int = 0         # 25.09: consecutive frames with the walls_min_far_support condition (not reported)
    disagree_left: int = 0           # 27.09 (axis_disagree_hold): nominal frame periods the disagreement cap still applies to one-boundary frames (not reported)
    axis_valid_both: float = 1e9     # 25.09: X up to which BOTH fitted boundaries support the axis (= axis_valid with one or none); read only with cluster.far_axis_both_sides 1, not serialised
    axis_valid_bent: float = 1e9     # 25.09: the same without the straight bonus, on a bent axis with two boundaries only (1e9 otherwise); cluster.far_axis_both_sides 2, not serialised
    wall_drift: float = 1e9          # 15.10 (axis_wall_drift): X where a near tunnel boundary has come axis_wall_drift nearer the axis than in the rail range (1e9 = none): the monitored range ends there
    axis_valid_without_rails: float = 0.0  # N6: pre-extension range, restored before the next frame
    rail_axis_support: float = 0.0   # N6: last observed paired-rail station supporting an extension
    curv_step: float = 0.0           # 19.10 (axis_joint_fit): curvature change at curv_knot (1/m): the axis bends by curv_step (X - curv_knot)^2 / 2 more beyond it (C1 piecewise); 0 = a single quadratic
    curv_knot: float = 0.0           # 19.10: X of that change (m)
    curv_range: float = 0.0          # 20.10 (v4, axis_joint_range off): the per-side fits' curvature, smoothed, for the straight test only (not serialised)
    axis_straight: bool = False      # 19.10: the straight bonus applied this frame (hysteresis with axis_joint_fit; not serialised)
    # 19.10 (v5, axis_joint_min_curvature > 0; None otherwise): the model of the estimator without the joint fit, carried
    # to the next frame as its state (this model is the output); the joint fit's own shape state (centre, yaw, curvature,
    # curv_step, curv_knot); whether the output uses that shape this frame (serialised as track.joint_used only then);
    # the reach cap applied this frame (v5b, axis_joint_reach_cap; serialised as track.joint_reach only when it capped)
    base: Optional["TrackModel"] = field(default=None, repr=False, compare=False)
    joint_shape: Optional[tuple] = field(default=None, repr=False, compare=False)
    joint_used: Optional[bool] = None
    joint_reach: float = 0.0

    @property
    def bent(self) -> bool:
        """The axis has a curvature step (19.10, ``axis_joint_fit``): ``center_coefs`` alone does not describe
        it, so the native kernels, which take only those, are not used for it."""
        return self.curv_step != 0.0

    def _step_y(self, X: np.ndarray) -> np.ndarray:
        d = np.maximum(X - self.curv_knot, 0.0)
        return 0.5 * self.curv_step * d * d

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
        if self.bent:
            X = np.asarray(X, dtype=np.float64)
            return self.center + np.tan(self.yaw) * X + 0.5 * self.curvature * X * X + self._step_y(X)
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
            **({"floor_shadow": round(float(self.floor_shadow), 1), "floor_held": bool(self.floor_held),
                "floor_hold_run": int(self.floor_hold_run)}
               if self.floor_shadow > 0 else {}),
            # 15.10 (additive, only in a frame with a wall drift)
            **({"wall_drift": round(float(self.wall_drift), 1)} if self.wall_drift < 1e9 else {}),
            **({"axis_valid_without_rails": round(float(self.axis_valid_without_rails), 2),
                "rail_axis_support": round(float(self.rail_axis_support), 2)}
               if self.rail_axis_support > 0 else {}),
            # 19.10 (additive, only with a curvature step)
            **({"curv_step": float(self.curv_step), "curv_knot": float(self.curv_knot)} if self.bent else {}),
            # 19.10 (v5, additive, only with axis_joint_min_curvature > 0): which shape the output uses, the reach cap
            **({"joint_used": bool(self.joint_used)} if self.joint_used is not None else {}),
            **({"joint_reach": round(float(self.joint_reach), 1)} if self.joint_reach > 0 else {}),
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


def _floor_shadow(xs: np.ndarray, zs: np.ndarray, ref: TrackModel, cfg: TrackConfig,
                  bins: Optional[np.ndarray] = None):
    """The shadow of a large near object in the bed band (25.09, ``floor_shadow_height``).

    An object that fills the band (the organizers' 2 x 2 m box) hides the bed behind it: the
    bins there hold only the tunnel roof, 3-4 m above the bed, and once they outnumber the bed
    bins in front the line through the near bins tilts (set O, box at 9-26 m: the rail head at
    20 m 0.8-3.5 m off). The shadow starts at the first populated bin within ``floor_shadow_range``
    that lies more than ``floor_shadow_height`` above the previous frame's bed and is followed
    by another such bin adjacent to it in X (``bins``: the profile bin index of each entry; since
    the review of 25.09 two high bins with an empty bin between them, e.g. at 29 and 60 m, are no
    shadow). Then only bins within ``floor_max_residual`` of the previous bed are fitted, never
    the populated bin just before the shadow (the object's face, whose low percentile can still
    look like bed); with fewer than ``floor_shadow_min_bins`` of them in front of the shadow the
    previous bed is held. The object's face is the bin nearest the shadow that starts the last run
    of bins before it that are not bed (more than ``floor_max_residual`` off; an object raised above
    the bed lets the bed show under it for a few metres; a nearer off-bed bin, a switch part or a
    low object, is not the face since the review of 25.09), else that populated bin just before the
    shadow. Returns (keep mask or None, shadow start X or 0, lower edge X of the face bin or 0,
    hold)."""
    d = zs - ref.floor_z(xs)
    high = d > cfg.floor_shadow_height
    pair = high[:-1] & high[1:] & (xs[:-1] < cfg.floor_shadow_range)
    adjacent = np.ones(max(xs.size - 1, 0), dtype=bool) if bins is None else np.diff(bins) == 1
    start = np.flatnonzero(pair & adjacent)
    if start.size == 0:
        return None, 0.0, 0.0, False
    s = int(start[0])
    x_s = float(xs[s] - 0.5 * cfg.floor_bin)                 # lower edge of the first shadowed bin
    keep = np.abs(d) < cfg.floor_max_residual
    off = np.flatnonzero(~keep[:s])
    if off.size:
        f = int(off[-1])                                     # the off-bed run nearest the shadow ...
        while f > 0 and not keep[f - 1] and adjacent[f - 1]:
            f -= 1                                           # ... from its first bin (the object's front)
    else:
        f = s - 1
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
               shadow_ref: Optional[TrackModel] = None, info: Optional[dict] = None, release: bool = False):
    """Robust per-bin percentile fit of the track bed. Returns (coef, range, n_bins, rms).

    Two stages: a line through the dense near bins (< 40 m), then far bins are accepted
    only if they agree with that line within ``floor_max_residual``; a quadratic is fitted
    only when enough consistent far bins exist. This avoids the quadratic blowing up when
    the bed is hidden at range (platforms, switches) and structure points take its place.
    With ``shadow_ref`` (the previous frame's model; ``floor_shadow_height`` > 0) the bins in
    the shadow of a large near object are left out first, or ``shadow_ref``'s bed is returned
    unchanged (:func:`_floor_shadow`); ``info`` then receives ``shadow``, ``face`` and ``hold``.
    With ``release`` (the bed was held ``floor_shadow_max_hold`` frames in a row) the shadow is
    only looked for, to know whether it persists; the bed is fitted as without the rule.
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.floor_fit_range
    # bins grow with range (2 m near, 2.5x beyond 40 m) so that the sparse far bed still fills them
    edges = np.concatenate([np.arange(x0, min(40.0, x1), cfg.floor_bin),
                            np.arange(max(40.0, x0), x1 + 2.5 * cfg.floor_bin, 2.5 * cfg.floor_bin)])
    nb = edges.size - 1
    fast = (_native.floor_band(xyz, x0, x1, prior.center_coefs(), cfg.floor_halfwidth, edges)
            if _native.enabled() and not prior.bent else None)   # the band below in one pass (resense/_native.py)
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
        keep, x_s, x_face, hold = _floor_shadow(xs, zs, shadow_ref, cfg, bins=np.flatnonzero(ok))
        if release:
            keep, x_face, hold = None, 0.0, False
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
                             far_support_run: int = 0, boundaries: Optional[dict] = None):
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
    applies from the ``walls_far_support_frames``-th. ``boundaries`` (15.10, ``axis_wall_drift``):
    a dict that receives per side the boundary bins as ``(centres, absolute Y)``, populated bins
    only, nearest first, whether or not the side's fit succeeded (:func:`wall_drift_range`).
    """
    X, Y, Z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    x0, x1 = cfg.walls_range
    zf = model.floor_z(X) if floor_z_all is None else floor_z_all
    fast = (_native.walls_band(xyz, zf, model.rail_offset, x0, x1, cfg.walls_band[0], cfg.walls_band[1],
                               model.center_coefs()) if _native.enabled() and not model.bent else None)
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
        if boundaries is not None:
            boundaries[name] = (centres[ok], yq[ok])
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


_DRIFT_GAP_BINS = 3        # 15.10 (axis_wall_drift): a boundary is followed outward while its populated bins are at most this many walls_bin apart
_DRIFT_NEAR_MAD = 0.25     # m, the boundary's offset in the rail range must be this consistent (median absolute deviation) to be the reference
_DRIFT_NEAR_SLOPE = 0.02   # and run this parallel to the rails there (|slope| of a line through its offsets: 0.4 m over 20 m)
_DRIFT_MAX_CURVATURE = 2e-3  # 1/m (R 500 m): a curvature error this large moves a boundary by at most this x X x dX between bins at X; a faster change is a structure edge
_STEP_ZERO = 1e-7          # 19.10: 1/m, a smaller curvature step is none (0.4 mm at 150 m); keeps the native kernels in use
_STRAIGHT_X = 150.0        # 19.10: m, where a curvature step's bend is compared with the straight test's (|curvature| < 1e-4)


def wall_drift_range(boundaries: dict, model: TrackModel, cfg: TrackConfig) -> float:
    """The X from which the fitted axis contradicts a near tunnel boundary (15.10, ``axis_wall_drift``),
    or 1e9.

    A boundary within ``axis_wall_drift_max_offset`` of the axis in the rail range (the wall of a
    single-track tube, a column row: structures the gauge keeps parallel to the track) runs at the same
    offset along the whole track. Its median offset from ``model``'s axis over the bins within
    ``rails_range[1]``, where the rails fix the axis, is the reference (at least three bins, median
    absolute deviation at most ``_DRIFT_NEAR_MAD``, a line through the ones within that of the
    reference sloping at most ``_DRIFT_NEAR_SLOPE``: parallel to the rails; a boundary closing in
    already there is a structure crossing, not a wall). The boundary is then followed outward while its
    populated bins are at most ``_DRIFT_GAP_BINS`` bins apart. A change between two followed bins faster
    than a curvature error of ``_DRIFT_MAX_CURVATURE`` can move it is a structure edge (a gate, a
    platform screen, a niche): the reference moves with it. Where the boundary is more than
    ``axis_wall_drift`` nearer the axis than the reference in ``axis_wall_drift_bins`` consecutive bins,
    the axis there is off the track by about that much, or the boundary is not parallel to it: either
    way the corridor beyond is not where the track is. The near edge of the first of those bins is
    returned (the smallest over the sides). At the entry of a curve the quadratic axis lags the track
    (the curvature of a transition grows with the distance, the fit's does not), the outer wall runs
    diagonally across the corridor and an object on the track beyond the crossing is outside the
    corridor (roundT_pressureGate_roundT frames 57-117: 1.0-2.4 m at 100 m; at the returned X the
    axis is 0.7-1.1 m off the wall-referenced track). ``boundaries`` is
    :func:`estimate_axis_from_walls`'s; a boundary that moves away from the axis says nothing (a
    niche, a hall, a diverging tunnel)."""
    best = 1e9
    near_max = cfg.rails_range[1]
    c, t, k2 = model.center_coefs()
    for x, y in boundaries.values():
        x = np.asarray(x, dtype=np.float64)
        dy = np.asarray(y, dtype=np.float64) - (c + t * x + k2 * x * x)
        if model.bent:
            dy = dy - model._step_y(x)
        near = x <= near_max
        if int(near.sum()) < 3:
            continue
        a = dy * np.sign(np.median(dy[near]))          # offset from the axis, positive towards the boundary
        ref = float(np.median(a[near]))
        if ref <= 0.0 or ref > cfg.axis_wall_drift_max_offset or float(np.median(np.abs(a[near] - ref))) > _DRIFT_NEAR_MAD:
            continue
        inl = near & (np.abs(a - ref) <= _DRIFT_NEAR_MAD)  # the slope without the odd near bin (a structure at 6-10 m)
        if int(inl.sum()) < 3 or abs(float(np.polyfit(x[inl], a[inl], 1)[0])) > _DRIFT_NEAR_SLOPE:
            continue
        prev, prev_a, run, first = float(x[near][-1]), float(a[near][-1]), 0, 0.0
        for xi, ai in zip(x[~near], a[~near]):
            if xi - prev > _DRIFT_GAP_BINS * cfg.walls_bin:
                break                                   # the boundary is lost (occluded): no evidence beyond
            if abs(ai - prev_a) > _DRIFT_MAX_CURVATURE * xi * (xi - prev):
                ref += ai - prev_a                      # a structure edge, not the axis drifting
            prev, prev_a = float(xi), float(ai)
            if ai < ref - cfg.axis_wall_drift:
                run += 1
                first = first if run > 1 else float(xi) - 0.5 * cfg.walls_bin
                if run >= cfg.axis_wall_drift_bins:
                    best = min(best, first)
                    break
            else:
                run = 0
    return best


def _followed_reach(x, y, model: TrackModel, cfg: TrackConfig) -> float:
    """How far a boundary (bins ``x`` / absolute ``y``, nearest first) runs parallel to ``model``'s axis (19.10,
    ``axis_joint_fit``): followed outward from its first bins while populated bins are at most ``_DRIFT_GAP_BINS``
    bins apart; a jump faster than a curvature error of ``_DRIFT_MAX_CURVATURE`` is a structure edge (the reference
    moves with it, as in :func:`wall_drift_range`); it ends before the first of two consecutive bins more than
    ``walls_max_residual`` from the reference. 0 when it has fewer than 3 bins."""
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    fin = np.isfinite(x) & np.isfinite(y)
    x, y = x[fin], y[fin]
    if x.size < 3:
        return 0.0
    a = y - model.center_y(x)
    ref = float(np.median(a[:3]))
    last, prev, prev_a, off = float(x[0]), float(x[0]), float(a[0]), 0
    for xi, ai in zip(x[1:], a[1:]):
        if xi - prev > _DRIFT_GAP_BINS * cfg.walls_bin:
            break
        if abs(ai - prev_a) > max(cfg.axis_joint_tolerance, _DRIFT_MAX_CURVATURE * xi * (xi - prev)):
            ref += ai - prev_a                              # a structure edge
        prev, prev_a = float(xi), float(ai)
        if abs(ai - ref) > cfg.walls_max_residual:
            off += 1
            if off >= 2:
                break
        else:
            off, last = 0, float(xi)
    return last


def _joint_basis(x: np.ndarray, knot: float) -> np.ndarray:
    """Columns (x, x^2 / 2[, max(x - knot, 0)^2 / 2]) of the axis shape: tangent, curvature[, curvature step]."""
    cols = [x, 0.5 * x * x]
    if knot > 0:
        d = np.maximum(x - knot, 0.0)
        cols.append(0.5 * d * d)
    return np.stack(cols, axis=1)


def joint_axis_fit(rails: RailsFit, boundaries: dict, prior: TrackModel, cfg: TrackConfig) -> Optional[dict]:
    """Axis tangent, curvature and curvature step from one least-squares fit of the near rail pair and the tunnel
    boundaries (19.10, ``axis_joint_fit``, card K2), or None.

    Before: the rail tangent came from a line through the slab midpoints with the *prior* curvature held fixed, so
    on a curve whose prior is too straight it is the tangent at ~17 m, not at the vehicle; the boundaries were then
    fitted with that tangent fixed, which returns a curvature pulled back towards the prior (roundT_doubleT frames
    124-164: rail tangent -0.057, driven path -0.028; curvature 2-4x too small), and the per-side curvatures
    disagree for the same reason (the axis_disagree_range cap). Here the slab midpoints (``rails.xm`` /
    ``rails.mids``: ``y = c + t x + k x^2 / 2``) and the boundary bins (``y = a_s + t x + k x^2 / 2``) share t and k.

    * Each boundary (``estimate_axis_from_walls``' ``boundaries``) is cut into segments at gaps of more than
      ``_DRIFT_GAP_BINS`` bins and at structure edges (a step of the offset from the prior axis that departs
      from the neighbouring steps' slope by more than ``axis_joint_tolerance`` and than a curvature error of
      ``_DRIFT_MAX_CURVATURE`` moves it between the two bins: a jump, not the smoothly growing slope of a curvature
      error of the prior);
      each segment of at least ``axis_joint_min_segment`` bins has its own offset ``a_s``: a wall is piecewise
      parallel to the track (niches, gates, platform screens).
    * The fit grows outward: the bins up to ``axis_joint_grow_start`` first, then ``axis_joint_grow_step`` further
      each round, a bin joining only within ``axis_joint_tolerance`` of the current fit; then, nearest first, the
      remaining bins of a segment (or a new segment) as a group, kept only when the refit (which may change the
      step) keeps every bin used within the tolerance and the rail midpoints within 3 SD. So a far wall that bends
      with a transition curve, or straightens where a curve ends, is followed, and a structure that is not
      parallel never joins.
    * With ``axis_joint_knot`` > 0 the axis may bend by a curvature step ``s (x - knot)^2 / 2`` beyond the knot
      (C1: a transition curve, where the curvature grows with the distance), fitted only with at least
      ``axis_joint_min_far_bins`` bins beyond it and drawn towards 0 with prior SD ``axis_joint_step_sigma``.

    Returns ``{c, t, k, step, knot, x_max: {side: farthest bin used}, n_bins, rms}``."""
    if (rails is None or rails.xm is None or rails.mids is None or len(rails.xm) < 2
            or not (np.all(np.isfinite(rails.xm)) and np.all(np.isfinite(rails.mids)))):
        return None
    knot = float(cfg.axis_joint_knot)
    knot = knot if knot > cfg.rails_range[1] else 0.0
    xm = np.asarray(rails.xm, dtype=np.float64)
    ym = np.asarray(rails.mids, dtype=np.float64)
    rc = np.polyfit(xm, ym, 2 if xm.size >= 3 else 1)  # the rail-pair midpoints as a curve, for the parallel test

    def mids_curve(x):
        return np.polyval(rc, x)
    segs = []                                        # (side, x, y) per boundary segment
    for name, (x, y) in boundaries.items():
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        fin = np.isfinite(x) & np.isfinite(y)
        x, y = x[fin], y[fin]
        if x.size < cfg.axis_joint_min_segment:
            continue
        a = y - prior.center_y(x)
        dx, da = np.diff(x), np.diff(a)
        slope = da / dx
        # the local slope of the offset from the neighbouring steps: a curvature error of the prior grows the slope
        # smoothly (R 400 m against a straight prior: 0.01 per metre at 100 m), a structure edge is a jump
        nb_ = np.stack([np.r_[slope[:1], slope[:-1]], np.r_[slope[1:], slope[-1:]]], axis=1)
        local = np.where(np.arange(slope.size) == 0, nb_[:, 1],
                         np.where(np.arange(slope.size) == slope.size - 1, nb_[:, 0], np.median(nb_, axis=1)))
        cut = np.zeros(x.size, dtype=bool)
        cut[1:] = (dx > _DRIFT_GAP_BINS * cfg.walls_bin) | (np.abs(da - local * dx)
                                                             > np.maximum(cfg.axis_joint_tolerance,
                                                                          _DRIFT_MAX_CURVATURE * x[1:] * dx))
        sid = np.cumsum(cut)
        for s in range(int(sid[-1]) + 1):
            m = sid == s
            if m.sum() < cfg.axis_joint_min_segment:
                continue
            # a segment in the rail range must run parallel to the rail pair there (its offset from the slab
            # midpoints sloping at most _DRIFT_NEAR_SLOPE, as wall_drift_range's reference): a converging platform
            # wall or hall end would otherwise turn the shared tangent (doubleT_platform)
            near = m & (x <= cfg.rails_range[1] + cfg.walls_bin)
            if int(near.sum()) >= 3:
                off = y[near] - mids_curve(x[near])
                if abs(float(np.polyfit(x[near], off, 1)[0])) > _DRIFT_NEAR_SLOPE:
                    continue
            segs.append((name, x[m], y[m]))
    if not segs:
        return None
    nshape = 3 if knot > 0 else 2
    wr, ww = 1.0 / cfg.axis_joint_rail_sigma, 1.0 / cfg.axis_joint_wall_sigma
    Br = _joint_basis(xm, knot)
    tol = float(cfg.axis_joint_tolerance)

    def solve(masks: dict):
        """(solution, segment order) of the fit of the rails and the masked bins of each segment."""
        order = sorted(masks)
        n = len(order)
        rows = [np.concatenate([[1.0], Br[i], np.zeros(n)]) * wr for i in range(xm.size)]
        rhs = list(ym * wr)
        far = 0
        for j, g in enumerate(order):
            x, y = segs[g][1][masks[g]], segs[g][2][masks[g]]
            e = np.zeros((x.size, n))
            e[:, j] = 1.0
            rows.extend(np.hstack([np.zeros((x.size, 1)), _joint_basis(x, knot), e]) * ww)
            rhs.extend(y * ww)
            far += int(np.count_nonzero(x > knot)) if knot > 0 else 0
        if knot > 0:                                       # the step: ridge towards 0, or none without far data
            reg = np.zeros(1 + nshape + n)
            reg[nshape] = 1e6 if far < cfg.axis_joint_min_far_bins else 1.0 / cfg.axis_joint_step_sigma
            rows.append(reg)
            rhs.append(0.0)
        return np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)[0], order

    def residual(sol, order, g, x, y):
        return y - (sol[nshape + 1 + order.index(g)] + _joint_basis(x, knot) @ sol[1:nshape + 1])

    def consistent(sol, order, masks) -> bool:
        """every bin used within the tolerance, the rail midpoints within 3 SD"""
        if np.any(np.abs(ym - (sol[0] + Br @ sol[1:nshape + 1])) > 3.0 * cfg.axis_joint_rail_sigma):
            return False
        return all(np.all(np.abs(residual(sol, order, g, segs[g][1][m], segs[g][2][m])) < tol)
                   for g, m in masks.items())

    lim = float(cfg.axis_joint_grow_start)
    x_end = max(float(cfg.walls_range[1]), lim)
    masks = {g: x <= lim for g, (_, x, _) in enumerate(segs)}
    masks = {g: m for g, m in masks.items() if m.sum() >= cfg.axis_joint_min_segment}
    if not masks:
        return None
    sol, order = solve(masks)
    # the start is held to the same test: the segment with the largest residual leaves until the rest is
    # consistent (a short converging structure at 28-44 m must not bend the shared curvature)
    while masks and not consistent(sol, order, masks):
        worst = max(masks, key=lambda g: float(np.max(np.abs(residual(sol, order, g, segs[g][1][masks[g]],
                                                                         segs[g][2][masks[g]])))))
        del masks[worst]
        if not masks:
            return None
        sol, order = solve(masks)
    step_m = max(float(cfg.axis_joint_grow_step), 1.0)
    while lim < x_end:
        lim += step_m
        # single bins of the segments in the fit that lie within the tolerance of its extrapolation
        for g in list(masks):
            _, x, y = segs[g]
            masks[g] = masks[g] | ((x <= lim) & (np.abs(residual(sol, order, g, x, y)) < tol))
        sol, order = solve(masks)
        # then, nearest first, a segment's remaining bins (or a new segment) as a group: kept only when the
        # refit, which may bend beyond the knot, keeps every bin used within the tolerance (a curve that ends or
        # tightens beyond the reach so far is followed; a structure that is not parallel is not)
        for g in sorted(range(len(segs)), key=lambda g: float(segs[g][1][0])):
            _, x, _ = segs[g]
            add = (x <= lim) & ~masks.get(g, np.zeros(x.size, dtype=bool))
            if add.sum() < (3 if g in masks else cfg.axis_joint_min_segment):
                continue
            trial = dict(masks)
            trial[g] = masks.get(g, np.zeros(x.size, dtype=bool)) | add
            s2, o2 = solve(trial)
            if consistent(s2, o2, trial):
                masks, sol, order = trial, s2, o2
    x_max: dict = {}
    res = []
    for g in order:
        name, x, y = segs[g]
        x, y = x[masks[g]], y[masks[g]]
        x_max[name] = max(x_max.get(name, 0.0), float(x.max()))
        res.append(residual(sol, order, g, x, y))
    r = np.concatenate(res)
    if not np.all(np.isfinite(sol)):
        return None
    return {"c": float(sol[0]), "t": float(sol[1]), "k": float(sol[2]),
            "step": float(sol[3]) if knot > 0 else 0.0, "knot": knot, "x_max": x_max,
            "n_bins": int(r.size), "rms": float(np.sqrt(np.mean(r * r)))}


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
                                   edges) if _native.enabled() and floor_z_all is not None and not model.bent else None)
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
                               prior_center, half) if _native.enabled() and floor_z_all is not None
            and not (prior is not None and prior.bent) else None)
    if fast is not None:                                   # the selection below in one pass (resense/_native.py)
        xs, y, hh = fast
    else:
        near = (X > x0) & (X < x1)                # the near range only: the profile needs ~1/3 of the frame
        Xd = X[near].astype(np.float64)
        Yn, Zn = Y[near].astype(np.float64), Z[near]
        h = Zn - (floor.floor_z(Xd) if floor_z_all is None else floor_z_all[near])
        if prior is not None:
            shape = np.tan(prior.yaw) * Xd + 0.5 * prior.curvature * Xd * Xd
            if prior.bent:
                shape = shape + prior._step_y(Xd)
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
    mids_abs = mids + (np.tan(prior.yaw) * xm + 0.5 * kap * xm * xm + (prior._step_y(xm) if prior.bent else 0.0)
                       if prior is not None else 0.0)
    # line through the absolute midpoints with the prior curvature held fixed:
    # y - k x^2 / 2 = c + t x  ->  c = axis at X = 0, t = tangent at the vehicle
    w = np.sqrt(wts / max(float(wts.max()), 1e-6))
    t, c = np.polyfit(xm, mids_abs - 0.5 * kap * xm * xm, 1, w=w)
    return RailsFit(best[0], float(c), best[2], len(mids), float(t), xm, mids_abs, wts, **heads)


_RING_MIN_STATIONS = 3     # consistent ring-pair stations beyond the near rails needed as evidence
_RING_MIN_REACH = 15.0     # m beyond rails_range[1] the last of them must reach
_RING_GROUP_M = 5.0        # stations are averaged per this along-track span before the axis refit


def _ring_far_evidence(xyz: np.ndarray, ring: np.ndarray, model: TrackModel, cfg: TrackConfig,
                       near: RailsFit, x_max: float):
    """Far rail-pair centres from single ring crossings as ``(RailsFit-like, last station)``, or None.

    The stations (``resense.farrails.far_rails``) are averaged per ``_RING_GROUP_M`` so that the
    dense far evidence does not outweigh the three near slabs in the axis refit."""
    from resense.farrails import FarRailParams, far_rails
    p = FarRailParams(x_max=x_max, gauge=cfg.rails_spacing, min_stations=_RING_MIN_STATIONS)
    far = far_rails(xyz, ring, model, (float(near.xm[-1]), float(near.mids[-1])), p)
    if far.n < p.min_stations or float(far.x.max()) < cfg.rails_range[1] + _RING_MIN_REACH:
        return None
    group = np.round(far.x / _RING_GROUP_M)
    keys = np.unique(group)
    if keys.size < 2:
        return None
    xm = np.array([far.x[group == k].mean() for k in keys])
    mids = np.array([far.y[group == k].mean() for k in keys])
    wts = np.full(keys.size, float(np.median(near.wts)))
    return (RailsFit(score=float(np.median(near.wts)), center=model.center, rail_offset=model.rail_offset,
                     n_slabs=int(keys.size), xm=xm, mids=mids, wts=wts), float(far.x.max()))


def _check_far_rails(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig, near: RailsFit,
                      ring: Optional[np.ndarray] = None) -> None:
    """Replace wall-derived curvature that contradicts independently visible rails.

    Station hall walls can look like a gentle curve while the rails remain straight. A
    near rail pair fixes the tangent but cannot validate the walls' curvature at 80 m.
    Use two *independent* slabs beyond the near fit; with no far pair there is no new
    evidence and the existing range policy applies unchanged. Beyond the last rail
    slab the contradictory walls cannot validate the axis, so that range is advisory.

    With ``cfg.rails_far_rings`` and the per-point ``ring`` index of the uncorrected frame
    (``resense.farrails.ring_index``) the far rail evidence comes from single ring crossings
    (``resense.farrails``): the slab profile never finds a pair beyond ``rails_range[1]``.
    Everything after the evidence, the disagreement rule and the correction, is the same.
    """
    if (near.n_slabs < cfg.rails_yaw_min_slabs or near.xm is None or model.axis_sides == 0
            or model.axis_valid <= cfg.rails_range[1] + cfg.axis_valid_margin):
        return
    near_end = cfg.rails_range[1]
    far_cfg = replace(cfg, rails_range=(near_end, near_end + 2 * (near_end - cfg.rails_range[0])),
                      rails_yaw_slabs=2, rails_yaw_min_slabs=2)
    if abs(model.curvature) * far_cfg.rails_range[1] ** 2 / 2 <= cfg.rails_yaw_max_dev:
        return  # a wall bend this small cannot displace the far corridor appreciably
    if cfg.rails_far_rings and ring is not None:
        far = _ring_far_evidence(xyz, ring, model, cfg, near, far_cfg.rails_range[1])
        if far is None:
            return
        rails, end = far
    else:
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
            model.curv_step = 0.0
            model.axis_valid = min(model.axis_valid, end + cfg.axis_valid_margin)


def _extend_axis_from_rails(xyz: np.ndarray, model: TrackModel, cfg: TrackConfig,
                            near: Optional[RailsFit], ring: Optional[np.ndarray]) -> None:
    """Support the existing axis after wall loss with current, agreeing paired rails.

    This does not fit or change the axis. Actual supplied ring IDs keep two rail heads on
    one scan line even under mount correction; missing rings provide no evidence. The
    accepted stations retain the existing observation margin, with no straight bonus.
    ``estimate_track`` removes this extension before processing the next frame, so stale
    rail evidence cannot enter the ordinary wall-range decay or a failed floor-fit hold.
    """
    if (not cfg.rails_axis_extension or model.axis_sides != 0 or ring is None or near is None
            or near.score < cfg.rails_min_score or near.n_slabs < cfg.rails_yaw_min_slabs
            or near.xm is None or near.mids is None or near.tan_yaw is None):
        return
    from resense.farrails import FarRailParams, far_rails
    params = FarRailParams(x_max=80.0, gauge=cfg.rails_spacing, height_band=0.3, cant=0.1,
                           max_gap=10.0, min_stations=3, pair_max_forward_gap=5.0,
                           pair_use_nearer_forward=True)
    rails = far_rails(xyz, ring, model, (float(near.xm[-1]), float(near.mids[-1])), params)
    beyond = rails.x > cfg.rails_range[1]
    x = rails.x[beyond]
    # Three distinct metre stations, spanning at least five metres, cannot be supplied
    # by duplicate echoes or a single short switch fitting. Every consensus-chosen
    # station must agree with the axis; the consensus itself can reject other pairs.
    if (x.size < 3 or np.unique(np.floor(x)).size < 3 or np.ptp(x) < 5.0
            or np.any(np.abs(rails.y - model.center_y(rails.x)) > 0.10)):
        return
    end = float(np.max(x))
    supported = end + cfg.axis_valid_margin
    if supported > model.axis_valid:
        model.axis_valid_without_rails = model.axis_valid
        model.rail_axis_support = end
        model.axis_valid = supported


def rotate_track_model(model: TrackModel, dR: np.ndarray, n: int = 64) -> TrackModel:
    """The same bed, rail head and axis seen through a change of the mount correction ``dR``
    (``p_new = dR @ p_old``; 26.09, ``calibration.reseed_keep_max_deg``). Points on the bed
    profile and on the axis are rotated and the model's polynomials refitted to them (same
    degrees); everything else - the rail offset, the rail and wall state, the age and the
    floor-shadow state - is kept, so the next frame has its previous model, its floor-shadow
    reference and its rate limits as without the change. Meant for sub-degree changes.
    A v5 model (``.base`` set, ``axis_joint_min_curvature``): the carried base model and the joint shape are each
    rotated and the output composed from them again (shape choice, range caps and wall drift kept)."""
    if model.base is not None:
        base_r = rotate_track_model(model.base, dR, n)
        js = model.joint_shape
        if js is not None:
            jm = rotate_track_model(replace(model.base, center=js[0], yaw=js[1], curvature=js[2], curv_step=js[3],
                                            curv_knot=js[4]), dR, n)
            js = (jm.center, jm.yaw, jm.curvature, jm.curv_step, jm.curv_knot)
        out = replace(base_r, base=base_r, joint_shape=js, joint_used=model.joint_used, joint_reach=model.joint_reach,
                      axis_valid=model.axis_valid, axis_valid_both=model.axis_valid_both,
                      axis_valid_bent=model.axis_valid_bent, wall_drift=model.wall_drift)
        if model.joint_used and js is not None:
            out.center, out.yaw, out.curvature, out.curv_step, out.curv_knot = (float(v) for v in js)
        return out
    dR = np.asarray(dR, dtype=np.float64)
    coef = np.asarray(model.floor_coef, dtype=np.float64)
    x0, x1 = float(model.floor_range[0]), float(model.floor_range[1])
    X = np.linspace(x0, x1, n) if x1 > x0 else np.array([x0, x0 + 1.0])
    bed = np.stack([X, model.center_y(X), model.floor_z(X)], axis=1) @ dR.T
    deg = 2 if (coef.size == 3 and coef[0] != 0.0) else 1
    fc = np.polyfit(bed[:, 0], bed[:, 2], deg)
    floor_coef = np.concatenate([np.zeros(3 - fc.size), fc]) if coef.size == 3 else fc
    frange = (float(bed[0, 0]), float(bed[-1, 0])) if x1 > x0 else tuple(model.floor_range)
    xa = np.linspace(0.0, max(x1, 60.0, model.curv_knot + 100.0 if model.bent else 0.0), n)
    axis = np.stack([xa, model.center_y(xa), model.rail_z(xa)], axis=1) @ dR.T
    if model.bent:
        # 19.10: the same C1 piecewise shape, refitted with the knot kept
        xr = axis[:, 0]
        d = np.maximum(xr - model.curv_knot, 0.0)
        sol, *_ = np.linalg.lstsq(np.stack([np.ones_like(xr), xr, 0.5 * xr * xr, 0.5 * d * d], axis=1), axis[:, 1],
                                  rcond=None)
        return replace(model, floor_coef=floor_coef, floor_range=frange, center=float(sol[0]),
                       yaw=float(np.arctan(sol[1])), curvature=float(sol[2]), curv_step=float(sol[3]))
    if model.curvature != 0.0:
        k2, t, c = np.polyfit(axis[:, 0], axis[:, 1], 2)
    else:
        (t, c), k2 = np.polyfit(axis[:, 0], axis[:, 1], 1), 0.0
    return replace(model, floor_coef=floor_coef, floor_range=frange, center=float(c),
                   yaw=float(np.arctan(t)), curvature=float(2.0 * k2))


def estimate_track(xyz: np.ndarray, cfg: TrackConfig, prev: Optional[TrackModel] = None,
                   periods: int = 1, ring: Optional[np.ndarray] = None,
                   axis_ring: Optional[np.ndarray] = None, travel: Optional[float] = None) -> TrackModel:
    """Fit floor + rails + boundary-based yaw/curvature for one frame, smoothing against the
    previous model. ``periods`` is the number of nominal frame periods since ``prev`` (1 at
    the nominal rate); with ``cfg.rates_per_period`` the yaw / curvature rate limits and the
    warm-up age scale with it (physical rates per second), and with
    ``cfg.walls_smoothing_per_period`` the yaw / curvature EMA weight is ``walls_smoothing ** k``
    (the axis changes with the distance travelled); else it is ignored. The bed and rail-head
    weights stay per processed frame: they average the per-frame noise (squaring them at 5 Hz
    made the bed fit noisy enough to lose the object on the rail, EXPERIMENTS.md section 1i).
    ``ring`` (per-point ring index of the uncorrected frame) is read only by the opt-in far rail
    evidence (``cfg.rails_far_check_enabled`` with ``cfg.rails_far_rings``); None = unused.
    ``travel`` (19.10, K1): metres travelled since ``prev`` (the previous frame's speed x the time), read only with
    ``cfg.walls_smoothing_distance`` > 0: the yaw / curvature EMA exponent and the two axis rate limits then count
    ``travel / walls_smoothing_distance`` (at least ``walls_smoothing_min_k``, at most the frame periods) instead of
    frame periods, so a standing train averages its wall fits instead of following their noise; None = as before;
    not during the warm-up (``axis_warmup_frames``) after a (re)seed.
    With ``cfg.axis_joint_fit`` the tangent, curvature and curvature step come from :func:`joint_axis_fit`.
    With ``cfg.axis_joint_min_curvature`` > 0 (v5; axis_joint_fit on, axis_joint_range off) the estimate without the
    joint fit is made from its own carried state (``prev.base``) exactly as with the joint fit off, and the joint fit's
    shape (its own carried state ``prev.joint_shape``) replaces its axis shape in the returned model only on frames
    whose curvature is at least that (:func:`_joint_output`)."""
    curves_only = cfg.axis_joint_fit and not cfg.axis_joint_range and cfg.axis_joint_min_curvature > 0
    jprev: Optional[tuple] = None                 # v5: the joint fit's own shape state
    jnew: Optional[list] = None
    if curves_only and prev is not None and prev.base is not None:
        jprev, prev = prev.joint_shape, prev.base
    k = max(1, int(periods)) if cfg.rates_per_period else 1
    kw = max(1, int(periods)) if cfg.walls_smoothing_per_period else 1
    kr = k                                         # the rate-limit multiplier (19.10: per distance with K1)
    if (cfg.walls_smoothing_distance > 0 and travel is not None and np.isfinite(travel)
            and prev is not None and prev.age >= cfg.axis_warmup_frames):   # not during the warm-up after a (re)seed
        kd = abs(float(travel)) / cfg.walls_smoothing_distance
        kw = float(np.clip(kd, cfg.walls_smoothing_min_k, kw))
        kr = float(np.clip(kd, cfg.walls_smoothing_min_k, k))
    prior = prev if prev is not None else default_track_model(cfg)
    if prior.rail_axis_support > 0:
        # A previous rail extension is not a wall observation and must never be held
        # through a missing rail/floor frame or fed into the ordinary 20 m decay.
        prior = replace(prior, axis_valid=prior.axis_valid_without_rails,
                        axis_valid_without_rails=0.0, rail_axis_support=0.0)
        if prev is not None:
            prev = prior
    shadow_ref = (prev if cfg.floor_shadow_height > 0 and prev is not None and prev.age >= cfg.axis_warmup_frames
                  else None)
    # review 25.09: a held bed becomes the next frame's reference, so nothing in the rule itself ends
    # a hold (a pitch step of 3.4 deg held the bed for good: a lasting false STOP at 4.3 m); after
    # floor_shadow_max_hold held frames in a row the rule is released until no shadow is found
    release = (shadow_ref is not None and cfg.floor_shadow_max_hold > 0
               and shadow_ref.floor_hold_run >= cfg.floor_shadow_max_hold)
    info: dict = {}
    fit = _fit_floor(xyz, cfg, prior, shadow_ref=shadow_ref, info=info, release=release)
    if fit is None:
        return _joint_output(prior, jprev, cfg) if curves_only else prior
    coef, frange, n_bins, rms = fit
    if prev is not None and cfg.floor_smoothing > 0:
        a = cfg.floor_smoothing
        coef = a * prev.floor_coef + (1 - a) * coef
    model = TrackModel(
        floor_coef=coef, floor_range=frange, center=prior.center, yaw=prior.yaw,
        curvature=prior.curvature, rail_offset=prior.rail_offset, n_bins=n_bins, residual=rms,
        curv_step=prior.curv_step, curv_knot=prior.curv_knot,
        wall_quality=prior.wall_quality, axis_valid=prior.axis_valid,
        age=(prev.age + k) if prev is not None else 0,
        floor_shadow=float(info.get("shadow", 0.0)), floor_held=bool(info.get("hold", False)),
        floor_hold_run=(prev.floor_hold_run + 1 if prev is not None and (
            info.get("hold", False) or (release and info.get("shadow", 0.0) > 0)) else 0),
    )
    a_r = cfg.rails_smoothing if prev is not None else 0.0
    a_w = cfg.walls_smoothing ** kw if prev is not None else 0.0
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
    bounds: Optional[dict] = {} if cfg.walls_enabled and (cfg.axis_wall_drift > 0 or cfg.axis_joint_fit) else None
    if cfg.walls_enabled:
        est = estimate_axis_from_walls(xyz, model, cfg, t_fixed, floor_z_all=zf, far_support_run=prior.far_support_run,
                                       boundaries=bounds)
        joint = None
        if (est is not None and cfg.axis_joint_fit and t_fixed is not None and rails is not None
                and rails.score >= cfg.rails_min_score):
            joint = joint_axis_fit(rails, bounds, model, cfg)
        one_wall = False
        if joint is not None and curves_only:
            # 19.10 (v5): the joint shape with its own EMA; the model itself stays the estimate without the joint fit
            jp = jprev if jprev is not None else (prior.center, prior.yaw, prior.curvature, 0.0, 0.0)
            k_max = 1.0 / cfg.walls_min_radius
            kj = float(np.clip(joint["k"], -k_max, k_max))
            step = float(np.clip(joint["k"] + joint["step"], -k_max, k_max)) - kj
            js = (a_w * jp[3] + (1 - a_w) * step) if joint["knot"] > 0 else 0.0
            jnew = [a_r * jp[0] + (1 - a_r) * joint["c"],
                    a_w * jp[1] + (1 - a_w) * np.arctan(float(np.clip(joint["t"], -cfg.walls_max_yaw, cfg.walls_max_yaw))),
                    a_w * jp[2] + (1 - a_w) * kj, js if abs(js) >= _STEP_ZERO else 0.0]
        if joint is not None and not curves_only:
            # 19.10 (K2): one fit; the side bookkeeping (count, disagreement, reach) from each side's own fit with
            # the joint tangent, so a disagreement made only by a biased tangent no longer caps the range
            fits = {}
            for name, (xb_, yb_) in bounds.items():
                f = _fit_side(np.asarray(xb_, dtype=np.float64), np.asarray(yb_, dtype=np.float64), cfg, 0.0, joint["t"])
                if f is not None:
                    fits[name] = f
            n_sides = len(fits) or len(joint["x_max"])
            # a side with fewer than walls_min_bins bins beyond the rail range (an inner wall hidden by the curve)
            # has no curvature of its own to disagree with
            far_ok = [n for n, f in fits.items() if f[5] >= cfg.walls_min_bins]
            disagreement = abs(fits["left"][1] - fits["right"][1]) if len(far_ok) == 2 else 0.0
            q = float(min(f[2] for f in fits.values())) if fits else joint["rms"]
            one_wall = len(far_ok) < 2                     # the far range rests on one boundary at most
            model.far_support_run = est[7]
            model.center = a_r * prior.center + (1 - a_r) * joint["c"]
            model.yaw = a_w * prior.yaw + (1 - a_w) * np.arctan(float(np.clip(joint["t"], -cfg.walls_max_yaw,
                                                                                   cfg.walls_max_yaw)))
            k_max = 1.0 / cfg.walls_min_radius
            model.curvature = a_w * prior.curvature + (1 - a_w) * float(np.clip(joint["k"], -k_max, k_max))
            step = float(np.clip(joint["k"] + joint["step"], -k_max, k_max)) - float(np.clip(joint["k"], -k_max, k_max))
            model.curv_knot = joint["knot"]
            model.curv_step = (a_w * prior.curv_step + (1 - a_w) * step) if joint["knot"] > 0 else 0.0
            if abs(model.curv_step) < _STEP_ZERO:          # numerically no step: the quadratic (native kernels)
                model.curv_step = 0.0
            model.wall_quality = q
            # the reach of each side against the final axis (smoothed; the one the corridor uses): as far as the
            # boundary stays parallel to it, at least as far as the joint fit followed it this frame
            reach = [max(joint["x_max"].get(n, 0.0), _followed_reach(xb_, yb_, model, cfg))
                     for n, (xb_, yb_) in bounds.items() if len(xb_)]
            reach = [r_ for r_ in reach if r_ > 0] or list(joint["x_max"].values())
            x_valid, x_valid_min = float(max(reach)), float(min(reach))
            if not cfg.axis_joint_range:
                # 20.10 (v4, axis_joint_range off): the joint fit sets the axis shape only; the trusted range, the
                # side count, the disagreement and the wall quality stay those of the per-side fits (as without the
                # joint fit), so the range policy of the straight track is unchanged
                _, curv_est, q, x_valid, n_sides, disagreement, x_valid_min, model.far_support_run = est
                model.wall_quality = q
                one_wall = False
                model.curv_range = a_w * prior.curv_range + (1 - a_w) * curv_est
        if (joint is None or curves_only) and est is not None:
            tan_yaw, curv, q, x_valid, n_sides, disagreement, x_valid_min, model.far_support_run = est
            model.yaw = a_w * prior.yaw + (1 - a_w) * np.arctan(tan_yaw)
            model.curvature = a_w * prior.curvature + (1 - a_w) * curv
            if model.bent:                                  # 19.10: no joint fit this frame: the step decays
                model.curv_step = a_w * prior.curv_step
                if abs(model.curv_step) < _STEP_ZERO:
                    model.curv_step = 0.0
            model.wall_quality = q
        if est is not None:
            model.axis_sides = n_sides
            model.axis_valid = x_valid + cfg.axis_valid_margin
            agree = n_sides == 2 and (cfg.axis_sides_max_disagreement <= 0 or disagreement <= cfg.axis_sides_max_disagreement)
            # 19.10: with a curvature step, "straight" is the same lateral bend at _STRAIGHT_X as |curvature| < 1e-4
            bend = model.curvature + (model.curv_step * (max(_STRAIGHT_X - model.curv_knot, 0.0) / _STRAIGHT_X) ** 2
                                      if model.bent else 0.0)
            if joint is not None and not cfg.axis_joint_range and not curves_only:
                bend = model.curv_range                      # v4: the straight test of the per-side fits, as before
            lim = (1.5e-4 if (cfg.axis_joint_fit and cfg.axis_joint_range and prior.axis_straight)
                   else 1e-4)                               # 19.10: hysteresis (joint fit with its own range)
            straight = abs(bend) < lim and q < 0.2 and (agree or cfg.axis_one_side_range <= 0)
            model.axis_straight = bool(straight)
            bonus = cfg.axis_valid_straight_bonus if straight else 0.0
            model.axis_valid += bonus
            # 25.09: the range both boundaries support (cluster.far_axis_both_sides); the caps
            # below apply to it through min(axis_valid, ...) where it is read
            model.axis_valid_both = (x_valid_min + cfg.axis_valid_margin + bonus) if n_sides == 2 else model.axis_valid
            if n_sides == 2 and not straight:
                model.axis_valid_bent = x_valid_min + cfg.axis_valid_margin
            if cfg.axis_one_side_range > 0 and (n_sides == 1 or (joint is not None and one_wall)):
                # one boundary alone cannot tell a parallel wall from a diverging one
                model.axis_valid = min(model.axis_valid, cfg.axis_one_side_range)
            if n_sides == 2 and cfg.axis_sides_max_disagreement > 0 and disagreement > cfg.axis_sides_max_disagreement:
                # the two boundaries bend differently (transition, cavern, platform hall):
                # whichever side won, the corridor beyond the disagreement is a guess
                model.axis_valid = min(model.axis_valid, cfg.axis_disagree_range)
                model.disagree_left = max(0, int(cfg.axis_disagree_hold))
            elif n_sides == 1 and cfg.axis_disagree_hold > 0 and prior.disagree_left > 0:
                # 27.09 (P4 history, axis_disagree_hold): the contradicting boundary was lost, not
                # resolved - one boundary cannot tell which of the two was right, so the cap of the
                # disagreement outlives it for a bounded time (two agreeing boundaries end it)
                model.axis_valid = min(model.axis_valid, cfg.axis_disagree_range)
                model.disagree_left = max(0, prior.disagree_left - k)
        else:
            # no boundary parallel to the track this frame: the rails alone give the tangent,
            # the curvature (unsupported now) decays towards straight and the trusted range
            # shrinks; without rails the corridor keeps its shape (no jump on a bad frame)
            floor_valid = cfg.walls_range[0] + cfg.axis_valid_margin
            if t_fixed is not None:
                model.yaw = a_w * prior.yaw + (1 - a_w) * np.arctan(t_fixed)
                model.curvature = a_w * prior.curvature
                model.curv_step = a_w * prior.curv_step if abs(a_w * prior.curv_step) >= _STEP_ZERO else 0.0
                floor_valid = cfg.rails_range[1] + cfg.axis_valid_margin
            model.axis_valid = max(floor_valid, prior.axis_valid - 20.0)
            model.axis_sides = 0            # axis_valid_both keeps its default: no second limit
            model.disagree_left = max(0, prior.disagree_left - k)
    else:
        model.yaw = np.radians(cfg.yaw_deg)
        model.curvature = cfg.curvature
        model.curv_step = 0.0
        model.axis_valid = 1e9
    if prev is not None and prev.age >= cfg.axis_warmup_frames:
        # the vehicle cannot turn by more than a fraction of a degree per frame, nor can the
        # curvature ahead change faster than along a transition curve: larger jumps are
        # estimator noise (a boundary flipping between two structures) and are clipped.
        # Not during the warm-up after a (re)seed (v0.6): a wrong first-frame estimate (a free
        # wall fit clipped at 5 deg on a cold start mid-ride) would otherwise take 30+ frames
        # to unwind at 0.17 deg per frame.
        if cfg.axis_max_yaw_rate > 0:
            r = kr * cfg.axis_max_yaw_rate
            model.yaw = float(np.clip(model.yaw, prev.yaw - r, prev.yaw + r))
        if cfg.axis_max_curvature_rate > 0:
            r = kr * cfg.axis_max_curvature_rate
            model.curvature = float(np.clip(model.curvature, prev.curvature - r, prev.curvature + r))
            if model.bent or prev.bent:
                model.curv_step = float(np.clip(model.curv_step, prev.curv_step - r, prev.curv_step + r))
    if curves_only:
        # 19.10 (v5): without a joint fit this frame the joint shape follows this estimate and its step decays; its own
        # rate limits against its previous state, as the model's above
        jp = jprev if jprev is not None else (prior.center, prior.yaw, prior.curvature, 0.0, 0.0)
        if jnew is None:
            js = a_w * jp[3]
            jnew = [model.center, model.yaw, model.curvature, js if abs(js) >= _STEP_ZERO else 0.0]
        if jprev is not None and prev is not None and prev.age >= cfg.axis_warmup_frames:
            if cfg.axis_max_yaw_rate > 0:
                r = kr * cfg.axis_max_yaw_rate
                jnew[1] = float(np.clip(jnew[1], jp[1] - r, jp[1] + r))
            if cfg.axis_max_curvature_rate > 0:
                r = kr * cfg.axis_max_curvature_rate
                jnew[2] = float(np.clip(jnew[2], jp[2] - r, jp[2] + r))
                if jnew[3] != 0.0 or jp[3] != 0.0:
                    jnew[3] = float(np.clip(jnew[3], jp[3] - r, jp[3] + r))
        knot = float(cfg.axis_joint_knot) if cfg.axis_joint_knot > cfg.rails_range[1] else 0.0
        jnew = (float(jnew[0]), float(jnew[1]), float(jnew[2]), float(jnew[3]) if knot > 0 else 0.0, knot)
    if cfg.rails_far_check_enabled and rails is not None and cfg.walls_enabled:
        _check_far_rails(xyz, model, cfg, rails, ring)
    if cfg.walls_enabled:
        _extend_axis_from_rails(xyz, model, cfg, rails, axis_ring)
    if bounds and cfg.axis_wall_drift > 0:
        # 15.10: against the final axis (smoothed, rate-limited), the one the corridor uses
        model.wall_drift = wall_drift_range(bounds, model, cfg)
    model.floor_verified = verify_floor_extrapolation(xyz, model, cfg, floor_z_all=zf)
    if curves_only:
        return _joint_output(model, jnew, cfg, bounds)
    return model


def _joint_output(base: TrackModel, jshape: Optional[tuple], cfg: TrackConfig,
                  bounds: Optional[dict] = None) -> TrackModel:
    """The returned model with ``axis_joint_min_curvature`` > 0 (19.10, v5): ``base`` (the estimate without the joint
    fit, carried as ``.base`` to the next frame as its state) with the joint fit's shape ``jshape`` (centre, yaw,
    curvature, curv_step, curv_knot; carried as ``.joint_shape``) in place of its axis shape when ``base``'s curvature is
    |k| >= ``axis_joint_min_curvature`` (``.joint_used``): on a straight section the output is ``base`` itself, on a curve
    the corridor follows the joint shape and the trusted range stays ``base``'s; the wall drift is then measured against
    that shape and, with ``axis_joint_reach_cap`` (v5b), the trusted range is also capped at the farthest boundary's
    reach along it plus ``axis_valid_margin`` (both boundaries' nearer reach for ``axis_valid_both``; ``.joint_reach``).
    ``axis_joint_reach_dual`` (20.10, v5c) > 0 moves that end out by as much (never past ``base``'s own range); beyond
    ``.joint_reach`` an obstacle then also needs the base axis' gauge (``Detector._dual_zone``).
    ``bounds``: :func:`estimate_axis_from_walls`' boundaries of this frame, or None (no re-measure, no cap)."""
    use = jshape is not None and abs(base.curvature) >= cfg.axis_joint_min_curvature
    out = replace(base, base=base, joint_shape=jshape, joint_used=bool(use), joint_reach=0.0)
    if not use:
        return out
    out.center, out.yaw, out.curvature, out.curv_step, out.curv_knot = (float(v) for v in jshape)
    if bounds and cfg.axis_wall_drift > 0:
        out.wall_drift = wall_drift_range(bounds, out, cfg)
    if bounds and cfg.axis_joint_reach_cap:
        reach = [_followed_reach(x, y, out, cfg) for x, y in bounds.values() if len(x)]
        reach = [r_ for r_ in reach if r_ > 0]
        if reach:
            cap = max(reach) + cfg.axis_valid_margin
            both = (min(reach) + cfg.axis_valid_margin) if len(reach) == 2 else cap
            if cap < out.axis_valid:
                out.joint_reach = cap
            # 20.10 (v5c, axis_joint_reach_dual): on a frame the cap shortened, the range goes on beyond it (never
            # past base's), where the detector holds an obstacle to both gauges, the joint shape's and base's
            ext = max(float(cfg.axis_joint_reach_dual), 0.0) if out.joint_reach > 0 else 0.0
            out.axis_valid = min(out.axis_valid, cap + ext)
            out.axis_valid_both = min(out.axis_valid_both, both + ext)
            if out.axis_valid_bent < 1e9:
                out.axis_valid_bent = min(out.axis_valid_bent, both + ext)
    return out
