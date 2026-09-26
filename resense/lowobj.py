"""Low foreign objects on the track (v0.6): bumps above the learned track-bed cross-section.

The organizers' size criterion is an object of 300 x 300 x 100 mm (Q&A session, 2026-09;
docs/organizers/QA_session.md). Lying on the bed between the rails such an object stays
below the rail head, i.e. below the bottom of any clearance-gauge polygon, and it is lower
than the rail fastenings and cable ducts the corridor stage has to ignore, so the ordinary
pipeline cannot see it by construction. It is, however, an *anomaly of the bed*: the
cross-section of a metro track (rails, fastenings, the concrete bed, the drainage trough)
is the same every metre, so

1. the **template** ``h_bed(dy)`` - the height above the rail head of the bed surface at
   lateral offset ``dy`` - is learned every frame from the dense near range (4-30 m) as a
   low percentile per 2.5 cm lateral bin, dilated by +-5 cm (the rail heads and their flanks
   belong to the template, not to the anomalies), and smoothed over frames;
2. at every along-track bin (2 m) the **local offset** of the bed returns from the template
   (the height reference drifts by centimetres with range) is the median residual of the
   points that look like bed (residual within -0.15 ... +0.05 m);
3. a point in the train's envelope (``|dy| <= half_width``) below the gauge polygon bottom
   whose residual exceeds ``min_excess`` is a **low candidate**; the candidates go to the
   clusterer with the corridor candidates (flagged, so that the low-hardware rule does not
   drop them) and a cluster made of them must be short along the track (rails, guard rails
   and cables are long), at least ``min_width`` wide, have ``min_points`` voxels and **reach
   the rail-head plane** (its highest point at least ``min_top`` above the rail head): the bed
   carries fixtures of the same size that stay below the rail head by design.

4. (v0.6.2) **objects straddling the envelope floor**: an object lying across a rail can have
   most of its points below the rail head and only its top above the envelope floor (the
   organizers' object in ``doubleT_obstacle``: ~21 points at 56 m, ~16 of them below the rail
   head, ~3 above the 0.12 m floor, top 0.10-0.15 m above the rail head). The rule of step 3 that
   every candidate be ``min_point_top`` above the rail head (it keeps the rail fittings out)
   leaves it two points. ``low_candidates`` therefore also returns every bed anomaly without that
   rule; the detector clusters them together with the corridor points just above the floor and
   reports such a cluster only when its top reaches ``straddle_min_top`` (0.10 m) above the rail
   head - above the 1-8 cm the rail fittings reach (EXPERIMENTS.md §1d) - and it is at least
   ``straddle_min_width`` (0.35 m) wide across the track and at most ``straddle_max_length``
   (0.8 m) long along it: the trackside devices beside the rails (train stops, lubricators,
   signalling) reach 0.2-0.35 m but are mounted along the rail, 0.2-0.3 m across and 0.5-1.4 m
   long; without this shape rule the path added 49 false events on the 20-minute ride.

5. An opt-in central near-bed path accepts a compact, sufficiently raised anomaly below
   the rail head only within 30 m, inside the rail pair, with local bed support and current
   rail lock. Disabled by default pending real-ride false-positive evaluation. The
   point-wise rail-head rule and the straddle thresholds stay unchanged.

Where the bed is not observed (beyond ~50-80 m, grazing incidence) there is no local
offset and nothing is reported: the stage's range is where the bed is seen. Puddles in the
trough return nothing or mirror images *below* the bed (negative residuals): they are
ignored by construction.
"""
from __future__ import annotations

from typing import Optional

import numpy as np

from resense import _native
from resense.config import LowObjectConfig
from resense.track import bin_percentile


