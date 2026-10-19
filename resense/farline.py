"""Far straight track axis for a long-range sensor (19.10, ``farrange``; off by default).

The track model (``resense/track.py``) is one parabola anchored at the sensor: its tangent comes
from the rails at 4-30 m and its curvature from the tunnel boundaries. On the Falcon recording the
track bends slightly in the first 40 m and is straight beyond; the parabola then leaves the track
by 2 m at 150 m and 15 m at 300 m (``docs/evidence/falcon_long_range_2026-10-19``), so nothing
beyond ~125 m is ever inside the corridor.

This module fits the far part on its own: per side, the inner tunnel boundary (structures 1.0-2.8 m
above the rail head, 1.2-4 m from a provisional line, never the gauge itself) per 5 m bin from
``axis_join`` outwards and a robust straight line through it. A side's *support* is contiguous: it
ends at the first gap longer than ``axis_max_gap`` between kept bins or at ``axis_max_rejected_run``
consecutive bins off the line (the start of a curve), and the bins of the last stretch must not lie
to one side of the line. The frame is accepted only when the supported line is long, straight
(residual, bow of a quadratic), consistent with a second side when one is seen, and joins the near
model without a kink (stricter with one side, where a diverging wall cannot be told from the track).
The far axis is the near axis' value at ``axis_join`` continued with the smoothed far slope, trusted
``axis_margin`` beyond the support (pessimistic: the support shrinks at once and grows slowly, and
decays while a failed frame is held), with a lateral uncertainty ``sigma(X)`` (offset, slope error,
the one-side divergence allowance, and an unseen curvature of R 300 m beyond the support) that shrinks
the strict gauge. Only an explicit ``declared_straight_to`` (a route-map statement) extends the
trust beyond the observed support. On a curve the checks fail and the near model is used as before.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from resense.config import FarRangeConfig
from resense.track import TrackModel


@dataclass
class FarAxis:
    """y_far(X) = y_join + slope (X - join) for join < X <= valid; the near model elsewhere."""
    join: float
    y_join: float
    slope: float
    slope_se: float
    support: float           # X of the last supporting bin (smoothed, pessimistic)
    valid: float             # X up to which the far line is trusted
    sides: int
    sigma0: float
    unseen_k: float
    one_side_slope: float = 0.0   # rad, divergence allowance with one fitted side
    straight_to: float = 0.0      # X from which an unseen curve may start (support minus the lead, or a declared map section)

    def offset(self, X: np.ndarray, model: TrackModel) -> np.ndarray:
        """y_far - y_near at X (0 before the join): dy_far = dy_near - offset."""
        X = np.asarray(X, dtype=np.float64)
        out = np.zeros(X.shape, dtype=np.float64)
        far = (X > self.join) & (X <= self.valid)      # only where the far line is trusted; the near model beyond
        if far.any():
            out[far] = self.y_join + self.slope * (X[far] - self.join) - model.center_y(X[far])
        return out

    def sigma(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        d = np.maximum(X - self.join, 0.0)
        beyond = np.maximum(X - self.straight_to, 0.0)
        stat = np.sqrt(self.sigma0 ** 2 + (self.slope_se * d) ** 2 + (self.one_side_slope * d) ** 2)
        return np.where((X > self.join) & (X <= self.valid), stat + 0.5 * self.unseen_k * beyond ** 2, 0.0)

    def to_dict(self) -> dict:
        return {"join": self.join, "y_join": round(self.y_join, 3), "slope": round(self.slope, 6),
                "slope_se": round(self.slope_se, 6), "support": round(self.support, 1),
                "valid": round(self.valid, 1), "sides": self.sides}


def _side_line(xs: np.ndarray, ys: np.ndarray, cfg: FarRangeConfig, min_bins: int):
    """Robust straight line of one boundary over its contiguous support:
    (slope, intercept, slope_se, x_support) or None."""
    if xs.size < min_bins:
        return None
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    keep = np.ones(xs.size, dtype=bool)
    for _ in range(3):
        if keep.sum() < min_bins:
            return None
        p = np.polyfit(xs[keep], ys[keep], 1)
        keep = np.abs(ys - np.polyval(p, xs)) < 2.0 * cfg.axis_max_rms
    # the support ends at a long gap between kept bins or at a run of rejected bins
    end, last, run = -1, None, 0
    for i in range(xs.size):
        if keep[i]:
            if last is not None and xs[i] - xs[last] > cfg.axis_max_gap:
                break
            last, run, end = i, 0, i
        else:
            run += 1
            if last is not None and run >= cfg.axis_max_rejected_run:
                break
    if end < 0:
        return None
    sup = keep.copy()
    sup[end + 1:] = False
    if sup.sum() < min_bins:
        return None
    x, y = xs[sup], ys[sup]
    if x.max() - x.min() < cfg.axis_min_span:
        return None
    p = np.polyfit(x, y, 1)
    res = y - np.polyval(p, x)
    rms = float(np.sqrt(np.mean(res ** 2)))
    if rms > cfg.axis_max_rms:
        return None
    if abs(float(np.mean(res[-3:]))) > cfg.axis_max_rms:        # the last stretch to one side: bending away
        return None
    q = np.polyfit(x, y, 2)
    grid = np.linspace(x.min(), x.max(), 32)
    if float(np.max(np.abs(np.polyval(q, grid) - np.polyval(p, grid)))) > cfg.axis_max_bow:
        return None
    sxx = float(np.sum((x - x.mean()) ** 2))
    se = rms / np.sqrt(max(sxx, 1e-9)) if x.size > 2 else 1.0
    return float(p[0]), float(p[1]), float(max(se, 1e-5)), float(x.max())


def measure(xyz: np.ndarray, model: TrackModel, cfg: FarRangeConfig, max_range: float):
    """This frame's far line: (slope, slope_se, support X, sides) or None."""
    X, Y, Z = xyz[:, 0].astype(np.float64), xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)
    j = cfg.axis_join
    lo, hi = cfg.axis_fit_range[0], min(cfg.axis_fit_range[1], max_range)
    sel = (X > lo) & (X < hi)
    if sel.sum() < 50:
        return None
    X, Y, Z = X[sel], Y[sel], Z[sel]
    yj = float(model.center_y(np.array([j]))[0])
    tj = float(np.tan(model.yaw) + model.curvature * j)
    dy0 = Y - (yj + tj * (X - j))
    h = Z - model.rail_z(X)
    band = ((h > cfg.axis_band[0]) & (h < cfg.axis_band[1]) & (np.abs(dy0) > cfg.axis_lateral[0])
            & (np.abs(dy0) < cfg.axis_lateral[1]))
    edges = np.arange(lo, hi + cfg.axis_bin, cfg.axis_bin)
    primary, second = [], []
    for s in (1.0, -1.0):
        m = band & (np.sign(dy0) == s)
        if m.sum() < cfg.axis_min_points * min(cfg.axis_min_bins, cfg.axis_second_min_bins):
            continue
        idx = np.digitize(X[m], edges) - 1
        a, yy = np.abs(dy0[m]), Y[m]
        xs, ys = [], []
        for b in np.unique(idx):
            q = np.flatnonzero(idx == b)
            if q.size < cfg.axis_min_points or b < 0 or b >= edges.size - 1:
                continue
            k = q[np.argsort(a[q])[int(0.1 * q.size)]]          # the inner boundary: 10th percentile of |lateral|
            xs.append(0.5 * (edges[b] + edges[b + 1]))
            ys.append(yy[k])
        xs, ys = np.asarray(xs), np.asarray(ys)
        f = _side_line(xs, ys, cfg, cfg.axis_min_bins)
        if f is not None:
            primary.append(f)
        else:
            f = _side_line(xs, ys, cfg, cfg.axis_second_min_bins)
            if f is not None:
                second.append(f)
    if not primary:
        return None
    fits = primary + second
    if len(fits) == 2 and abs(fits[0][0] - fits[1][0]) > cfg.axis_max_side_disagreement:
        return None
    w = np.array([1.0 / f[2] ** 2 for f in fits])
    slope = float(np.sum(w * [f[0] for f in fits]) / w.sum())
    se = float(1.0 / np.sqrt(w.sum()))
    kink = cfg.axis_max_kink if len(fits) == 2 else cfg.axis_max_kink_one_side
    if abs(slope - tj) > kink:
        return None
    return slope, se, max(f[3] for f in primary), len(fits)


