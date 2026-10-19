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


class DustGuard:
    """Per-detector state of the diffuse-return guard (hysteresis)."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.active = False
        self._quiet = 0
        self.last: Optional[dict] = None
        self._tree = None
        self._roi_idx = None

    def reset(self) -> None:
        self.active = False
        self._quiet = 0
        self.last = None
        self._tree = None
        self._roi_idx = None

    def _neighbours(self, xyz: np.ndarray, idx: np.ndarray) -> np.ndarray:
        """Distinct other returns within r(R) of each queried frame point."""
        P = xyz[idx].astype(np.float64)
        rng = np.linalg.norm(P, axis=1)
        counts = self._tree.query_ball_point(P, support_radius(rng, self.cfg), return_length=True)
        return np.asarray(counts, dtype=np.int64) - 1          # the query point itself

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
        n_iso = 0
        if interior.size >= cfg.on_density * volume or self.active:
            self._build(xyz, dy, h)
            n_iso = int((self._neighbours(xyz, interior) == 0).sum()) if interior.size else 0
        density = n_iso / volume
        if density >= cfg.on_density:
            self.active, self._quiet = True, 0
        elif self.active:
            self._quiet = self._quiet + 1 if density < cfg.off_density else 0
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
                     "field_density": round(rho, 4), "quiet_frames": self._quiet}
        return self.last

    def _build(self, xyz, dy, h):
        cfg = self.cfg
        roi = np.flatnonzero((np.abs(dy) <= cfg.roi_half_width) & (h >= cfg.roi_height[0])
                             & (h <= cfg.roi_height[1]) & (xyz[:, 0] > 0))
        P = xyz[roi].astype(np.float64)
        # distinct returns: coincident echoes (dual return, duplicated points) are one ray hit
        _, first = np.unique(np.round(P / cfg.dedup).astype(np.int64), axis=0, return_index=True)
        self._tree = cKDTree(P[np.sort(first)])
        self._roi_idx = roi

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
        keep[cur] = counts >= required_support(lam, self.cfg)
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
