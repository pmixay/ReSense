"""Clearance-gauge corridor: which points violate the envelope the train needs."""
from __future__ import annotations

from typing import Tuple

import numpy as np

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
    X = xyz[:, 0].astype(np.float64)
    dy = xyz[:, 1] - track.center_y(X)
    h = xyz[:, 2] - track.rail_z(X)
    return dy, h


def corridor_mask(xyz: np.ndarray, track: TrackModel, cfg: GaugeConfig) -> Tuple[np.ndarray, np.ndarray]:
    """Returns (mask_any, in_gauge): points inside the warning corridor, and among the
    whole frame, which are inside the strict gauge."""
    X = xyz[:, 0]
    in_range = (X >= cfg.range_min) & (X <= cfg.range_max)
    mask = np.zeros(xyz.shape[0], dtype=bool)
    strict = np.zeros(xyz.shape[0], dtype=bool)
    if not in_range.any():
        return mask, strict
    idx = np.flatnonzero(in_range)
    dy, h = corridor_coordinates(xyz[idx], track)
    if cfg.lateral_growth_per_100m > 0:
        dy = dy / (1.0 + cfg.lateral_growth_per_100m * X[idx] / 100.0)
    wide = point_in_polygon(dy, h, widened_profile(cfg, cfg.warning_margin))
    sub = np.flatnonzero(wide)
    mask[idx[sub]] = True
    if sub.size:
        strict[idx[sub[point_in_polygon(dy[sub], h[sub], cfg.profile)]]] = True
    return mask, strict


def profile_bounds(cfg: GaugeConfig):
    p = np.asarray(cfg.profile)
    return float(p[:, 0].min()), float(p[:, 0].max()), float(p[:, 1].min()), float(p[:, 1].max())