class FarAxisTracker:
    """Temporal state of the far line (EMA of the slope, pessimistic support, confirmation, hold)."""

    def __init__(self, cfg: FarRangeConfig):
        self.cfg = cfg
        self.reset()

    def reset(self) -> None:
        self.slope: Optional[float] = None
        self.se = 1.0
        self.support = 0.0
        self.sides = 0
        self.good = 0
        self.bad = 0

    def update(self, xyz: np.ndarray, model: Optional[TrackModel], max_range: float) -> Optional[FarAxis]:
        cfg = self.cfg
        if model is None:
            self.reset()
            return None
        m = measure(xyz, model, cfg, max_range)
        if m is None:
            self.bad += 1
            # a held line is stale: its support decays (10 m per failed frame)
            self.support = max(cfg.axis_join, self.support - 10.0)
            if self.bad > cfg.axis_hold_frames:
                self.slope, self.good = None, 0
        else:
            slope, se, support, sides = m
            a = cfg.axis_smoothing if self.slope is not None else 0.0
            self.slope = slope if self.slope is None else a * self.slope + (1 - a) * slope
            self.se = se if a == 0.0 else a * self.se + (1 - a) * se
            if a == 0.0 or support < self.support:
                self.support = support                       # shrinks at once
            else:
                self.support = self.support + (1 - a) * (support - self.support)   # grows slowly
            self.sides = sides
            self.good += 1
            self.bad = 0
        if self.slope is None or self.good < cfg.axis_confirm_frames:
            return None
        j = cfg.axis_join
        k = float(cfg.axis_unseen_curvature)
        # a curve departs less than the keep tolerance (2 axis_max_rms) for sqrt(2 tol / k) after its start:
        # it may already have begun that far before the support's end
        lead = float(np.sqrt(2.0 * 2.0 * cfg.axis_max_rms / k)) if k > 0 else 0.0
        straight = max(self.support - lead, float(cfg.declared_straight_to), j)
        far = FarAxis(join=j, y_join=float(model.center_y(np.array([j]))[0]), slope=float(self.slope),
                      slope_se=float(self.se), support=float(self.support), valid=0.0, sides=self.sides,
                      sigma0=cfg.axis_sigma0, unseen_k=k,
                      one_side_slope=cfg.axis_one_side_slope_sigma if self.sides < 2 else 0.0,
                      straight_to=straight)
        # trusted to axis_margin beyond the support (or the declared section), and only while sigma <= axis_max_sigma
        end = min(max(self.support + cfg.axis_margin, float(cfg.declared_straight_to)), max_range)
        grid = np.arange(j, end + 1e-6, 1.0)
        far.valid = float(end)
        ok = far.sigma(grid) <= cfg.axis_max_sigma
        bad = np.flatnonzero(~ok)
        if bad.size:
            far.valid = float(grid[bad[0] - 1]) if bad[0] > 0 else j
        return far


