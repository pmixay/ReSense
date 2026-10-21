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
    lateral_to: float = 0.0       # X up to which the far line gives the laterals (>= valid: the whole trusted range)

    def offset(self, X: np.ndarray, model: TrackModel) -> np.ndarray:
        """y_far - y_near at X (0 before the join): dy_far = dy_near - offset."""
        X = np.asarray(X, dtype=np.float64)
        out = np.zeros(X.shape, dtype=np.float64)
        far = (X > self.join) & (X <= max(self.valid, self.lateral_to))   # the whole trusted range; the near model beyond
        if far.any():
            out[far] = self.y_join + self.slope * (X[far] - self.join) - model.center_y(X[far])
        return out

    def sigma(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        d = np.maximum(X - self.join, 0.0)
        beyond = np.maximum(X - self.straight_to, 0.0)
        stat = np.sqrt(self.sigma0 ** 2 + (self.slope_se * d) ** 2 + (self.one_side_slope * d) ** 2)
        return np.where((X > self.join) & (X <= max(self.valid, self.lateral_to)), stat + 0.5 * self.unseen_k * beyond ** 2, 0.0)

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


def _side_bins(xyz: np.ndarray, model: TrackModel, cfg: FarRangeConfig, max_range: float):
    """Per side (+1 left, -1 right) the inner-boundary bins (xs, ys), and the near tangent at the join;
    None when the frame has too few points."""
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
    sides = []
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
        sides.append((s, np.asarray(xs), np.asarray(ys)))
    return sides, tj


def measure(xyz: np.ndarray, model: TrackModel, cfg: FarRangeConfig, max_range: float):
    """This frame's far line: (slope, slope_se, support X, sides) or None."""
    bins = _side_bins(xyz, model, cfg, max_range)
    if bins is None:
        return None
    sides, tj = bins
    primary, second = [], []
    for s, xs, ys in sides:
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
    # the trust ends where the shorter side's support ends (review R1): beyond it the line is one-sided
    support = min(f[3] for f in fits) if len(fits) == 2 else primary[0][3]
    return slope, se, support, len(fits)


def _rejected_run_start(xs: np.ndarray, ys: np.ndarray, cfg: FarRangeConfig) -> float:
    """When a run of rejected bins ended a primary side's support (``_side_line``'s robust line and loop): the X of
    the last kept bin before it (a curve may start right after it); inf when the support ended at a gap or at the
    last bin: an observed contradiction vs missing data."""
    if xs.size < 2:
        return np.inf
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    keep = np.ones(xs.size, dtype=bool)
    for _ in range(3):
        if keep.sum() < 2:
            return np.inf
        p = np.polyfit(xs[keep], ys[keep], 1)
        keep = np.abs(ys - np.polyval(p, xs)) < 2.0 * cfg.axis_max_rms
    last, run = None, 0
    for i in range(xs.size):
        if keep[i]:
            if last is not None and xs[i] - xs[last] > cfg.axis_max_gap:
                return np.inf
            last, run = i, 0
        else:
            run += 1
            if last is not None and run >= cfg.axis_max_rejected_run:
                return float(xs[last])
    return np.inf


def _second_tube(xs: np.ndarray, ys: np.ndarray, line, cfg: FarRangeConfig):
    """21.10 (C7): a sparse second side (a column row) as a confirmation of the primary line ``line`` =
    (slope, intercept): its bins, from the near end outwards, must stay within T of one line *parallel* to
    the primary (offset = mean residual, rms about it <= ``axis_second_max_rms``). That bounds, at every
    observed bin, how far the two sides have diverged, without a slope estimate from a few noisy bins.
    Returns (support X or None, contradiction X): when an observed bin breaks the tube, the contradiction X is
    the last bin before it (a curve may start right after it); the support is contiguous (a gap longer than
    ``axis_max_gap`` ends it: missing data, not a contradiction); a side drifting away over its last bins is a
    contradiction before them."""
    T = cfg.axis_second_tube
    if xs.size < 2:
        return None, np.inf
    o = np.argsort(xs)
    xs, ys = xs[o], ys[o]
    r = ys - (line[1] + line[0] * xs)

    def fits(n):
        d = r[:n] - np.mean(r[:n])
        return float(np.max(np.abs(d))) < T and float(np.sqrt(np.mean(d ** 2))) <= cfg.axis_second_max_rms

    n = 1
    while n < xs.size and fits(n + 1):
        n += 1
    contra = float(xs[n - 1]) if n < xs.size else np.inf
    end = 0
    while end + 1 < n and xs[end + 1] - xs[end] <= cfg.axis_max_gap:
        end += 1
    x, d = xs[:end + 1], r[:end + 1] - np.mean(r[:end + 1])
    if x.size < cfg.axis_second_min_bins or x[-1] - x[0] < cfg.axis_min_span:
        return None, contra
    if abs(float(np.mean(d[-3:]))) > cfg.axis_second_max_rms:       # drifting away over the last bins
        return None, min(contra, float(x[-4]))
    return float(x[-1]), contra


def measure_stable(xyz: np.ndarray, model: TrackModel, cfg: FarRangeConfig, max_range: float):
    """21.10 (``axis_stable``): this frame's far line as a dict (slope, se, primary support, two-sided support or
    None, sides, contradiction X), or None when no primary side passes or the line kinks at the join."""
    bins = _side_bins(xyz, model, cfg, max_range)
    if bins is None:
        return None
    sides, tj = bins
    prim, rest = [], []
    for s, xs, ys in sides:
        f = _side_line(xs, ys, cfg, cfg.axis_min_bins)
        (prim if f is not None else rest).append((f, xs, ys))
    if not prim:
        return None
    contra = min(_rejected_run_start(xs, ys, cfg) for _, xs, ys in prim)
    T = cfg.axis_second_tube
    if len(prim) == 2:
        (f1, _, _), (f2, _, _) = prim
        w = np.array([1.0 / f1[2] ** 2, 1.0 / f2[2] ** 2])
        slope = float((w[0] * f1[0] + w[1] * f2[0]) / w.sum())
        se = float(1.0 / np.sqrt(w.sum()))
        two, n, ds = min(f1[3], f2[3]), 2, abs(f1[0] - f2[0])
        support = max(f1[3], f2[3])
    else:
        f1 = prim[0][0]
        slope, se, support, two, ds, n = f1[0], f1[2], f1[3], None, 0.0, 1
        if rest:
            _, xs, ys = rest[0]
            sup2, c2 = _second_tube(xs, ys, (f1[0], f1[1]), cfg)
            contra = min(contra, c2)
            if sup2 is not None:
                two, n = min(f1[3], sup2), 2                     # the tube bounds the divergence: no slope test
    # two fitted walls: they have diverged by T at join + T / |slope difference|; a property of this frame's
    # fit, not an observed location, so it caps this frame only (the contradictions are aged in the history)
    diverge = cfg.axis_join + T / ds if len(prim) == 2 and ds > 0 else np.inf
    if abs(slope - tj) > (cfg.axis_max_kink if n == 2 else cfg.axis_max_kink_one_side):
        return None
    return {"slope": slope, "se": se, "support": support, "two": two, "sides": n, "contra": contra, "diverge": diverge}


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
        self.t = 0.0                    # s, elapsed (axis_stable)
        self.hist: list = []            # (t, two-sided support or None, contradiction X) of the last frames (axis_stable)
        self.last_used: Optional[float] = None

    def update(self, xyz: np.ndarray, model: Optional[TrackModel], max_range: float,
               dt: Optional[float] = None) -> Optional[FarAxis]:
        cfg = self.cfg
        if cfg.axis_stable:
            return self._update_stable(xyz, model, max_range, dt)
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
        # trusted to axis_margin beyond the support (or the declared section), and only while sigma <= axis_max_sigma;
        # with one side a straight wall cannot tell a track curving away from it (review R1): no further than
        # the near model's own trusted range unless a straight section is declared
        end = min(max(self.support + cfg.axis_margin, float(cfg.declared_straight_to)), max_range)
        if self.sides < 2 and cfg.declared_straight_to <= 0:
            end = min(end, max(float(model.axis_valid), j))
        grid = np.arange(j, end + 1e-6, 1.0)
        far.valid = float(end)
        ok = far.sigma(grid) <= cfg.axis_max_sigma
        bad = np.flatnonzero(~ok)
        if bad.size:
            far.valid = float(grid[bad[0] - 1]) if bad[0] > 0 else j
        return far


    def _update_stable(self, xyz, model, max_range, dt) -> Optional[FarAxis]:
        """21.10 (C7-C9): the support is the farthest of the last frames' two-sided supports that at least two
        frames reach and more frames reach than contradict below it, every value aged by ``axis_history_speed``
        x the elapsed time; capped by this frame's contradiction and this frame's divergence of two fitted
        walls; no two-sided support, no far
        axis (unless a straight section is declared). A frame failing the line tests keeps the existing hold."""
        cfg = self.cfg
        if model is None:
            self.reset()
            return None
        self.t += float(dt) if dt is not None and dt > 0 else cfg.axis_frame_dt
        m = measure_stable(xyz, model, cfg, max_range)
        if m is None:
            self.bad += 1
            if self.bad > cfg.axis_hold_frames:
                self.slope, self.good, self.hist = None, 0, []
        else:
            a = cfg.axis_smoothing if self.slope is not None else 0.0
            self.slope = m["slope"] if self.slope is None else a * self.slope + (1 - a) * m["slope"]
            self.se = m["se"] if a == 0.0 else a * self.se + (1 - a) * m["se"]
            self.support = m["support"]
            self.good += 1
            self.bad = 0
            self.hist.append((self.t, m["two"], m["contra"]))
        diverge = m["diverge"] if m is not None else np.inf
        self.hist = [h for h in self.hist if h[0] > self.t - cfg.axis_history_frames * cfg.axis_frame_dt - 1e-9][-cfg.axis_history_frames:]
        if self.slope is None or self.good < cfg.axis_confirm_frames:
            return None
        v, j = cfg.axis_history_speed, cfg.axis_join
        need = max(cfg.axis_history_min, 1)
        conf = sorted((two - v * (self.t - t) for t, two, _ in self.hist if two is not None), reverse=True)
        contra = [c - v * (self.t - t) for t, _, c in self.hist if np.isfinite(c)]
        used, sides = None, 2
        # the farthest level that at least `need` frames support and more frames support than contradict
        # (a contradiction below it), every value aged; this frame's contradiction caps at once
        for k in range(need - 1, len(conf)):
            if sum(c < conf[k] for c in contra) < k + 1:
                used = conf[k]
                break
        if used is not None:
            now = [m["contra"]] if m is not None and np.isfinite(m["contra"]) else []
            used = min([used, diverge] + now) - 10.0 * self.bad     # a held line decays as before (10 m per failed frame)
        if used is None or used <= j:
            if cfg.declared_straight_to <= 0:
                self.last_used = None
                return None
            used, sides = self.support - 10.0 * self.bad, 1     # a declared section: the 19.10 one-sided path
        self.last_used = used
        self.sides = sides
        k = float(cfg.axis_unseen_curvature)
        tol = max(2.0 * cfg.axis_max_rms, cfg.axis_second_tube if sides == 2 else 0.0)
        lead = float(np.sqrt(2.0 * tol / k)) if k > 0 else 0.0
        straight = max(used - lead, float(cfg.declared_straight_to), j)
        far = FarAxis(join=j, y_join=float(model.center_y(np.array([j]))[0]), slope=float(self.slope),
                      slope_se=float(self.se), support=float(used), valid=0.0, sides=sides,
                      sigma0=cfg.axis_sigma0, unseen_k=k,
                      one_side_slope=cfg.axis_one_side_slope_sigma if sides < 2 else 0.0, straight_to=straight)
        end = min(max(used + cfg.axis_margin, float(cfg.declared_straight_to)), max_range)
        grid = np.arange(j, end + 1e-6, 1.0)
        far.valid = float(end)
        bad = np.flatnonzero(far.sigma(grid) > cfg.axis_max_sigma)
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