class BedTemplate:
    """The learned cross-section h_bed(dy) (smoothed across frames)."""

    def __init__(self, cfg: LowObjectConfig):
        self.cfg = cfg
        half = cfg.half_width + 0.15
        self.edges = np.arange(-half, half + cfg.template_bin, cfg.template_bin)
        self.centres = 0.5 * (self.edges[:-1] + self.edges[1:])
        self.prof: Optional[np.ndarray] = None

    def reset(self) -> None:
        self.prof = None

    def update(self, X: np.ndarray, dy: np.ndarray, h: np.ndarray) -> Optional[np.ndarray]:
        cfg = self.cfg
        x0, x1 = cfg.template_range
        sel = _native.select(X.size, (dy, ">", self.edges[0], "<", self.edges[-1]), (h, ">", -1.2, "<", 0.4),
                             (X, ">", x0, "<", x1))       # np.flatnonzero of the mask below; None: numpy
        if sel is None:
            sel = (X > x0) & (X < x1) & (dy > self.edges[0]) & (dy < self.edges[-1]) & (h > -1.2) & (h < 0.4)
        n_sel = int(sel.sum()) if sel.dtype == bool else sel.size
        if n_sel < 200:
            return self.prof
        nb = self.edges.size - 1
        b = np.clip(np.digitize(dy[sel], self.edges) - 1, 0, nb - 1)
        prof, _ = bin_percentile(h[sel].astype(np.float64), b, nb, cfg.template_percentile, cfg.template_min_points)
        ok = np.isfinite(prof)
        if ok.sum() < nb // 3:
            return self.prof
        prof = np.interp(self.centres, self.centres[ok], prof[ok])
        k = max(0, int(round(cfg.template_dilate / cfg.template_bin)))
        if k:
            pad = np.pad(prof, k, mode="edge")
            prof = np.max(np.stack([pad[i:i + nb] for i in range(2 * k + 1)]), axis=0)
        if self.prof is None:
            self.prof = prof
        else:
            a = cfg.template_smoothing
            self.prof = a * self.prof + (1.0 - a) * prof
        return self.prof

    def __call__(self, dy: np.ndarray) -> np.ndarray:
        return np.interp(dy, self.centres, self.prof)


