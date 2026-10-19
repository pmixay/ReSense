"""N3 diffuse-return guard (``dust.enabled``, off by default): degraded-visibility health and
local-support qualification of obstacle candidates while volumetric clutter is observed.

Physical basis (synthetic-model results only; no physical dust recording exists): returns from
airborne particles are volumetric and uncorrelated in space, while returns from a solid surface,
a cable or an edge come in rows and columns of neighbouring rays. A return of a solid object at
range R therefore has other returns within a few beam spacings (``r(R) = support_radius +
R * support_radius_per_m``); a diffuse return mostly has none.

The guard has two parts, both inactive on frames without the diffuse signal:

1. Assessment, every frame: the returns inside the empty gauge interior (``interior_*``, where a
   clean tunnel has nothing but the occasional object) that have no neighbour within ``r(R)``
   are counted. Their density per cubic metre is the diffuse signal; a solid object or a wall in
   the interior contributes supported returns only. Hysteresis: on at ``on_density``, off below
   ``off_density`` after ``hold_frames`` frames.
2. While active: (a) health reports degraded visibility (warn: CAUTION; never lowers an error),
   monitored and clear range 0; (b) a corridor / low-object candidate return is kept for
   clustering only if it has at least ``k(R)`` neighbours, where ``k(R)`` is the smallest count
   (at least ``min_support``) that a diffuse field of the measured density reaches by chance with
   probability at most ``false_support``. No frame point is deleted: the track model, bed model,
   calibration, ego speed and health see the whole cloud. Unsupported returns cannot start or
   feed a STOP; the degraded health keeps the node at CAUTION while they are present.

No intensity threshold is used (a dark real object must not be removed by a dust rule, and a
new sensor's intensity scale is not assumed). The guard never promotes GO.
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

import numpy as np
from scipy.spatial import cKDTree


def support_radius(rng: np.ndarray, cfg) -> np.ndarray:
    return cfg.support_radius + np.asarray(rng, dtype=np.float64) * cfg.support_radius_per_m


def required_support(lam: np.ndarray, cfg) -> np.ndarray:
    """Smallest k >= min_support with P(Poisson(lam) >= k) <= false_support (vectorised)."""
    lam = np.asarray(lam, dtype=np.float64)
    kmin, kmax = int(cfg.min_support), int(cfg.max_support)
    k = np.full(lam.shape, kmax, dtype=np.int64)
    term = np.exp(-lam)                 # P(N = 0)
    cdf = np.zeros_like(lam)            # P(N < j)
    for j in range(kmax + 1):
        if j >= kmin:
            k = np.where((k == kmax) & (1.0 - cdf <= cfg.false_support), np.minimum(k, j), k)
        cdf = cdf + term
        term = term * lam / (j + 1)
    return k


def count_within(tree, P: np.ndarray, r: np.ndarray, cap: int) -> np.ndarray:
    """min(tree points within r of each query point, cap): a capped nearest-neighbour query, so
    dense surfaces cost O(cap) per point instead of all their neighbours."""
    if not len(P):
        return np.zeros(0, dtype=np.int64)
    d, _ = tree.query(P, k=int(cap), distance_upper_bound=float(np.max(r)) * (1 + 1e-9) + 1e-12)
    d = d.reshape(len(P), -1)
    return (d <= r[:, None]).sum(axis=1).astype(np.int64)


class DustGuard:
    """Per-detector state of the diffuse-return guard (hysteresis)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.active = False
        self._quiet = 0
        self.last: Optional[dict] = None
        self._tree = None
        self._roi_idx = None
        self._window = deque(maxlen=max(1, int(cfg.light_window)))
        self.light = False

    def reset(self) -> None:
        self.active = False
        self._quiet = 0
        self.last = None
        self._tree = None
        self._roi_idx = None
        self._window.clear()
        self.light = False

    def _neighbours(self, xyz: np.ndarray, idx: np.ndarray, cap: Optional[int] = None) -> np.ndarray:
        """Distinct other returns within r(R) of each queried frame point, capped at ``cap``
        (default max_support)."""
        P = xyz[idx].astype(np.float64)
        rng = np.linalg.norm(P, axis=1)
        cap = int(self.cfg.max_support) if cap is None else int(cap)
        return count_within(self._tree, P, support_radius(rng, self.cfg), cap + 1) - 1   # minus the point itself

    def assess(self, xyz: np.ndarray, dy: np.ndarray, h: np.ndarray) -> dict:
        """Measure the diffuse signal of this frame and update the hysteresis state."""
        cfg = self.cfg
        self._tree = None
        x = xyz[:, 0]
        x0, x1 = cfg.interior_range
        h0, h1 = cfg.interior_height
        interior = np.flatnonzero((x >= x0) & (x < x1) & (np.abs(dy) <= cfg.interior_half_width)
                                  & (h >= h0) & (h < h1))
        volume = (x1 - x0) * 2.0 * cfg.interior_half_width * (h1 - h0)
        n_iso, spread = 0, 0.0
        low_bar = min(cfg.on_density, cfg.light_density) if cfg.light_spread > 0 else cfg.on_density
        if interior.size >= low_bar * volume or self.active:
            self._build(xyz, dy, h)
            iso = interior[self._neighbours(xyz, interior, cap=1) == 0] if interior.size else interior
            n_iso = int(iso.size)
            # A diffuse field fills the whole interior; isolated returns of real clutter (a thinly
            # sampled structure, an edge) stay where that structure is.
            nx = max(1, int(round((x1 - x0) / cfg.cell[0])))
            ny = max(1, int(round(2.0 * cfg.interior_half_width / cfg.cell[1])))
            nz = max(1, int(round((h1 - h0) / cfg.cell[2])))
            if n_iso:
                cx = np.clip(((x[iso] - x0) / cfg.cell[0]).astype(np.int64), 0, nx - 1)
                cy = np.clip(((dy[iso] + cfg.interior_half_width) / cfg.cell[1]).astype(np.int64), 0, ny - 1)
                cz = np.clip(((h[iso] - h0) / cfg.cell[2]).astype(np.int64), 0, nz - 1)
                spread = np.unique((cx * ny + cy) * nz + cz).size / float(nx * ny * nz)
        density = n_iso / volume
        if density >= cfg.on_density and spread >= cfg.on_spread:
            self.active, self._quiet = True, 0
        elif self.active:
            low = density < cfg.off_density or spread < cfg.off_spread
            self._quiet = self._quiet + 1 if low else 0
            if self._quiet > cfg.hold_frames:
                self.active, self._quiet = False, 0
        # Density of the field for the chance-support threshold: isolated returns underestimate a
        # dense field (some diffuse returns do have a neighbour); correct with the Poisson share
        # of isolated returns at the interior's mean radius, bounded.
        r_mid = float(support_radius(0.5 * (x0 + x1), cfg))
        v_mid = 4.0 / 3.0 * math.pi * r_mid ** 3
        rho = density
        for _ in range(8):
            rho = min(density * math.exp(min(rho * v_mid, 3.0)), cfg.max_density)
        self.last = {"active": self.active, "interior_returns": int(interior.size),
                     "isolated_returns": n_iso, "isolated_density": round(density, 4),
                     "isolated_spread": round(spread, 4),
                     "field_density": round(rho, 4), "quiet_frames": self._quiet}
        # Light diffuse returns (below the degraded-visibility level) still move the far track
        # model; a sustained, spread signal over light_window frames lets only the track filter run.
        self._window.append((density, spread))
        if cfg.light_spread > 0 and len(self._window) == self._window.maxlen:
            d, sp = np.mean(np.asarray(self._window), axis=0)
            self.light = bool(d >= cfg.light_density and sp >= cfg.light_spread)
        else:
            self.light = False
        self.last["light"] = self.light
        return self.last

    def _build(self, xyz, dy, h):
        cfg = self.cfg
        roi = np.flatnonzero((np.abs(dy) <= cfg.roi_half_width) & (h >= cfg.roi_height[0])
                             & (h <= cfg.roi_height[1]) & (xyz[:, 0] > 0))
        P = xyz[roi].astype(np.float64)
        # distinct returns: coincident echoes (dual return, duplicated points) are one ray hit
        q = np.round(P / cfg.dedup).astype(np.int64)
        q -= q.min(axis=0) if len(q) else 0
        span = q.max(axis=0) + 1 if len(q) else np.ones(3, dtype=np.int64)
        _, first = np.unique((q[:, 0] * span[1] + q[:, 1]) * span[2] + q[:, 2], return_index=True)
        self._tree = cKDTree(P[np.sort(first)])
        self._roi_idx = roi

    def track_input(self, xyz: np.ndarray, prev_track) -> np.ndarray:
        """Keep-mask of the frame for the track model while active (the previous frame's state
        and model): unsupported returns near the track (the volume a diffuse field fills) are
        withheld from the bed / rail / axis fits only; everything else is kept."""
        from resense.gauge import corridor_coordinates
        cfg = self.cfg
        keep = np.ones(len(xyz), dtype=bool)
        if not (self.active or self.light) or prev_track is None or self.last is None or not len(xyz):
            return keep
        dy, h = corridor_coordinates(xyz, prev_track)
        x = xyz[:, 0]
        roi = np.flatnonzero((x > 0) & (x < cfg.interior_range[1] + cfg.track_margin)
                             & (np.abs(dy) <= cfg.roi_half_width)
                             & (h >= cfg.track_min_height) & (h <= cfg.roi_height[1]))
        if not roi.size:
            return keep
        # Supporters come from the whole near-track volume (bed and rails included); only returns
        # above the rail-head band are candidates for withholding: far rail and bed returns are
        # single grazing hits per scan line and must stay in the fit.
        sup = np.flatnonzero((x > 0) & (x < cfg.interior_range[1] + cfg.track_margin + 1.0)
                             & (np.abs(dy) <= cfg.roi_half_width + 0.5)
                             & (h >= cfg.roi_height[0]) & (h <= cfg.roi_height[1] + 0.5))
        S = xyz[sup].astype(np.float64)
        q = np.round(S / cfg.dedup).astype(np.int64)
        q -= q.min(axis=0)
        span = q.max(axis=0) + 1
        _, first = np.unique((q[:, 0] * span[1] + q[:, 1]) * span[2] + q[:, 2], return_index=True)
        tree = cKDTree(S[np.sort(first)])
        P = xyz[roi].astype(np.float64)
        rng = np.linalg.norm(P, axis=1)
        r = support_radius(rng, cfg)
        counts = count_within(tree, P, r, int(cfg.max_support) + 1) - 1
        lam = self.last["field_density"] * 4.0 / 3.0 * math.pi * r ** 3
        lam = np.where(P[:, 0] > cfg.interior_range[1], 0.0, lam)
        keep[roi] = counts >= required_support(lam, cfg)
        return keep

    def supported(self, xyz: np.ndarray, idx: np.ndarray, dy: np.ndarray, h: np.ndarray) -> np.ndarray:
        """Boolean per queried frame index: enough local support to be obstacle evidence while
        active; all True when inactive. Indices < 0 (accumulated returns) are kept."""
        idx = np.asarray(idx, dtype=np.int64)
        keep = np.ones(idx.size, dtype=bool)
        if not self.active or idx.size == 0:
            return keep
        if self._tree is None:
            self._build(xyz, dy, h)
        cur = idx >= 0
        if not cur.any():
            return keep
        q = idx[cur]
        counts = self._neighbours(xyz, q)
        rng = np.linalg.norm(xyz[q].astype(np.float64), axis=1)
        lam = self.last["field_density"] * 4.0 / 3.0 * math.pi * support_radius(rng, self.cfg) ** 3
        # The field is measured inside the interior only; beyond it the base requirement applies
        # (a far, sparsely sampled real object must stay detectable where no field was observed).
        lam = np.where(xyz[q, 0] > self.cfg.interior_range[1], 0.0, lam)
        solid = counts >= required_support(lam, self.cfg)
        loose = np.flatnonzero(~solid)
        if loose.size and solid.any() and self.cfg.attach_factor > 0:
            # The fringe of a real structure (a thinly sampled edge, a sparse row next to a
            # surface) stays with it: an unsupported return within attach_factor * r(R) of a
            # supported candidate return is kept. Only returns away from all solid evidence go.
            near = cKDTree(xyz[q[solid]].astype(np.float64))
            dist, _ = near.query(xyz[q[loose]].astype(np.float64), k=1)
            solid[loose[dist <= self.cfg.attach_factor * support_radius(rng[loose], self.cfg)]] = True
        keep[cur] = solid
        return keep


def degraded_health(health: dict, stats: dict, removed: int) -> dict:
    """Retain severity and STOP evidence; decline monitored / clear range claims."""
    out = dict(health)
    out["level"] = "error" if out.get("level") == "error" else "warn"
    out["decision_level"] = "error" if out.get("decision_level") == "error" else "warn"
    out["messages"] = list(out.get("messages", [])) + [
        "diffuse volumetric returns (dust / suspension): visibility degraded, range unverified; "
        f"{removed} unsupported candidate returns kept out of obstacle evidence"]
    out["monitored_range"] = out["clear_distance"] = 0.0
    out["dust_guard"] = {**stats, "unsupported_candidate_returns": int(removed)}
    return out
