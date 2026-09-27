"""Persistent sparse envelope evidence for the monitored-range estimate (27.09, P3 range overclaim).

A small object far ahead (the 0.3 m cube of set O at 60-130 m) leaves two to four returns inside
the envelope: below every cluster size bar, so no candidate, no track and no cap on
``clear_distance`` - the estimate claimed 120-140 m of clear track past it. Single-frame caps on
such returns (M1, ``health.clear_cap_points``) cost 15-50 % of the empty recordings' range: the
far corridor holds returns of the same size everywhere (floor and ceiling rows, the tunnel wall
where the extrapolated corridor meets a curve).

:class:`PersistentEvidence` keeps, per frame, the *sparse blobs* of the returns inside the nominal
envelope polygon (the rail-referenced envelope without the lateral edge margin, low candidates
excluded): connected groups of returns (link ``LINK`` m at range 0, grown by ``1 + X / 100``) that
are compact (at most ``persist_max_extent`` along the track and across and up, or one scan line up
to the envelope's width), hold at least ``persist_min_points`` returns and are isolated (at most
``persist_max_around`` other corridor returns within 2 m along the track). A blob is chained to a
blob of the previous frame at the same lateral offset and height (``persist_tol_dy``,
``persist_tol_h``) that lies farther by a shift in ``persist_shift`` m per frame (a static object
approaching at the train's apparent motion), and the chain holds only while the shift stays within
``persist_tol_shift`` of the previous link's (constant apparent velocity). A blob at the end of a
chain of ``health.clear_cap_persist`` frames caps the estimate at its nearest return.

Nothing here changes a detection, a track or the decision. Evidence that never forms such a chain
(an object seen in fewer frames, one moving across the track, a train standing still) is not
represented, and objects can be missed beyond the cap as before.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from resense.gauge import point_in_polygon

LINK = 0.45          # m, blob link distance at range 0 (x (1 + X / 100))
AROUND = 2.0         # m along the track either side of a blob in which other corridor returns count


def sparse_blobs(X: np.ndarray, dy: np.ndarray, h: np.ndarray, ev: np.ndarray, hcfg) -> np.ndarray:
    """Compact, isolated blobs of the evidence returns ``ev`` (bool mask over the corridor
    returns ``X, dy, h``). Returns an (n, 4) array: nearest X, mean dy, mid height, returns."""
    out = np.zeros((0, 4))
    idx = np.flatnonzero(ev)
    if idx.size < max(1, int(hcfg.persist_min_points)):
        return out
    A = int(hcfg.persist_max_around)
    Xs = np.sort(X)
    Xe = X[idx]
    Xes = np.sort(Xe)
    # isolation first, per return: a compact blob (x0 <= X_p <= x1 <= x0 + extent) around a return
    # has at least C(X_p +- (2 - extent)) - E(X_p +- extent) other corridor returns within 2 m (C: all
    # corridor returns, E: evidence returns), so a return where that exceeds A is dropped before the
    # linking; crowded stretches (a wall in the corridor, a platform) cost nothing. Blobs are formed
    # from the remaining returns and tested on all corridor returns
    ext = float(hcfg.persist_max_extent)
    c = np.searchsorted(Xs, Xe + AROUND - ext, "right") - np.searchsorted(Xs, Xe - AROUND + ext, "left")
    e = np.searchsorted(Xes, Xe + ext, "right") - np.searchsorted(Xes, Xe - ext, "left")
    keep = c - e <= A
    idx = idx[keep]
    n = idx.size
    if n < max(1, int(hcfg.persist_min_points)):
        return out
    Q = np.stack([X[idx], dy[idx], h[idx]], axis=1).astype(np.float64)
    if n > 1:
        pairs = cKDTree(Q).query_pairs(r=LINK * (1.0 + max(float(Q[:, 0].max()), 0.0) / 100.0),
                                       output_type="ndarray")
        if pairs.size:
            d = np.linalg.norm(Q[pairs[:, 0]] - Q[pairs[:, 1]], axis=1)
            pairs = pairs[d <= LINK * (1.0 + np.minimum(Q[pairs[:, 0], 0], Q[pairs[:, 1], 0]) / 100.0)]
        adj = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
        nc, lab = connected_components(adj, directed=False)
    else:
        nc, lab = 1, np.zeros(1, dtype=int)
    order = np.argsort(lab, kind="stable")
    cnt = np.bincount(lab, minlength=nc)
    starts = np.concatenate([[0], np.cumsum(cnt)[:-1]])
    S = Q[order]
    x0 = np.minimum.reduceat(S[:, 0], starts)
    x1 = np.maximum.reduceat(S[:, 0], starts)
    dy0 = np.minimum.reduceat(S[:, 1], starts)
    dy1 = np.maximum.reduceat(S[:, 1], starts)
    h0 = np.minimum.reduceat(S[:, 2], starts)
    h1 = np.maximum.reduceat(S[:, 2], starts)
    dym = np.add.reduceat(S[:, 1], starts) / cnt
    edy, eh = dy1 - dy0, h1 - h0
    around = np.searchsorted(Xs, x1 + AROUND, "right") - np.searchsorted(Xs, x0 - AROUND, "left") - cnt
    ok = ((cnt >= hcfg.persist_min_points) & (x1 - x0 <= ext) & (around <= A)
          & (((edy <= ext) & (eh <= ext)) | ((eh <= hcfg.persist_row_height) & (edy <= hcfg.persist_row_width))))
    return np.stack([x0[ok], dym[ok], 0.5 * (h0[ok] + h1[ok]), cnt[ok].astype(np.float64)], axis=1)


class PersistentEvidence:
    """Chains of sparse envelope blobs across frames (module docstring); ``update`` returns the
    cap (m) of this frame or None."""

    def __init__(self, hcfg, gauge_cfg):
        self.hcfg = hcfg
        self.profile = gauge_cfg.profile
        self.range_min = float(gauge_cfg.range_min)
        self.reset()

    def reset(self) -> None:
        self._prev: Optional[np.ndarray] = None       # (n, 6): x0, dy, h, returns, depth, shift

    def update(self, X: np.ndarray, dy: np.ndarray, h: np.ndarray, low: Optional[np.ndarray]) -> Optional[float]:
        cfg = self.hcfg
        k = int(cfg.clear_cap_persist)
        X = np.asarray(X, dtype=np.float64)
        ok = np.ones(X.size, dtype=bool) if low is None else ~np.asarray(low, dtype=bool)
        X, dy, h = X[ok], np.asarray(dy, dtype=np.float64)[ok], np.asarray(h, dtype=np.float64)[ok]
        ev = (X >= self.range_min) & point_in_polygon(dy, h, self.profile) if X.size else np.zeros(0, dtype=bool)
        B = sparse_blobs(X, dy, h, ev, cfg)
        n = B.shape[0]
        depth = np.ones(n)
        shift = np.full(n, np.nan)
        P = self._prev
        if n and P is not None and P.shape[0]:
            lo, hi = cfg.persist_shift
            dX = P[None, :, 0] - B[:, None, 0]
            match = ((np.abs(P[None, :, 1] - B[:, None, 1]) <= cfg.persist_tol_dy)
                     & (np.abs(P[None, :, 2] - B[:, None, 2]) <= cfg.persist_tol_h)
                     & (dX >= lo) & (dX <= hi))
            match &= np.isnan(P[None, :, 5]) | (np.abs(P[None, :, 5] - dX) <= cfg.persist_tol_shift)
            for a in np.flatnonzero(match.any(axis=1)):
                js = np.flatnonzero(match[a])
                j = js[np.argmax(P[js, 4])]
                depth[a] = P[j, 4] + 1.0
                shift[a] = dX[a, j]
        self._prev = np.concatenate([B, depth[:, None], shift[:, None]], axis=1)
        m = depth >= k
        return float(B[m, 0].min()) if m.any() else None
