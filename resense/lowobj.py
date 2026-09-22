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
   and cables are long) and have ``min_points`` voxels.

Where the bed is not observed (beyond ~50-80 m, grazing incidence) there is no local
offset and nothing is reported: the stage's range is where the bed is seen. Puddles in the
trough return nothing or mirror images *below* the bed (negative residuals): they are
ignored by construction.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

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
        sel = (X > x0) & (X < x1) & (dy > self.edges[0]) & (dy < self.edges[-1]) & (h > -1.2) & (h < 0.4)
        if sel.sum() < 200:
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
                   h_bottom: float) -> Tuple[np.ndarray, float]:
    """(indices of low candidates, range up to which the bed was observed)."""
    if template.prof is None:
        return np.zeros(0, dtype=np.int64), 0.0
    x1 = min(cfg.range_max, x_limit)
    band = (X >= range_min) & (X < x1) & (np.abs(dy) <= cfg.half_width) & (h < h_bottom) & (h > -1.2)
    idx = np.flatnonzero(band)
    if idx.size == 0:
        return idx, 0.0
    res = h[idx] - template(dy[idx])
    edges = np.arange(range_min, x1 + cfg.local_bin, cfg.local_bin)
    nb = edges.size - 1
    b = np.clip(np.digitize(X[idx], edges) - 1, 0, nb - 1)
    bed = (res > -0.15) & (res < 0.05)
    off, cnt = bin_percentile(res[bed].astype(np.float64), b[bed], nb, 50.0, cfg.local_min_points)
    seen = np.isfinite(off)
    if not seen.any():
        return np.zeros(0, dtype=np.int64), 0.0
    # the bed is "observed" up to the last bin with bed returns (gaps of a few bins are bridged)
    last = int(np.flatnonzero(seen)[-1])
    x_seen = float(edges[last + 1])
    centres = 0.5 * (edges[:-1] + edges[1:])
    off = np.interp(centres, centres[seen], off[seen])
    r = res - off[b]
    keep = (r > cfg.min_excess) & (r < cfg.max_excess) & (X[idx] < x_seen)
    if cfg.min_top > -1.0:
        keep &= h[idx] > cfg.min_top
    return idx[keep], x_seen
