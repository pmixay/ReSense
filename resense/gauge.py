"""Clearance-gauge corridor: which points violate the envelope the train needs."""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from resense import _native
from resense.config import GaugeConfig
from resense.track import TrackModel


def point_in_polygon(px: np.ndarray, py: np.ndarray, poly) -> np.ndarray:
    """Vectorised even-odd point-in-polygon test. ``poly`` = list of (x, y)."""
    poly = np.asarray(poly, dtype=np.float64)
    n = poly.shape[0]
    inside = np.zeros(px.shape[0], dtype=bool)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cond = (yi > py) != (yj > py)
        denom = (yj - yi)
        with np.errstate(divide="ignore", invalid="ignore"):
            x_int = xi + (py - yi) * (xj - xi) / np.where(denom == 0, np.inf, denom)
        inside ^= cond & (px < x_int)
        j = i
    return inside


def widened_profile(cfg: GaugeConfig, margin: float):
    """Profile whose outer (widest) edges are pushed out by ``margin``; the inner low zone
    between the rails is kept, so track hardware next to the rails does not enter the
    advisory zone."""
    p = np.asarray(cfg.profile, dtype=np.float64)
    out = p.copy()
    outer = np.abs(p[:, 0]) >= 0.99 * np.abs(p[:, 0]).max()
    out[outer, 0] = p[outer, 0] + np.sign(p[outer, 0]) * margin
    return out


def corridor_coordinates(xyz: np.ndarray, track: TrackModel):
    """(dy, h): lateral offset from the track axis and height above the rail head."""
    if _native.enabled() and np.asarray(track.floor_coef).size == 3:
        res = _native.corridor_coordinates(xyz, track.floor_range, np.asarray(track.floor_coef, dtype=np.float64),
                                           track.rail_offset, *track.center_coefs())
        if res is not None:
            return res
    X = xyz[:, 0].astype(np.float64)
    dy = xyz[:, 1] - track.center_y(X)
    h = xyz[:, 2] - track.rail_z(X)
    return dy, h