def low_candidates(X: np.ndarray, dy: np.ndarray, h: np.ndarray, template: BedTemplate,
                   cfg: LowObjectConfig, range_min: float, x_limit: float,
                   h_bottom: float, with_all: bool = False, with_near: bool = False):
    """(indices of low candidates, range up to which the bed was observed); with ``with_all``
    also the indices of every bed anomaly before the ``min_point_top`` rule (step 4).
    ``with_near`` adds dense-bed, central near-range anomalies independently of that rule."""
    empty = np.zeros(0, dtype=np.int64)

    def result(kept, seen_range, all_idx=empty, near_idx=empty):
        return ((kept, seen_range, all_idx, near_idx) if with_near else
                (kept, seen_range, all_idx) if with_all else (kept, seen_range))

    if template.prof is None:
        return result(empty, 0.0)
    x1 = min(cfg.range_max, x_limit)
    idx = _native.select(X.size, (dy, None, None, "<=", cfg.half_width, True), (h, ">", -1.2, "<", h_bottom),
                         (X, ">=", range_min, "<", x1))
    if idx is None:
        band = (X >= range_min) & (X < x1) & (np.abs(dy) <= cfg.half_width) & (h < h_bottom) & (h > -1.2)
        idx = np.flatnonzero(band)
    if idx.size == 0:
        return result(idx, 0.0)
    res = h[idx] - template(dy[idx])
    edges = np.arange(range_min, x1 + cfg.local_bin, cfg.local_bin)
    nb = edges.size - 1
    b = np.clip(np.digitize(X[idx], edges) - 1, 0, nb - 1)
    bed = (res > -0.15) & (res < 0.05)
    off, cnt = bin_percentile(res[bed].astype(np.float64), b[bed], nb, 50.0, cfg.local_min_points)
    seen = np.isfinite(off)
    if not seen.any():
        return result(empty, 0.0)
    # the bed is "observed" up to the last bin with bed returns (gaps of a few bins are bridged)
    last = int(np.flatnonzero(seen)[-1])
    x_seen = float(edges[last + 1])
    centres = 0.5 * (edges[:-1] + edges[1:])
    off = np.interp(centres, centres[seen], off[seen])
    r = res - off[b]
    anomaly = (r > cfg.min_excess) & (r < cfg.max_excess) & (X[idx] < x_seen)
    keep = anomaly.copy()
    if cfg.min_point_top > -1.0:
        keep &= h[idx] > cfg.min_point_top
    # Require bed support in the *same* along-track bin: interpolation across an unobserved
    # trough / puddle or gap in the bed must not produce a near-bed alarm.
    near = empty
    if with_near and cfg.near_enabled:
        central_bed = bed & (np.abs(dy[idx]) <= cfg.near_half_width)
        cb = b[central_bed]
        lat = np.floor((dy[idx][central_bed] + cfg.near_half_width)
                       / max(cfg.template_bin, 1e-6)).astype(np.int64)
        # distinct lateral template bins with bed returns per along-track bin: one
        # np.unique over (along-track bin, lateral bin) pairs instead of a loop over bins
        spread = np.zeros(nb, dtype=np.int64)
        if lat.size:
            lat -= lat.min()
            span = int(lat.max()) + 1
            spread = np.bincount(np.unique(cb.astype(np.int64) * span + lat) // span, minlength=nb)
        near_seen = ((np.bincount(cb, minlength=nb) >= cfg.local_min_points)
                     & (spread >= cfg.near_min_bed_lateral_bins))
        central = ((r > cfg.near_min_excess) & (r < cfg.max_excess)
                   & (X[idx] < min(cfg.near_range, x_seen)) & (np.abs(dy[idx]) <= cfg.near_half_width)
                   & seen[b] & near_seen[b])
        near = idx[central]
    return result(idx[keep], x_seen, idx[anomaly], near)


def mark_rail_line(clusters, X: np.ndarray, dy: np.ndarray, h: np.ndarray, cfg: LowObjectConfig,
                   rails_spacing: float, range_min: float) -> int:
    """26.09 (P3 rail start, ``rail_start_within`` > 0; docs/evidence/results/p3_rail_start_2026-09-26.json):
    set ``Cluster.rail_line`` on the low clusters near the train that are rail geometry, not an
    object; returns how many. A fresh start at a standing train saw the rail heads 3.0-3.6 m ahead
    3-12 cm above a young model's rail-head plane, in front of the range the bed cross-section is
    learned from (``template_range``), and STOPped on them (EXPERIMENTS §1j).

    ``X``, ``dy``, ``h``: the whole frame (vehicle X, track coordinates). A low cluster is marked
    when (1) it starts nearer than ``rail_start_within``; (2) its lateral extent reaches an expected
    rail line (the axis +- ``rails_spacing`` / 2) within ``rail_start_lateral``; (3) it is at most
    ``rail_start_max_width`` wide across the track (an object lying across a rail is wider); (4)
    the same lateral band continues along the track: at least 4 of the 0.25 m bins between
    ``range_min`` - 0.5 m and ``rail_start_within`` + 2 m, outside the cluster's extent +- 0.3 m,
    hold >= 2 returns (a piece of a structure elongated along the track); and (5) its top - the
    band's highest return within its extent, the corridor points above the envelope floor
    included - is at most ``rail_start_margin`` above the band's height where the cluster is not
    (the median of those bins' highest returns: the rail head's own line). An object standing on a
    rail rises above that line (the organizers' 0.10 m object by 0.10 m). Only where the heights
    are 0.3 m below to 0.6 m above the modelled rail head. (6) (safety review of 26.09) That line
    is at least ``rail_start_min_ref`` above the modelled rail head: the young model's fault the
    rule compensates (the finding: 0.135-0.148 m); under a correct model (~0) nothing is marked.
    The tracker withholds a new report of a marked track that was never matched at >=
    ``rail_start_within`` (``Tracker.update``); that clause is no safeguard (a track deleted after
    its misses, a detector reset or a re-mount starts again): the margins (5) and (6) are."""
    near = float(cfg.rail_start_within)
    todo = [c for c in clusters if c.kind == "low" and c.distance < near and c.points_idx.size]
    if not todo:
        return 0
    x_lo, x_hi, step = float(range_min) - 0.5, near + 2.0, 0.25
    sel = np.flatnonzero((X >= x_lo) & (X < x_hi) & (np.abs(dy) < cfg.half_width + 0.5) & (h > -0.3) & (h < 0.6))
    Xs, dys, hs = X[sel].astype(np.float64), dy[sel], h[sel]
    half, tol = 0.5 * float(rails_spacing), float(cfg.rail_start_lateral)
    nb = int(np.ceil((x_hi - x_lo) / step))
    n = 0
    for c in todo:
        d = dy[c.points_idx]
        d0, d1 = float(d.min()), float(d.max())
        if not any(d0 <= s * half + tol and d1 >= s * half - tol for s in (-1.0, 1.0)):
            continue
        if float(c.size[1]) > cfg.rail_start_max_width:
            continue
        x0, x1 = float(c.bbox_min[0]), float(c.bbox_max[0])
        band = (dys >= d0) & (dys <= d1)
        foot = band & (Xs >= x0) & (Xs <= x1)
        if not foot.any():
            continue
        out = band & ((Xs < x0 - 0.3) | (Xs > x1 + 0.3))
        b = np.clip(np.floor((Xs[out] - x_lo) / step).astype(np.int64), 0, nb - 1)
        cnt = np.bincount(b, minlength=nb)
        top_bin = np.full(nb, -np.inf)
        np.maximum.at(top_bin, b, hs[out].astype(np.float64))
        ok = cnt >= 2
        if int(ok.sum()) < 4:
            continue
        line = float(np.median(top_bin[ok]))
        if line >= cfg.rail_start_min_ref and float(hs[foot].max()) <= line + cfg.rail_start_margin:
            c.rail_line = True
            n += 1
    return n