class FarConfirm:
    """Far confirmation (19.10, ``farrange.confirm_*``): beyond ``confirm_from`` a strict-gauge track
    is reported as an obstacle only after ``confirm_min_hits`` matched frames within the last
    ``confirm_window`` whose distances lie on a straight line in time (rms <= ``confirm_max_residual``,
    |slope| <= ``confirm_max_step`` per frame): a static obstacle, a walking person or a train's
    approach at constant speed do; returns that hop along a ray do not (on the Falcon recording one
    azimuth column returns between 245 and 310 m on the same ray from frame to frame, per-ray range
    sd 9 m). Before that the track stays advisory (``far_unconfirmed``)."""

    def __init__(self, cfg: FarRangeConfig):
        self.cfg = cfg
        self.reset()

    def reset(self) -> None:
        self.n = 0
        self.hist: dict = {}

    def update(self, tracks) -> None:
        self.n += 1
        alive = set()
        for t in tracks:
            alive.add(t.id)
            if t.misses == 0 and t.last is not None:
                self.hist.setdefault(t.id, []).append((self.n, float(t.last.distance)))
                self.hist[t.id] = [h for h in self.hist[t.id] if h[0] > self.n - self.cfg.confirm_window]
        for k in [k for k in self.hist if k not in alive]:
            del self.hist[k]

    def ok(self, track_id: int) -> bool:
        cfg = self.cfg
        h = [x for x in self.hist.get(track_id, []) if x[0] > self.n - cfg.confirm_window]
        if len(h) < cfg.confirm_min_hits:
            return False
        f = np.array([x[0] for x in h], dtype=np.float64)
        d = np.array([x[1] for x in h], dtype=np.float64)
        p = np.polyfit(f, d, 1)
        rms = float(np.sqrt(np.mean((d - np.polyval(p, f)) ** 2)))
        return rms <= cfg.confirm_max_residual and abs(float(p[0])) <= cfg.confirm_max_step