def corridor_mask(xyz: np.ndarray, track: TrackModel, cfg: GaugeConfig,
                  dy_all: Optional[np.ndarray] = None, h_all: Optional[np.ndarray] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (mask_any, in_gauge): points inside the warning corridor, and among the
    whole frame, which are inside the strict gauge. ``dy_all`` / ``h_all`` are the corridor
    coordinates of the whole frame when the caller already has them."""
    X = xyz[:, 0]
    mask = np.zeros(xyz.shape[0], dtype=bool)
    strict = np.zeros(xyz.shape[0], dtype=bool)
    if dy_all is not None and h_all is not None and cfg.lateral_growth_per_100m <= 0 and _native.enabled():
        # the range test and the bounding box below in one pass (resense/_native.py): frame indices
        poly = widened_profile(cfg, cfg.warning_margin)
        box = _native.select(xyz.shape[0], (dy_all, None, None, "<=", np.abs(poly[:, 0]).max(), True),
                             (h_all, ">=", poly[:, 1].min(), "<=", poly[:, 1].max()),
                             (X, ">=", cfg.range_min, "<=", cfg.range_max))
        if box is not None:
            if box.size == 0:
                return mask, strict
            sub = box[point_in_polygon(dy_all[box], h_all[box], poly)]
            mask[sub] = True
            if sub.size:
                strict[sub[point_in_polygon(dy_all[sub], h_all[sub], cfg.profile)]] = True
            return mask, strict
    in_range = (X >= cfg.range_min) & (X <= cfg.range_max)
    if not in_range.any():
        return mask, strict
    idx = np.flatnonzero(in_range)
    if dy_all is not None and h_all is not None:
        dy, h = dy_all[idx], h_all[idx]
    else:
        dy, h = corridor_coordinates(xyz[idx], track)
    if cfg.lateral_growth_per_100m > 0:
        dy = dy / (1.0 + cfg.lateral_growth_per_100m * X[idx] / 100.0)
    poly = widened_profile(cfg, cfg.warning_margin)
    # bounding-box prefilter: the polygon test on ~190k points costs 6 ms, on the few
    # thousand points inside the box well under 1 ms
    box = np.flatnonzero((np.abs(dy) <= np.abs(poly[:, 0]).max()) & (h >= poly[:, 1].min()) & (h <= poly[:, 1].max()))
    if box.size == 0:
        return mask, strict
    sub = box[point_in_polygon(dy[box], h[box], poly)]
    mask[idx[sub]] = True
    if sub.size:
        strict[idx[sub[point_in_polygon(dy[sub], h[sub], cfg.profile)]]] = True
    return mask, strict


def gauge_core_mask(dy: np.ndarray, h: np.ndarray, X: np.ndarray, cfg: GaugeConfig) -> np.ndarray:
    """Strict-gauge membership with the lateral edge margin (v0.5): a point counts only when it
    lies ``edge_margin + edge_margin_per_100m * X / 100`` inside the polygon's lateral edge,
    i.e. it is tested at |dy| + margin. The axis is uncertain by about 0.1 deg (0.1 m per
    60 m), so a return a few centimetres inside the edge at range is not evidence of an
    object in the gauge; candidates and the advisory zone are unaffected."""
    m = cfg.edge_margin + cfg.edge_margin_per_100m * np.asarray(X, dtype=np.float64) / 100.0
    if not np.any(m > 0):
        return point_in_polygon(dy, h, cfg.profile)
    return point_in_polygon(dy + np.sign(dy) * m, h, cfg.profile)


def gauge_reach_mask(dy: np.ndarray, h: np.ndarray, X: np.ndarray, cfg: GaugeConfig) -> np.ndarray:
    """Points that may lie inside the strict gauge within the axis uncertainty (review 25.09): the
    polygon tested at ``|dy| - margin``, the margin by which :func:`gauge_core_mask` shrinks the
    strict decision (``edge_margin + edge_margin_per_100m * X / 100``), after the lateral growth of
    :func:`corridor_mask`, or inside the polygon itself (so the unshrunk envelope, and with it the
    strict-gauge mask, is a subset whatever the profile's shape): the nearest point of an object in
    it is never farther than its nearest point inside the envelope, nor than where it truly enters
    the envelope while the axis is off by less than the margin. Used for the distance of a gauge
    cluster (``cluster.gauge_distance``), never for the decision."""
    X = np.asarray(X, dtype=np.float64)
    dy = np.asarray(dy, dtype=np.float64)
    h = np.asarray(h, dtype=np.float64)
    if cfg.lateral_growth_per_100m > 0:
        dy = dy / (1.0 + cfg.lateral_growth_per_100m * X / 100.0)
    m = np.maximum(cfg.edge_margin + cfg.edge_margin_per_100m * X / 100.0, 0.0)
    return (point_in_polygon(dy, h, cfg.profile)
            | point_in_polygon(np.sign(dy) * np.maximum(np.abs(dy) - m, 0.0), h, cfg.profile))


def axis_union_offset(X: np.ndarray, track: TrackModel, cfg: GaugeConfig) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Where the envelope is also measured from the sensor axis (26.09, ``gauge.axis_union``; judge A
    action 7): ``(ok, c)`` per point, ``c`` = the rail axis minus the sensor axis at the point's X
    (``track.center_y``; the processed frame's X axis is the sensor axis whenever the mount calibration
    applies no yaw, below ``calibration.min_yaw_deg``), ``ok`` = inside the region where the two
    references agree: range_min <= X <= ``axis_union_range`` and |c| <= ``axis_union_max_offset``.
    ``None`` when the option is off or the frame is not eligible: no rail pair in the near range
    (``track.rail_slabs == 0``) or |curvature| > ``axis_union_max_curvature`` (a curve, where the
    sensor axis leaves the track as X^2 / 2R)."""
    if cfg.axis_union <= 0 or track.rail_slabs <= 0 or abs(float(track.curvature)) > cfg.axis_union_max_curvature:
        return None
    X = np.asarray(X, dtype=np.float64)
    ok = (X >= cfg.range_min) & (X <= cfg.axis_union_range)
    if not ok.any():
        return None
    c = np.zeros(X.shape[0], dtype=np.float64)
    c[ok] = track.center_y(X[ok])
    ok &= np.abs(c) <= cfg.axis_union_max_offset
    if not ok.any():
        return None
    c[~ok] = 0.0
    return ok, c


def axis_union_strict(X: np.ndarray, dy: np.ndarray, h: np.ndarray, track: TrackModel,
                      cfg: GaugeConfig) -> Optional[np.ndarray]:
    """``gauge.axis_union`` 1 (candidate A): the points that are inside the strict envelope measured
    from the sensor axis (``dy + c``), edge margin included, within the region of
    :func:`axis_union_offset`; ``None`` when it does not apply. OR-ed into the strict membership
    measured from the rails; nothing else changes (with ``axis_union_max_offset`` below
    ``warning_margin`` the rail advisory corridor already holds these points)."""
    reg = axis_union_offset(X, track, cfg)
    if reg is None:
        return None
    ok, c = reg
    out = np.zeros(ok.shape[0], dtype=bool)
    i = np.flatnonzero(ok)
    ya = np.asarray(dy, dtype=np.float64)[i] + c[i]
    hh = np.asarray(h, dtype=np.float64)[i]
    inside = point_in_polygon(ya, hh, cfg.profile)
    if cfg.edge_margin > 0 or cfg.edge_margin_per_100m > 0:
        inside &= gauge_core_mask(ya, hh, np.asarray(X, dtype=np.float64)[i], cfg)
    out[i] = inside
    return out


def axis_union_coordinates(X: np.ndarray, dy: np.ndarray, track: TrackModel, cfg: GaugeConfig) -> np.ndarray:
    """``gauge.axis_union`` 2 (candidate B): the corridor coordinate re-measured so that the strict
    envelope is the union of the rail and the sensor-axis envelopes. Within the region of
    :func:`axis_union_offset`, on the side towards which the sensor axis lies off the rail axis
    (``s = -sign(c)``, ``e = |c|``, ``u = s * dy >= 0``): ``u' = max(u - e, u * W / (W + e))`` with
    ``W`` the envelope half-width - continuous and monotone, ``W + e`` maps to ``W`` and beyond it
    the lateral is the one from the sensor axis (``u - e``); the other side and every point outside
    the region keep ``dy``. Returns ``dy`` itself when nothing changes."""
    reg = axis_union_offset(X, track, cfg)
    if reg is None:
        return dy
    ok, c = reg
    i = np.flatnonzero(ok)
    d = np.asarray(dy, dtype=np.float64)[i]
    s = -np.sign(c[i])
    e = np.abs(c[i])
    u = s * d
    W = float(np.abs(np.asarray(cfg.profile, dtype=np.float64)[:, 0]).max())
    wide = (u > 0) & (e > 0)
    u2 = np.maximum(u - e, u * W / (W + e))
    out = np.array(dy, dtype=np.float64, copy=True)
    out[i] = np.where(wide, s * u2, d)
    return out


def profile_bounds(cfg: GaugeConfig):
    p = np.asarray(cfg.profile)
    return float(p[:, 0].min()), float(p[:, 0].max()), float(p[:, 1].min()), float(p[:, 1].max())
