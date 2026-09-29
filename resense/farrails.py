"""Far rail evidence from single LiDAR ring crossings (beyond the near rail tracker's 30 m).

The near rail tracker (``track.estimate_rails``) needs three returns per 5 cm profile bin, so it
stops at ~30 m. Beyond that a ring crosses each rail head once or twice, but the two heads of a
rail pair still sit one gauge apart on the *same* ring, and pairs found on many rings must lie on
one smooth offset curve that starts at the last near rail. That is the idea of the
``Tactical-Inventor/LCT-2026.NIIstovye`` repository (``route/_core/far_rails.py``; see
docs/COMPETITOR_REVIEW_2026-09-29.md), written here from its description: a vectorised lateral-cell
grid per ring instead of per-ring loops, and no numba.

It is the evidence source ``track._check_far_rails`` lacks: that check corrects a wall-derived
curvature that contradicts the rails (a station hall's walls look like a gentle curve while the rails
stay straight), but its slab profile never finds a rail pair beyond 30 m
(docs/archive/EXPERIMENTS_log_2026-09.md 1f, 1h), so it never fires. Opt-in, off by default:
``track.rails_far_check_enabled`` and ``track.rails_far_rings``.

Ring identity comes from the elevation angle of a return in the *sensor* frame (the axis-permuted
frame before the mount correction), snapped to the measured ring table: after the mount correction
a tilted mount smears a ring's elevation across its azimuth, and the two heads of one pair (1.6 m
apart, ~2 deg of azimuth at 50 m) would fall in different bins.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np

from resense.sensor import RING_ELEVATION_DEG

_RING_ORDER = np.argsort(RING_ELEVATION_DEG)
_RING_SORTED = RING_ELEVATION_DEG[_RING_ORDER]


@dataclass(frozen=True)
class FarRailParams:
    """Thresholds of the pairing and of the consensus, in metres unless stated."""
    x_max: float = 80.0          # rail heads are gone beyond this
    reach: float = 2.6           # lateral search band about the reference line
    height_band: float = 1.5     # about the rail-head plane
    cell: float = 0.10           # lateral cell of a ring's height profile
    bump: float = 0.06           # a rail head stands this far above the median of its neighbourhood
    gauge: float = 1.59          # rail-head centre to centre (track.rails_spacing)
    gauge_tol: float = 0.10
    cant: float = 0.25           # the two heads of a pair differ in height by less than this
    max_offset: float = 0.8      # furthest a far centre may lie from the reference line
    max_slope: float = 0.03      # offset curve e(t) = a t + b t^2 from the anchor: |a| ...
    max_curv: float = 4e-4       # ... and |b|
    inlier: float = 0.08
    min_stations: int = 2
    max_gap: float = 15.0        # a chain broken for longer is not the same rails any more
    ring_tol_deg: float = 0.04   # a return further than this from every ring elevation has no ring


@dataclass
class FarRails:
    x: np.ndarray = field(default_factory=lambda: np.empty(0))       # stations along the track
    y: np.ndarray = field(default_factory=lambda: np.empty(0))       # rail-pair centres, absolute Y
    n_candidates: int = 0                                            # ring pairs before the consensus
    curve: Optional[tuple] = None                                    # (a, b) of the chosen offset curve

    @property
    def n(self) -> int:
        return int(self.x.size)


_RING_TAN = np.tan(np.radians(_RING_SORTED))
_RING_SEC2 = 1.0 + _RING_TAN * _RING_TAN


def ring_index(xyz_sensor: np.ndarray, tol_deg: float = 0.04, band: Optional[tuple] = None) -> np.ndarray:
    """Index into ``RING_ELEVATION_DEG`` of each point's ring, -1 where no ring is within ``tol_deg``.

    ``xyz_sensor`` is the axis-permuted sensor frame (X forward, Y left, Z up) *before* any mount
    correction: only there is a ring a constant elevation. ``band = (x_lo, x_hi, |y|_max, z_max)`` restricts
    the work to the far corridor below the sensor that the rail search uses (every other point gets -1):
    ~5-15 ms instead of ~40 ms on a 350 k-point cloud. The lookup is in slope space (one sqrt, one
    divide, one ``searchsorted``)."""
    xyz = np.asarray(xyz_sensor)
    if band is not None:
        x_lo, x_hi, y_max, z_max = band
        idx = np.flatnonzero((xyz[:, 0] > x_lo) & (xyz[:, 0] < x_hi) & (np.abs(xyz[:, 1]) < y_max)
                             & (xyz[:, 2] < z_max))
        out = np.full(xyz.shape[0], -1, np.int16)
        out[idx] = ring_index(xyz[idx], tol_deg)
        return out
    x, y, z = (xyz[:, k].astype(np.float32, copy=False) for k in range(3))
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = z / np.sqrt(x * x + y * y)
    pos = np.searchsorted(_RING_TAN, slope)
    lo = np.clip(pos - 1, 0, _RING_TAN.size - 1)
    hi = np.clip(pos, 0, _RING_TAN.size - 1)
    d_lo = np.abs(slope - _RING_TAN[lo])
    d_hi = np.abs(slope - _RING_TAN[hi])
    near = np.where(d_lo <= d_hi, lo, hi)
    tol = np.radians(tol_deg) * _RING_SEC2[near]                 # the same angular tolerance in slope space
    ok = np.minimum(d_lo, d_hi) <= tol
    return np.where(ok, _RING_ORDER[near], -1).astype(np.int16)


def _shift(a: np.ndarray, k: int) -> np.ndarray:
    """``out[:, j] = a[:, j - k]``, NaN where there is no source column."""
    out = np.full_like(a, np.nan)
    if k > 0:
        out[:, k:] = a[:, :-k]
    elif k < 0:
        out[:, :k] = a[:, -k:]
    else:
        out[:] = a
    return out


def ring_pairs(xyz: np.ndarray, ring: np.ndarray, ref_y: Callable, rail_z: Callable,
               s_min: float, p: FarRailParams) -> np.ndarray:
    """Rail-pair candidates ``(s, e, gauge)``: two equal bumps one gauge apart on one ring.

    ``xyz`` is the corrected vehicle frame, ``ring`` the per-point ring index (``ring_index`` of the
    uncorrected points), ``ref_y(x)`` the reference line and ``rail_z(x)`` the rail-head plane. ``e``
    is the offset of the pair's centre from the reference line."""
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    sel = np.flatnonzero((ring >= 0) & (x > s_min) & (x < p.x_max))
    if sel.size < 8:
        return np.empty((0, 3))
    off = y[sel] - ref_y(x[sel])
    h = z[sel] - rail_z(x[sel])
    keep = (np.abs(off) < p.reach) & (np.abs(h) < p.height_band)
    sel, off, h = sel[keep], off[keep], h[keep]
    if sel.size < 8:
        return np.empty((0, 3))
    rows_u, row = np.unique(ring[sel], return_inverse=True)
    n_col = int(np.ceil(2.0 * p.reach / p.cell))
    col = np.clip(((off + p.reach) // p.cell).astype(np.int64), 0, n_col - 1)
    cell = row.astype(np.int64) * n_col + col
    order = np.lexsort((h, cell))                       # by cell, then by height: the last is the highest
    cell_sorted = cell[order]
    last = np.r_[cell_sorted[1:] != cell_sorted[:-1], True]
    top = order[last]
    shape = (rows_u.size, n_col)
    grid_h, grid_o, grid_x = (np.full(shape, np.nan) for _ in range(3))
    grid_h.flat[cell_sorted[last]] = h[top]
    grid_o.flat[cell_sorted[last]] = off[top]
    grid_x.flat[cell_sorted[last]] = x[sel][top]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN neighbourhoods are simply no peak
        around = np.stack([_shift(grid_h, k) for k in (-3, -2, -1, 1, 2, 3)])
        n_around = np.isfinite(around).sum(axis=0)
        median = np.nanmedian(around, axis=0)
        side = np.nanmax(np.stack([_shift(grid_h, -1), _shift(grid_h, 1)]), axis=0)
    peak = (np.isfinite(grid_h) & (n_around >= 2) & (grid_h - median >= p.bump)
            & ~(grid_h < np.where(np.isfinite(side), side, -np.inf)))
    out = []
    for r in np.flatnonzero(peak.any(axis=1)):
        c = np.flatnonzero(peak[r])
        o, hh, xx = grid_o[r, c], grid_h[r, c], grid_x[r, c]
        gap = o[None, :] - o[:, None]
        ok = (np.triu(np.ones((c.size, c.size), bool), 1) & (np.abs(gap - p.gauge) < p.gauge_tol)
              & (np.abs(hh[None, :] - hh[:, None]) < p.cant))
        for i, j in zip(*np.nonzero(ok)):
            out.append(((xx[i] + xx[j]) / 2.0, (o[i] + o[j]) / 2.0, gap[i, j]))
    if not out:
        return np.empty((0, 3))
    cand = np.array(out)
    cand = cand[(np.abs(cand[:, 1]) < p.max_offset) & (cand[:, 0] > s_min)]
    if cand.size == 0:
        return np.empty((0, 3))
    _, first = np.unique(np.round(cand[:, :2], 2), axis=0, return_index=True)
    return cand[np.sort(first)]


def consensus(s: np.ndarray, e: np.ndarray, s0: float, e0: float, p: FarRailParams):
    """Candidates that agree on one offset curve ``e0 + a t + b t^2`` (t = s - s0) from the anchor.

    Every candidate and every pair of candidates proposes a curve through the anchor; the curve whose
    inliers (within ``inlier``) cover the most distinct 1 m stations wins, ties broken by residual.
    A single wrong pair (a platform edge, the neighbouring track) cannot steer the rest, which
    following pairs one by one cannot promise. Returns (mask, (a, b)) or (all False, None)."""
    n = s.size
    none = np.zeros(n, bool)
    if n == 0:
        return none, None
    t, d = s - s0, e - e0
    a_list, b_list = [d / t], [np.zeros(n)]                # a line through the anchor and one candidate
    if n > 1:
        i, j = np.triu_indices(n, 1)
        ti, tj, di, dj = t[i], t[j], d[i], d[j]
        det = ti * tj * tj - tj * ti * ti
        ok = np.abs(ti - tj) >= 2.0
        det = np.where(ok, det, 1.0)
        a_list.append(np.where(ok, (di * tj * tj - dj * ti * ti) / det, np.inf))
        b_list.append(np.where(ok, (ti * dj - tj * di) / det, np.inf))
    a, b = np.concatenate(a_list), np.concatenate(b_list)
    ok = (np.abs(b) <= p.max_curv) & (np.abs(a) <= p.max_slope)
    if not ok.any():
        return none, None
    a, b = a[ok], b[ok]
    residual = np.abs(a[:, None] * t + b[:, None] * t * t - d)
    inlier = residual < p.inlier
    stations = np.round(s)
    score = np.array([np.unique(stations[row]).size for row in inlier], float) \
        - 0.1 * np.where(inlier, residual, 0.0).sum(axis=1) / p.inlier
    k = int(np.argmax(score))
    return inlier[k], (float(a[k]), float(b[k]))


def far_rails(xyz: np.ndarray, ring: np.ndarray, model, anchor: tuple,
              p: FarRailParams = FarRailParams()) -> FarRails:
    """Far rail centres beyond the last near rail station.

    ``model`` supplies the reference line (its tangent at the vehicle, wall curvature removed, as
    ``track._check_far_rails`` does) and the rail-head plane; ``anchor`` is ``(s0, y0)``, the last
    near rail-pair centre."""
    tan_yaw, centre = float(np.tan(model.yaw)), float(model.center)

    def ref_y(xv):
        return centre + tan_yaw * np.asarray(xv, dtype=np.float64)

    s0, y0 = float(anchor[0]), float(anchor[1])
    cand = ring_pairs(xyz, ring, ref_y, model.rail_z, s0 + 0.5, p)
    if cand.shape[0] == 0:
        return FarRails()
    mask, curve = consensus(cand[:, 0], cand[:, 1], s0, y0 - float(ref_y(s0)), p)
    if mask.sum() < p.min_stations:
        return FarRails(n_candidates=int(cand.shape[0]))
    chosen = cand[mask]
    chosen = chosen[np.argsort(chosen[:, 0])]
    cut = np.flatnonzero(np.diff(np.r_[s0, chosen[:, 0]]) > p.max_gap)
    if cut.size:
        chosen = chosen[:cut[0]]
    if chosen.shape[0] < p.min_stations:
        return FarRails(n_candidates=int(cand.shape[0]))
    return FarRails(x=chosen[:, 0], y=chosen[:, 1] + ref_y(chosen[:, 0]),
                    n_candidates=int(cand.shape[0]), curve=curve)


def would_correct_axis(rails: FarRails, model, rails_bin: float, yaw_max_dev: float) -> bool:
    """The disagreement rule of ``track._check_far_rails``: every far centre on the same side of
    our axis, all further than half a profile bin, and at least one beyond ``yaw_max_dev``."""
    if rails.n < 2:
        return False
    err = rails.y - model.center_y(rails.x)
    return bool(np.all(np.sign(err) == np.sign(err[0])) and np.min(np.abs(err)) > 0.5 * rails_bin
                and np.max(np.abs(err)) > yaw_max_dev)
