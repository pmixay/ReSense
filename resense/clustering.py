"""Range-adaptive clustering of corridor candidates and cluster descriptors."""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable, List, Optional

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from resense import _native
from resense.config import ClusterConfig, GaugeConfig
from resense.gauge import gauge_reach_mask
from resense.sensor import AZIMUTH_STEP_DEG, expected_points


@dataclass
class Cluster:
    points_idx: np.ndarray       # indices into the frame
    n: int                       # number of occupied voxels (~ distinct rays)
    n_raw: int                   # number of raw points
    centroid: np.ndarray         # (3,) vehicle frame
    bbox_min: np.ndarray         # (3,)
    bbox_max: np.ndarray         # (3,)
    distance: float              # along-track distance of the nearest point (m)
    lateral: float               # lateral offset of the centroid from the track axis (m)
    height_min: float            # lowest point above the rail head (m)
    height_max: float
    intensity: float             # mean intensity
    n_expected: float            # visibility prior: expected returns for this size at this range
    score: float                 # 0..1 single-frame plausibility
    zone: str = "warning"        # 'gauge' (inside the strict gauge) or 'warning'
    n_gauge: int = 0             # voxels inside the strict gauge
    retro: bool = False          # demoted to advisory as a retro-reflective sign / marker
    reason: str = ""             # why the cluster is advisory although it has gauge voxels ('' = it has not / it is an obstacle)
    kind: str = ""               # v0.6: 'low' = a bump above the track bed (resense/lowobj.py), '' = corridor cluster
    rail_line: bool = False      # 26.09: a low cluster near the train that is rail geometry (lowobj.mark_rail_line; lowobj.rail_start_within)
    wall_kept: bool = False      # 26.09: the wall-at-the-side rule would have dropped it; kept by cluster.wall_keep_gauge_voxels
    demoted: bool = False        # 26.09 (P3 range): in the strict gauge by its voxels, demoted only by a shape signature (SHAPE_SIGNATURES)
    thin: bool = False           # 26.09 (tracking.stop_keep_thin): flatter than min_height, kept only to continue a reported obstacle track
    weak: bool = False           # 27.09 (cluster.weak_min_points): fewer voxels than min_points, kept only as far evidence for an approaching track
    ring_count: int = 0          # distinct known channels in current-frame strict-gauge points; 0 = no ring evidence
    low_height_weak: bool = False  # below the straddle top-height threshold; only bounded continuation of a low STOP
    spared: bool = False         # 14.10: column-shaped, but not demoted as a column because its top is seen free (top_is_free; tracking.column_free_min_spares)
    cut: bool = False            # 14.10: a part of an oversize cluster cut along its wall surface (cluster.structure_cut_tol; Detector._not_part_of_corridor_objects)

    @property
    def size(self) -> np.ndarray:
        return self.bbox_max - self.bbox_min


# 26.09 (P3 range): the demotion reasons that are shape heuristics for infrastructure, applied to a
# cluster that has enough voxels inside the strict gauge; ``column`` is not one of them (the column
# hold of the tracker handles it), nor the far-field and overhead reasons, which say the geometry is
# not trusted there or the cluster is above the envelope (``Cluster.demoted``,
# ``tracking.stop_keep_signature``)
SHAPE_SIGNATURES = ("elevated", "floating", "edge", "wall_face")


def _scaled(xyz: np.ndarray, range_scale: float) -> np.ndarray:
    r = np.linalg.norm(xyz, axis=1)
    return xyz / (1.0 + r / range_scale)[:, None]


def voxelize(xyz: np.ndarray, cfg: ClusterConfig):
    """Voxel-downsample in range-normalised space. Returns (voxel_points, inverse) where
    ``inverse[i]`` is the voxel index of raw point i."""
    if xyz.shape[0] == 0:
        return np.zeros((0, 3), np.float32), np.zeros(0, int)
    p = _scaled(xyz, cfg.range_scale)
    keys = np.floor(p / cfg.voxel).astype(np.int64)
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    nv = int(inv.max()) + 1
    sums = np.zeros((nv, 3), np.float64)
    np.add.at(sums, inv, xyz)
    counts = np.bincount(inv, minlength=nv).astype(np.float64)
    return (sums / counts[:, None]).astype(np.float32), inv


def dbscan_labels(p: np.ndarray, eps: float, min_samples: int) -> np.ndarray:
    """The labels of ``sklearn.cluster.DBSCAN(eps, min_samples).fit_predict(p)``, exactly, in
    ~0.5 ms instead of ~2.5 ms per call (sklearn's validation and neighbour machinery dominate
    on our 100-1 000 voxels; the clustering itself is trivial).

    The same definition, step by step: the neighbours of a point are the points whose squared
    distance, summed over x, y, z in float64 in that order (sklearn's KD-tree leaf test), is at
    most ``eps * eps`` (the point itself included); a point with at least ``min_samples``
    neighbours is a core point; core points joined by neighbour links form the clusters, numbered
    in the order of their lowest core index (the order of sklearn's seed loop); a non-core point
    with a core neighbour takes the lowest-numbered of its neighbours' clusters (the first
    expansion that reaches it); the rest is noise, ``-1``. ``tests/test_cpu_savings.py`` checks
    it against sklearn on random sets."""
    n = p.shape[0]
    labels = np.full(n, -1, dtype=np.intp)
    if n == 0:
        return labels
    q = np.asarray(p, dtype=np.float64)
    # a slightly larger radius, then the exact test: the tree's own bound checks may differ in
    # the last bit from sklearn's, the per-pair sum below does not
    pairs = cKDTree(q).query_pairs(eps * (1.0 + 1e-6), output_type="ndarray")
    if pairs.size:
        a, b = pairs[:, 0], pairs[:, 1]
        d = q[a] - q[b]
        d2 = d[:, 0] * d[:, 0]
        d2 = d2 + d[:, 1] * d[:, 1]
        d2 = d2 + d[:, 2] * d[:, 2]
        keep = d2 <= float(eps) * float(eps)
        a, b = a[keep], b[keep]
        deg = np.bincount(a, minlength=n) + np.bincount(b, minlength=n) + 1
    else:
        a = b = np.zeros(0, dtype=np.intp)
        deg = np.ones(n, dtype=np.intp)
    core = deg >= min_samples
    ci = np.flatnonzero(core)
    if ci.size == 0:
        return labels
    pos = np.full(n, -1, dtype=np.intp)
    pos[ci] = np.arange(ci.size)
    cc = core[a] & core[b]
    g = coo_matrix((np.ones(int(cc.sum()), dtype=np.int8), (pos[a[cc]], pos[b[cc]])), shape=(ci.size, ci.size))
    ncomp, comp = connected_components(g, directed=False)
    first = np.full(ncomp, ci.size, dtype=np.intp)          # lowest core position of each component
    np.minimum.at(first, comp, np.arange(ci.size))
    rank = np.empty(ncomp, dtype=np.intp)
    rank[np.argsort(first, kind="stable")] = np.arange(ncomp)
    labels[ci] = rank[comp]
    m1 = core[a] & ~core[b]                                 # border points: the lowest neighbouring cluster
    m2 = core[b] & ~core[a]
    bi = np.concatenate([b[m1], a[m2]])
    if bi.size:
        bl = np.concatenate([labels[a[m1]], labels[b[m2]]])
        best = np.full(n, ncomp, dtype=np.intp)
        np.minimum.at(best, bi, bl)
        labels[bi] = best[bi]
    return labels


def cluster_labels(xyz: np.ndarray, cfg: ClusterConfig) -> np.ndarray:
    """DBSCAN in range-normalised coordinates so that eps grows linearly with range.

    p' = p / (1 + r / range_scale)  =>  eps_metric(r) = eps * (1 + r / range_scale)
    """
    if xyz.shape[0] == 0:
        return np.zeros(0, dtype=int)
    p = _scaled(xyz, cfg.range_scale)
    return dbscan_labels(p, cfg.eps, cfg.min_samples)


def find_clusters(xyz: np.ndarray, intensity: np.ndarray, dy: np.ndarray, h: np.ndarray,
                  in_gauge: np.ndarray, cfg: ClusterConfig,
                  frame_idx: Optional[np.ndarray] = None, axis_valid: float = 1e9,
                  min_points_factor: float = 1.0, factor_range: float = 0.0,
                  smear_max_length: float = 0.0, smear_max_width: float = 0.0,
                  low: Optional[np.ndarray] = None, low_cfg=None,
                  height_valid: Optional[float] = None, gauge: Optional[GaugeConfig] = None,
                  dy_alt: Optional[np.ndarray] = None, in_rail: Optional[np.ndarray] = None,
                  keep_thin: bool = False, dy_report: Optional[np.ndarray] = None,
                  weak_from: float = 0.0, ring: Optional[np.ndarray] = None,
                  low_height_margin: float = 0.0, frame_xyz: Optional[np.ndarray] = None,
                  frame_ring: Optional[np.ndarray] = None, frame_h: Optional[np.ndarray] = None,
                  frame_dy: Optional[np.ndarray] = None) -> List[Cluster]:
    """Voxelise candidates, cluster the voxels, describe and filter the clusters.

    ``xyz``/``intensity``/``dy``/``h``/``in_gauge`` are the corridor candidates;
    ``frame_idx`` maps candidates back to frame indices (identity if None; -1 marks points
    merged from earlier frames by the accumulation, they are left out of ``points_idx``).
    ``min_points_factor`` scales the point-count thresholds (``min_points``,
    ``min_points_far``, ``gauge_min_points``) for clusters beyond ``factor_range`` when
    several frames were merged, so that accumulated noise does not pass a single-frame bar.
    ``smear_max_length`` (> 0 with accumulation) is the smear guard: a merged cluster longer
    than this along X is a static object shifted by a wrong ego speed (or a moving one), so
    it is re-described from its current-frame points only, with single-frame thresholds - a
    wrong speed then degrades to single-frame behaviour instead of losing the object to the
    ``max_extent`` rule; ``smear_max_width`` is the same guard across the track (a moving
    person merged over 0.5 s, 21.09 review).

    v0.5 infrastructure signatures (``column``, ``wall_face``, ``elevated``, ``floating``,
    ``edge``; docs/ALGORITHM.md section 3.3) demote a cluster to advisory and record the
    rule in ``Cluster.reason``; nothing is dropped by them. Since v0.6 the ``column`` and
    ``floating`` signatures only apply off the track centre (``|lateral| >
    signature_min_lateral``): a broken cable or an object hanging into the envelope near the
    axis is an obstacle whatever its shape (organizers' Q&A: hanging cables must be detected);
    since 25.09 the ``floating`` shape also applies near the axis to a cluster longer than
    ``floating_long_min_length`` whose lowest point is above ``floating_long_min_bottom``
    (overhead infrastructure along the track).

    ``low`` (v0.6) flags candidates that are bumps above the track bed below the polygon
    bottom (``resense/lowobj.py``); a cluster made mostly of them skips the infrastructure
    filters written for the corridor (they would drop any 10 cm object) and is kept when it is
    short along the track (``low_cfg.max_length``), not wider than ``low_cfg.max_width`` and has
    ``low_cfg.min_points`` voxels; it is a gauge obstacle with ``kind = 'low'``.

    ``axis_valid`` is where the corridor's lateral position is trusted; ``height_valid`` (v0.6,
    default = ``axis_valid``) where its height reference is. Between the two - the far field of
    a straight tunnel, where the walls confirm the axis to ~200 m but the bed stopped returning
    at ~100 m and the extrapolated rail level drifts by 0.2-0.5 m (EXPERIMENTS.md §2d) - a
    cluster is an obstacle only if it is at least ``far_min_height`` tall, at most
    ``far_max_length`` long along the track (a face seen head-on, not a surface at grazing
    incidence) and reaches down below ``far_max_bottom``: a person, a trolley, a crate, a train
    ahead; not a flat patch of the far bed that the height error lifted into the polygon nor a
    sign hanging above it (``reason = 'beyond_height_ref'`` otherwise).

    ``gauge`` (the envelope profile and its axis-uncertainty margin) is what ``cfg.gauge_distance``
    measures a gauge cluster's distance against (:func:`resense.gauge.gauge_reach_mask`); without it
    the distance stays the cluster's nearest point.

    ``dy_alt`` (26.09, ``gauge.axis_union`` 3, off by default) is a second lateral coordinate of the
    candidates, measured from the sensor axis: the infrastructure and signature rules of a corridor
    cluster read it instead of ``dy`` when its mean places the cluster nearer the centre; the
    reported lateral and every other quantity keep ``dy``.

    ``in_rail`` (26.09) is the strict membership measured from the rails only; ``None`` = ``in_gauge``.
    It differs from ``in_gauge`` only with ``gauge.axis_union`` 1 / 3 (off), which adds the envelope
    measured from the sensor axis to ``in_gauge``. The wall keep (``cfg.wall_keep_gauge_voxels``)
    counts it, and an oversize cluster whose part in ``in_gauge`` is too long falls back to its part in
    it (safety review of 26.09: the union took in a long edge line beside an object and dropped both).

    ``keep_thin`` (26.09, ``tracking.stop_keep_thin``, on since 26.09): a corridor cluster flatter
    than ``min_height`` is not dropped but returned with ``thin`` set (every other test applied as
    usual); the caller hands such clusters to the tracker only to continue an obstacle track (one
    scan line of an object whose part inside the envelope is thinner than the ring spacing).

    ``dy_report`` (27.09, ``gauge.reference`` > 0, on): the lateral from the rail axis when
    ``dy`` is measured from the sensor axis; ``Cluster.lateral`` (the reported lateral) reads it, every
    rule reads ``dy`` but the gauge-distance reach, which reads it (with the strict membership of
    ``in_gauge``). ``None`` = ``dy``.
    ``weak_from`` (27.09, ``cluster.weak_min_points`` with ``tracking.thin_far_min_distance``, on by
    default): a corridor cluster at least this far with fewer voxels than the point-count bar but at
    least ``cfg.weak_min_points`` is not dropped but returned with ``weak`` set (every other test
    applied as usual); the caller hands it to the tracker only, as far evidence for an approaching
    track. ``ring`` contains decoded elevation-channel IDs (negative = unknown). The experimental
    ``cfg.weak_min_rings`` path admits ``cfg.weak_min_points_with_rings`` voxels when enough distinct
    channels support current-frame points inside the strict gauge; historical and off-gauge points
    cannot supply this support. Both weak paths still require ``weak_from`` > 0.

    ``frame_xyz`` (13.10, ``cfg.column_free_max_top`` > 0): the whole current frame that ``frame_idx``
    indexes (vehicle frame, the sensor at the origin), ``frame_ring`` its channel ids (or None); with it the
    column signature does not demote a cluster whose top is seen free (:func:`top_is_free`). ``None`` = the
    column rule by its shape alone. ``frame_h`` / ``frame_dy`` (15.10): the frame's heights above the rail head
    and laterals (the detector's corridor coordinates of every return); without them the test reads only the
    first ring above the top (``cfg.column_free_window`` and ``cfg.column_free_tall_gap`` need them). The frame
    is indexed by azimuth once per call, on the first test (:class:`FrameRays`).
    """
    out: List[Cluster] = []
    if xyz.shape[0] == 0:
        return out
    if frame_idx is None:
        frame_idx = np.arange(xyz.shape[0])
    rays = None if frame_xyz is None else FrameRays(frame_xyz, frame_ring, frame_h, frame_dy)
    vox, inv = voxelize(xyz, cfg)
    vlabels = cluster_labels(vox, cfg)
    labels = vlabels[inv]                       # raw point labels
    for lab in np.unique(vlabels):
        if lab < 0:
            continue
        b = _Blob.of(xyz, np.flatnonzero(labels == lab), int((vlabels == lab).sum()))
        factor = min_points_factor
        size = b.size
        merged = smear_max_length > 0 and (frame_idx[b.idx] < 0).any()
        if merged and (size[0] > smear_max_length or (smear_max_width > 0 and size[1] > smear_max_width)):
            idx = b.idx[frame_idx[b.idx] >= 0]
            if idx.size == 0:
                continue
            b = _Blob.of(xyz, idx, int(np.unique(inv[idx]).size))
            factor = 1.0
        if low is not None and low_cfg is not None and bool(low[b.idx].mean() >= 0.5):
            c = _low_cluster(b, dy, h, intensity, frame_idx, cfg, low_cfg, low_height_margin)
        else:
            head = (dy, h, in_gauge, intensity, inv, frame_idx, cfg, factor, factor_range)
            tail = (height_valid, gauge, dy_alt, in_rail, keep_thin, dy_report, weak_from, ring, rays)
            c = _corridor_cluster(b, *head, axis_valid, *tail)
            if c is None and cfg.structure_cut_tol > 0 and cfg.oversize_split_max_length > 0 \
                    and float(b.size.max()) > cfg.max_extent and _split_part(b, in_gauge, in_rail, inv, cfg) is None:
                # 13.10 (cluster.structure_cut_tol): an oversize cluster that the 25.09 split refused
                # (dropped whole) may be an object standing in front of the long surface it touches; its
                # parts off that surface are described on their own, every rule applied
                # (_off_structure_parts). A cluster whose split part was accepted keeps the split's
                # verdict: the cut gives no second chance to a part the rules dropped
                for part in _off_structure_parts(b, xyz, h, in_gauge, vox, inv, cfg):
                    cp = _corridor_cluster(part, *head, axis_valid, *tail)
                    if cp is not None:
                        cp.cut = True
                        out.append(cp)
        if c is not None:
            out.append(c)
    out.sort(key=lambda c: c.distance)
    return out


@dataclass
class _Blob:
    """One DBSCAN cluster: indices into the candidate arrays, occupied voxels, points, box."""
    idx: np.ndarray
    n_vox: int
    pts: np.ndarray
    bmin: np.ndarray
    bmax: np.ndarray

    @classmethod
    def of(cls, xyz: np.ndarray, idx: np.ndarray, n_vox: int) -> "_Blob":
        pts = xyz[idx]
        return cls(idx, n_vox, pts, pts.min(axis=0), pts.max(axis=0))

    @property
    def size(self) -> np.ndarray:
        return self.bmax - self.bmin


def _visibility(b: _Blob, width: float, height: float, cfg: ClusterConfig):
    """(expected returns for this size at this range, 0..1 score of the voxels seen against them)."""
    n_exp = float(expected_points(np.linalg.norm(b.pts.mean(axis=0)), width, height))
    score = float(np.clip(b.n_vox / max(n_exp, 1.0) / cfg.visibility_ratio, 0.0, 1.0)) if n_exp > 1.0 else 1.0
    return n_exp, score


def _low_cluster(b: _Blob, dy, h, intensity, frame_idx, cfg: ClusterConfig, low_cfg,
                 height_margin: float = 0.0) -> Optional[Cluster]:
    """A cluster made mostly of bed bumps (v0.6): kept as a gauge obstacle of ``kind = 'low'``
    when it is short along the track, not too wide, wide enough across the track and reaches
    the rail-head plane; the corridor's infrastructure filters are not applied."""
    size = b.size
    if (size[0] < getattr(low_cfg, "min_length", 0.0)
            or size[0] > low_cfg.max_length or size[1] > low_cfg.max_width
            or size[2] < low_cfg.min_height or b.n_vox < low_cfg.min_points):
        return None
    # rail-head slivers, fastenings and joint bars are narrow across the track; a 30 cm object is not
    if size[1] < low_cfg.min_width:
        return None
    # the object must reach the rail-head plane (bed fixtures stay below it by design)
    weak_height = low_cfg.min_top > -1.0 and float(h[b.idx].max()) < low_cfg.min_top
    if weak_height and (height_margin <= 0 or float(h[b.idx].max()) < low_cfg.min_top - height_margin):
        return None
    n_exp, score = _visibility(b, max(float(size[1]), 0.15), max(float(size[2]), 0.1), cfg)
    fi = frame_idx[b.idx]
    return Cluster(
        points_idx=fi[fi >= 0], n=b.n_vox, n_raw=int(b.idx.size), centroid=b.pts.mean(axis=0),
        bbox_min=b.bmin, bbox_max=b.bmax, distance=float(b.pts[:, 0].min()), lateral=float(dy[b.idx].mean()),
        height_min=float(h[b.idx].min()), height_max=float(h[b.idx].max()),
        intensity=float(intensity[b.idx].mean()) if intensity is not None else 0.0,
        n_expected=n_exp, score=score, zone="gauge", n_gauge=b.n_vox, kind="low", low_height_weak=weak_height,
    )


def _is_infrastructure(size: np.ndarray, lateral: float, h_max: float, cfg: ClusterConfig,
                       spare_wall: bool = False, lat_along: Optional[float] = None) -> bool:
    """Shapes dropped outright: linear infrastructure along the track (rails, pipes, cables,
    duct edges), low narrow track hardware, wall-like structure at the side, a tall long narrow
    wall segment that a mis-estimated axis pulled into the corridor, and long linear structure
    at the side (platform edge, duct, cabinet row). ``spare_wall`` (26.09,
    ``cluster.wall_keep_gauge_voxels``) skips the wall-at-the-side rule."""
    if size[0] > cfg.thin_min_length and size[1] < cfg.thin_max_width and size[2] < cfg.thin_max_height:
        return True
    # rail clamps, cables, joint bars — tune with injected data
    if h_max < cfg.hardware_max_top and size[1] < cfg.hardware_max_width and size[2] < cfg.hardware_max_height:
        return True
    if size[2] > cfg.wall_min_height and abs(lateral) > cfg.wall_min_lateral and not spare_wall:
        return True
    if size[2] > cfg.wall_min_height and size[0] > cfg.wall_segment_min_length and size[1] < cfg.wall_segment_max_width:
        return True
    return (size[0] > cfg.linear_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.linear_max_height
            and abs(lateral if lat_along is None else lat_along) > cfg.linear_min_lateral)


class FrameRays:
    """15.10: the current frame as the column free-top test (:func:`top_is_free`) reads it - the corrected cloud
    (vehicle frame, the sensor at the origin), its channel ids, and from the detector every return's height
    above the rail head (``h``) and lateral offset from the axis (``dy``); ``None`` where not known. The
    returns' azimuths are cached on the first :meth:`window` call as a uint8 bucket of tan(azimuth) per return
    (0.55 deg wide at the axis, 255 behind the sensor; ~0.7 ms on a 189 k return ride frame), and a window
    reads the returns of its buckets (~0.1-0.3 ms) before the exact test: 14.10 tested every return of the
    frame in floats in every test (~1.4 ms), a cost that grew with the column-shaped clusters of a frame. (A
    radix-sorted index on top of the buckets, measured: +0.6 ms a frame, its reads no faster.) The returns over
    the track axis that the local vault is read from are cached the same way (:meth:`axis_band`).
    :func:`find_clusters` makes one per call (once a frame in the detector), so the cache lives one frame."""

    SCALE, MID = 105.0, 127.0         # bucket = SCALE tan(azimuth) + MID: +-50 deg (the sensor's field) in 2-252

    def __init__(self, xyz: np.ndarray, ring: Optional[np.ndarray] = None, h: Optional[np.ndarray] = None,
                 dy: Optional[np.ndarray] = None):
        self.xyz, self.ring, self.h, self.dy = xyz, ring, h, dy
        self._keys: Optional[np.ndarray] = None
        self._band: Optional[tuple] = None

    def _bucket(self, t: float) -> int:
        return int(min(max(float(np.floor(t * self.SCALE + self.MID)), 0.0), 254.0))

    def window(self, a0: float, a1: float) -> np.ndarray:
        """Indices (ascending) of the returns ahead of the sensor (X > 0) with azimuth in [a0, a1] deg, compared
        as Y >= tan(a0) X and Y <= tan(a1) X (the frame scan of 13.10, return for return)."""
        t0, t1 = np.tan(np.radians(a0)), np.tan(np.radians(a1))
        if self._keys is None:
            X, Y = self.xyz[:, 0], self.xyz[:, 1]
            with np.errstate(divide="ignore", invalid="ignore"):
                s = Y / X
            s *= self.SCALE
            s += self.MID
            np.clip(s, 0.0, 254.0, out=s)               # beyond the field: the end buckets
            np.copyto(s, 255.0, where=~(X > 0))         # behind the sensor (and X = 0)
            self._keys = s.astype(np.uint8)
        # one bucket of slack on either side: the key's float32 quotient and the bounds' products may round apart
        b0, b1 = max(self._bucket(t0) - 1, 0), min(self._bucket(t1) + 1, 254)
        c = np.flatnonzero((self._keys >= b0) & (self._keys <= b1))
        X, Y = self.xyz[c, 0], self.xyz[c, 1]
        return c[(X > 0) & (Y >= t0 * X) & (Y <= t1 * X)]

    def axis_band(self):
        """The returns over the track axis (|dy| <= ``_VAULT_BAND``) above 0.5 m, cached on first use, sorted
        along the track: (frame indices, X, h, cell of 1 m along x 0.25 m across) for :func:`_local_vault`; None
        without heights or laterals."""
        if self.h is None or self.dy is None:
            return None
        if self._band is None:
            b = np.flatnonzero((np.abs(self.dy) <= _VAULT_BAND) & (self.h > 0.5))
            X = self.xyz[b, 0].astype(np.float64)
            o = np.argsort(X, kind="stable")
            b, X = b[o], X[o]
            cell = np.floor(X).astype(np.int64) * 8 + np.floor((self.dy[b] + _VAULT_BAND) / 0.25).astype(np.int64)
            self._band = (b, X, self.h[b], cell)
        return self._band


_VAULT_BAND = 0.5      # m either side of the track axis over which the local vault is read (_local_vault)


def _local_vault(rays: FrameRays, idx: np.ndarray, h_top: float, face: np.ndarray) -> Optional[float]:
    """15.10: the lowest height above the rail head of what is over the track at the object - the returns within
    ``_VAULT_BAND`` of the axis, from max(1 m, 15 %) before the object to max(5 m, 15 %) beyond it (the rings
    above 2 deg are 0.5 deg apart: at 60 m a flat ceiling is hit at 56 and 70 m only), higher than its top
    (``h_top``) + 0.1 m - its own face above its top (``face``: the returns of its azimuth window at its range) left
    out. The vault, the ceiling, a beam or a lintel over the track, measured in the frame itself: the heights of
    the far field drift with the rail level (0.3-0.7 m low at 110-150 m on the recordings), the vault's and the
    object's alike. Over the axis, not beside the object: a colonnade at the platform edge (the ride, columns 4 m
    apart at 0.9-1.0 m) puts its neighbours' faces beside each column at its range. Only what stands over free
    space counts: a cell of 1 m along the track x 0.25 m across with returns between 0.5 m and the object's top
    holds something standing (a post, a column, a wall the far axis lays across the track, an object) and is left
    out (the ride's crossover: posts over the far axis at 124-155 m read as a 3.0-3.1 m vault). A round vault is
    lower over the envelope's edge than over the axis (0.2-0.3 m: cluster.column_free_vault_margin). ``None`` when
    nothing is seen there (or no heights). The returns over the axis are the frame's cached :meth:`FrameRays.axis_band`."""
    band = rays.axis_band()
    if band is None:
        return None
    ib, xb, hb, cb = band
    x = rays.xyz[idx, 0]
    x0, x1 = float(x.min()), float(x.max())
    i0 = int(np.searchsorted(xb, x0 - max(1.0, 0.15 * x0), "left"))
    i1 = int(np.searchsorted(xb, x1 + max(5.0, 0.15 * x0), "right"))
    keep = ~np.isin(ib[i0:i1], face)
    H, cell = hb[i0:i1][keep], cb[i0:i1][keep]
    over = H > h_top + 0.1
    standing = np.unique(cell[~over])                       # every return here is above 0.5 m
    over &= ~np.isin(cell, standing)
    return float(H[over].min()) if over.any() else None


def _ids_in_elevation_order(rw: np.ndarray, qe: np.ndarray) -> bool:
    """15.10 (P2): the window's channel ids number its rings from the highest down, as the Pandar128's
    (``sensor.RING_ELEVATION_DEG``): the mean elevation of each id's returns falls as the id rises (0.02 deg
    slack), over at least three ids. A driver numbering bottom-up, another sensor's interleaved order or unknown
    ids are not read as ring order."""
    ok = rw >= 0
    ids, inv = np.unique(rw[ok], return_inverse=True)
    if ids.size < 3:
        return False
    mean = np.bincount(inv, weights=qe[ok]) / np.bincount(inv)
    return bool((np.diff(mean) <= 0.02).all())


def _ring_between(rays: FrameRays, w: np.ndarray, head: np.ndarray, ring: np.ndarray, qe: np.ndarray,
                  top: float, e1: float, a0: float, a1: float) -> bool:
    """The empty-ring evidence of :func:`top_is_free`: a ring of the sensor lies between the top's ring and the
    first ring above it that returns over the window (``ring``), and it returned nothing there - its rays
    passed over the top and left the sensor's range. Read from the channel ids where the window carries them in
    elevation order (``_ids_in_elevation_order``; the top's ring ``head``). 15.10 (P2): otherwise only where the
    frame itself shows such a ring beside the object - at least 6 returns (3 rays, each echo twice) at least
    15 m away (nearer, a return's elevation scatters by up to 0.05 deg) within 1.5 deg of its azimuth span,
    between the two rings with 0.04 deg to spare (the rings are >= 0.086 deg apart; a roll of 1 deg tilts a ring
    by 0.026 deg over 1.5 deg). 13.10 / 14.10 read the Pandar128's ring table there, its ring nearest to the top
    put at the top: a 64-ring sensor read through it saw an empty ring above a column occluded from above at
    30-100 m (the safety review of 14.10), and a mount tilt put the top at the wrong ring."""
    rw = None if rays.ring is None else rays.ring[w].astype(np.int64)
    if rw is not None and rw.min() < rw.max() and _ids_in_elevation_order(rw, qe):  # set O: one id (0) = none
        hd, first = rays.ring[head].astype(np.int64), rw[ring]
        if hd.min() >= 0 and first.min() >= 0 and first.max() < hd.min():
            rt, r1 = int(hd.min()), int(first.max())
            return r1 < rt - 1 and not ((rw > r1) & (rw < rt)).any()
        return False
    b = rays.window(a0 - 1.5, a1 + 1.5)
    s = rays.xyz[b].astype(np.float64)
    sh = np.hypot(s[:, 0], s[:, 1])
    se = np.degrees(np.arctan2(s[:, 2], sh))
    return int(((se > top + 0.04) & (se < e1 - 0.04) & (np.hypot(sh, s[:, 2]) >= 15.0)).sum()) >= 6


def _follow(qe: np.ndarray, same: np.ndarray, qh: np.ndarray, top: float, h_top: float):
    """15.10 (P4, ``cluster.column_free_tall_gap``): the object's own returns above the candidates' cut,
    followed ring by ring over the window: while the next ring with returns above the top has one at the
    top's range (``same``), the top moves up to it. Returns the top's elevation, its height above the rail
    head (``qh``: the window's heights) and the window's returns of the top ring at the top's range (None: not
    moved)."""
    last = None
    while True:
        up = qe > top + 0.04
        if not up.any():
            return top, h_top, last
        lev = up & (qe <= float(qe[up].min()) + 0.05)
        s = lev & same
        if not s.any():
            return top, h_top, last
        top, h_top, last = float(qe[lev].max()), max(h_top, float(qh[s].max())), s


def top_is_free(frame_xyz, idx: np.ndarray, min_returns: int = 2, frame_ring: Optional[np.ndarray] = None,
                window: float = 0.0, vault_margin: float = 0.3, tall_gap: float = 0.0) -> bool:
    """13.10 (``cluster.column_free_max_top``): the top of the cluster whose current-frame returns are
    ``frame_xyz[idx]`` is seen free - the rays right above it pass over it. Over the cluster's azimuth span
    plus 0.12 deg (an azimuth step and the rings' azimuth offsets) the first ring with returns above the top
    has none at the top's range (within max(0.5 m, 2 %)): a column continues up to the vault and that ring
    meets it there. And either a ring of the sensor lies between them that returned nothing over the span -
    its rays passed over the top and left the sensor's range (the far field; :func:`_ring_between`) - or at
    least ``min_returns`` of that ring's returns are beyond the top and more than those nearer (nearer:
    occluded from above, no evidence). Nothing above within 2.5 deg is no evidence.
    ``frame_xyz``: a :class:`FrameRays` (the detector's: with heights and laterals), or the whole frame in the
    vehicle frame, the sensor at the origin, with ``frame_ring`` its channel ids (0 the highest ring).

    15.10 (P1, ``window`` = ``cluster.column_free_window`` > 0; needs the heights): a column whose face right
    above the cluster's top returns nothing (dark paint, glass, a black sign) while the rays beside it reach the
    tunnel behind read as free on 14.10, whose continuation was the first ring with returns only. Now any
    return at the top's range over the window above the top up to ``window`` m over it, within the top ring's
    lateral extent +- 0.15 m (its own face; the round lining beside it at its range is not), is continuation -
    but never up to the local vault (:func:`_local_vault`; ``vault_margin`` under it): the vault, a ceiling or a
    beam over the object meets the rays above a free top at the object's range too. No vault seen: no window.

    15.10 (P4, ``tall_gap`` = ``cluster.column_free_tall_gap`` > 0; for a cluster reaching the candidates' cut
    under the envelope top): the object's own returns at its range are followed above the cut to its true top
    (:func:`_follow`), which must lie at least ``tall_gap`` under the local vault (seen), with no return of its
    own face above it up to ``vault_margin`` under the vault, the first ring above it passing it as above, and
    every one of its own rays (the top ring's azimuth span) above it up to there returning beyond it
    (:func:`_own_rays_pass`): a column whose face above the cut is dark returns nothing on its own rays."""
    rays = frame_xyz if isinstance(frame_xyz, FrameRays) else FrameRays(frame_xyz, frame_ring)
    if idx.size < 2 or (tall_gap > 0 and rays.h is None):
        return False                      # a cluster at the cut is followed only with the frame's heights
    p = rays.xyz[idx].astype(np.float64)
    rh = np.hypot(p[:, 0], p[:, 1])
    el = np.degrees(np.arctan2(p[:, 2], rh))
    az = np.degrees(np.arctan2(p[:, 1], p[:, 0]))
    top = float(el.max())
    head = el >= top - 0.06                                         # the top's own ring
    r_top = float(np.median(np.hypot(rh, p[:, 2])[head]))
    a0, a1 = float(az.min()), float(az.max())
    w = rays.window(a0 - 0.12, a1 + 0.12)                           # the azimuth window, ahead of the sensor
    q = rays.xyz[w].astype(np.float64)
    qh = np.hypot(q[:, 0], q[:, 1])
    qe = np.degrees(np.arctan2(q[:, 2], qh))
    qr = np.hypot(qh, q[:, 2])
    tol = max(0.5, 0.02 * r_top)
    same = np.abs(qr - r_top) <= tol                                # at the top's range
    tall = tall_gap > 0
    lim = None
    if rays.h is not None and (window > 0 or tall):
        qz = rays.h[w]
        h_top = float(rays.h[idx].max())
        vault = _local_vault(rays, idx, h_top, w[same])
        if tall:
            top, h_top, last = _follow(qe, same, qz, top, h_top)
            if vault is None or h_top > vault - tall_gap:
                return False              # not clearly under the vault (a column meets it), or no vault seen
            lim = vault - vault_margin
        else:
            # no vault seen (the far field: what is over the track there lies beyond the sensor's range): no
            # window, as 14.10 - it could reach the vault at the object's range unseen
            lim = None if vault is None else min(h_top + window, vault - vault_margin)
    up = (qe > top + 0.04) & (qe <= top + 2.5)   # above the top's own ring (the rings are >= 0.086 deg apart)
    if not up.any():
        return False
    e1 = float(qe[up].min())
    ring = up & (qe <= e1 + 0.05)
    if (same & ring).any():
        return False                      # the structure continues above the top: a column
    if lim is not None:
        # 15.10: its own face continues above a band that returns nothing - at its range and over its top ring's
        # lateral extent (+- 0.15 m; the round lining beside it at its range is not its face): a column
        d = rays.dy[idx][head]
        qd = rays.dy[w]
        if (same & up & (qz <= lim) & (qd >= float(d.min()) - 0.15) & (qd <= float(d.max()) + 0.15)).any():
            return False
    r = qr[ring]
    beyond, nearer = int((r > r_top + tol).sum()), int((r < r_top - tol).sum())
    free = _ring_between(rays, w, idx[head], ring, qe, top, e1, a0, a1) or (beyond >= min_returns
                                                                             and beyond > nearer)
    if free and tall:
        # the object's own rays over its true top - within the azimuth span of its top ring's returns, under the
        # vault margin's sight line at its range - every one of them returns beyond it
        qa = np.degrees(np.arctan2(q[:, 1], q[:, 0]))
        s0, s1 = (float(az[head].min()), float(az[head].max())) if last is None else \
            (float(qa[last].min()), float(qa[last].max()))
        rail = float(np.median(p[:, 2] - rays.h[idx]))
        e_lim = float(np.degrees(np.arctan2(lim + rail, float(np.median(rh[head])))))
        free = _own_rays_pass(qa, qe, qr > r_top + tol, up & (qe <= e_lim), s0, s1)
    return free


def _own_rays_pass(qa: np.ndarray, qe: np.ndarray, beyond: np.ndarray, above: np.ndarray, s0: float,
                   s1: float) -> bool:
    """15.10 (P4): the object's own rays over its true top pass beyond it - on at least two rings over the window's
    returns ``above`` the top, each ring's rays inside the top's azimuth span [``s0``, ``s1``] (on the ring's own
    0.1 deg grid, its phase read from its returns over the window) each have a return within 0.03 deg, and every
    such return is ``beyond`` the top. A ray without a return, at the top's range or nearer fails it: a column whose
    face above the candidates' cut returns nothing (dark), or a narrower shaft above a wider top whose own rays meet
    it while the rays beside it pass (a ray grazing it passes too: the span's own rays are all asked). Rings without
    a ray inside the span are not counted."""
    rings = 0
    rest = above.copy()
    while rest.any():
        lev = rest & (qe <= float(qe[rest].min()) + 0.05)
        rest &= ~lev
        a = qa[lev]
        phase = float(np.angle(np.exp(2j * np.pi * a / 0.1).mean()) / (2 * np.pi) * 0.1) % 0.1   # circular mean
        k0, k1 = int(np.ceil((s0 - 0.005 - phase) / 0.1)), int(np.floor((s1 + 0.005 - phase) / 0.1))
        if k1 < k0:
            continue
        for g in phase + 0.1 * np.arange(k0, k1 + 1):
            near = np.abs(a - g) <= 0.03
            if not near.any() or not beyond[lev][near].all():
                return False
        rings += 1
    return rings >= 2


def _advisory_reason(b: _Blob, dist: float, lateral: float, zone: str, dy, h, cfg: ClusterConfig,
                     axis_valid: float, height_valid: Optional[float], lat_along: Optional[float] = None,
                     free_top: Optional[Callable[[], bool]] = None) -> str:
    """Why a cluster is advisory although it may have gauge voxels ('' = it is an obstacle):
    beyond the range where the axis or the height reference is supported, hanging entirely in
    the top zone (cables, lamps), or a v0.5 infrastructure signature (EXPERIMENTS.md 1b).
    ``free_top`` (13.10, ``cluster.column_free_max_top``): asked only when the column shape fits, True =
    the cluster's top is seen free (:func:`top_is_free`), so it is not a column."""
    size = b.size
    hh = h[b.idx]
    h_min, h_max = float(hh.min()), float(hh.max())
    if dist > axis_valid:
        return "beyond_axis"
    if height_valid is not None and dist > height_valid and (
            size[2] < cfg.far_min_height or size[0] > cfg.far_max_length or h_min > cfg.far_max_bottom):
        return "beyond_height_ref"
    if h_min > cfg.overhead_min_height:
        return "overhead"
    if zone != "gauge":
        return ""
    ady = np.abs(dy[b.idx])
    off_centre = abs(lateral) > cfg.signature_min_lateral
    col_w = float(size[1])
    if cfg.column_width_trim > 0 and col_w >= cfg.column_max_width and b.idx.size >= 3:
        # 27.09 (P4 history): the width of the column's body, not of a few joined returns
        # only when the trimmed tails are sparse (they span at least column_width_trim_min_cut): a dense
        # uniform body 1.0-1.1 m wide keeps its box width (the tails of such a body are 0.1 m)
        q = float(cfg.column_width_trim)
        lo, hi = np.quantile(b.pts[:, 1], (q, 1.0 - q))
        if col_w - float(hi - lo) >= cfg.column_width_trim_min_cut:
            col_w = float(hi - lo)
    if cfg.column_min_height > 0 and size[2] > cfg.column_min_height and col_w < cfg.column_max_width \
            and (off_centre or col_w >= cfg.column_min_width) and not (free_top is not None and free_top()):
        return "column"                    # column, post, gate leg: taller than any listed object, narrow
    # opt-in, off by default: a cluster as short as the organizers' test objects (and near enough)
    # that the elevated or floating shape would demote stays an obstacle (the rules after them
    # are not tried either: scripts/short_signature_experiment.py, measured in docs/P4_AUDIT.md)
    short = (cfg.short_signature_max_length > 0 and size[0] <= cfg.short_signature_max_length
             and dist <= cfg.short_signature_max_distance)
    if cfg.elevated_min_height > 0 and h_min > cfg.elevated_min_height and size[1] > cfg.elevated_min_width:
        return "" if short else "elevated"   # beam / roof strip / gantry spanning the corridor above the rails
    # on by default since 25.09 (3.0 m, decided on the ride; 0 = off): longer than
    # floating_long_min_length along the track, the floating shape is an overhead duct / tray /
    # beam along the track wherever it is across it - but only when its lowest point is as high
    # as overhead infrastructure (floating_long_min_bottom, 1.6 m since the review of 25.09): a
    # cable tray, duct or pipe fallen onto the axis and hanging lower in the envelope is an obstacle
    along = (cfg.floating_long_min_length > 0 and size[0] > cfg.floating_long_min_length
             and h_min > cfg.floating_long_min_bottom)
    # opt-in (25.09, round 2; 0 = off): a compact cluster hanging free inside the envelope - every
    # extent at most floating_free_max_size, its outermost point at most floating_free_max_dy off the
    # axis and its top at most floating_free_max_top - reaches neither the wall side of the corridor
    # nor up to the vault, so it is not a sign, lamp or bracket fixed to them: the floating shape
    # does not demote it (the organizers' 0.3 m cube hanging 1.0-1.4 m up, 0.6-0.8 m off the axis)
    free = (cfg.floating_free_max_size > 0 and float(size.max()) <= cfg.floating_free_max_size
            and float(ady.max()) <= cfg.floating_free_max_dy and h_max <= cfg.floating_free_max_top)
    if cfg.floating_min_height > 0 and h_min > cfg.floating_min_height and size[2] < cfg.floating_max_height \
            and size[1] < cfg.floating_max_width and (off_centre or along) and not free:
        return "" if short else "floating"   # sign, lamp, bracket: small and not touching the ground
    if cfg.edge_min_lateral > 0 and abs(lateral if lat_along is None else lat_along) > cfg.edge_min_lateral \
            and size[0] > cfg.edge_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.edge_max_height:
        return "edge"                      # duct / bench / platform-edge fragment along the corridor edge
    if cfg.wall_face_min_height > 0 and size[2] > cfg.wall_face_min_height and h_max > cfg.wall_face_min_top:
        below = hh < cfg.wall_face_min_top
        if below.sum() >= 3 and ady[below].min() > cfg.wall_face_min_inner and ady[below].max() > cfg.wall_face_edge:
            return "wall_face"             # wall / portal face pulled in by the axis: hugs the edge, centre clear
    return ""


def find_hanging(xyz: np.ndarray, intensity: np.ndarray, dy: np.ndarray, h: np.ndarray,
                 cfg: ClusterConfig, top: float, range_min: float, max_distance: float,
                 in_gauge_idx: Optional[np.ndarray] = None) -> List[Cluster]:
    """Thin objects hanging from above into the envelope near the axis
    (``cluster.hanging_enabled``, on since 25.09; SCORECARD #11).

    The organizers' 5 cm object hanging from the roof dips only 0.2-0.4 m below the envelope top
    (``top``), with 1-3 returns there a frame, so it never reaches the corridor clustering's
    5-voxel minimum; the part that shows it is an object and not noise is above the envelope,
    where the corridor stops. Here the points of the whole frame near the axis
    (``|dy| < hanging_max_lateral``), above ``hanging_min_height`` and up to ``hanging_link_band``
    above the top are linked at the corridor's range-scaled radius (every point a core point:
    two returns a metre apart at 25 m are one object). A group is a hanging object when it has at
    least ``hanging_min_voxels`` voxels inside the strict envelope (at or below the top and, when
    ``in_gauge_idx`` is given, among those frame indices: the corridor's strict-gauge points, edge
    margin included), at least one voxel above the top, and is at most ``hanging_max_size`` along
    and across the track (a cable or a rod, not a duct, a tray or a ceiling). Only frame points up
    to ``max_distance`` are used: the returns
    above the sensor are 0.5 deg apart, so beyond ~60 m a 0.3 m dip is one ring or none.
    The clusters are gauge obstacles of ``kind = 'hanging'``; the caller drops those that
    overlap a cluster of the other stages (they decide) and the tracker confirms them like any
    other (``tracking.confirm_hits``, ``confirm_time_s``: 5 frames at 10 Hz).
    """
    out: List[Cluster] = []
    X = xyz[:, 0]
    lo, hi, lat = float(cfg.hanging_min_height), float(top + cfg.hanging_link_band), float(cfg.hanging_max_lateral)
    x0, x1 = float(range_min), float(max_distance)
    sel = _native.select(X.size, (h, ">", lo, "<=", hi), (dy, None, None, "<", lat, True), (X, ">=", x0, "<=", x1))
    if sel is None:
        sel = np.flatnonzero((h > lo) & (h <= hi) & (np.abs(dy) < lat) & (X >= x0) & (X <= x1))
    need = max(1, int(cfg.hanging_min_voxels))
    if sel.size < 2:
        return out
    ins = h[sel] <= top
    if int(ins.sum()) < need:
        return out
    if in_gauge_idx is not None:
        ins &= np.isin(sel, in_gauge_idx)
        if int(ins.sum()) < need:
            return out
    pts = xyz[sel]
    vox, inv = voxelize(pts, cfg)
    vlabels = dbscan_labels(_scaled(vox, cfg.range_scale), cfg.eps, 1)
    labels = vlabels[inv]
    above = h[sel] > top
    for lab in np.unique(vlabels):
        m = labels == lab
        n_in = int(np.unique(inv[m & ins]).size)
        if n_in < cfg.hanging_min_voxels or not (m & above).any():
            continue
        b = _Blob.of(pts, np.flatnonzero(m), int((vlabels == lab).sum()))
        size = b.size
        if size[0] > cfg.hanging_max_size or size[1] > cfg.hanging_max_size:
            continue
        k = sel[m]
        rng = float(np.linalg.norm(b.pts.mean(axis=0)))
        # the returns above the sensor are 0.5 deg apart (sensor.py): the prior with that elevation
        el = float(np.degrees(np.arctan2(float(b.pts[:, 2].mean()), max(rng, 1e-3))))
        n_exp = float(expected_points(rng, max(float(size[1]), 0.05), max(float(size[2]), 0.15), elevation_deg=el))
        score = float(np.clip(b.n_vox / max(n_exp, 1.0) / cfg.visibility_ratio, 0.0, 1.0)) if n_exp > 1.0 else 1.0
        out.append(Cluster(
            points_idx=k, n=b.n_vox, n_raw=int(k.size), centroid=b.pts.mean(axis=0),
            bbox_min=b.bmin, bbox_max=b.bmax, distance=float(b.pts[:, 0].min()), lateral=float(dy[k].mean()),
            height_min=float(h[k].min()), height_max=float(h[k].max()),
            intensity=float(intensity[k].mean()) if intensity is not None else 0.0,
            n_expected=n_exp, score=score, zone="gauge", n_gauge=n_in, kind="hanging",
        ))
    out.sort(key=lambda c: c.distance)
    return out


def _is_retro(b: _Blob, intensity, cfg: ClusterConfig) -> bool:
    """Retro-reflective plate / sign / marker: intensity is reflectivity %, > 100 only from
    retro-reflective material; small and low -> infrastructure, advisory only. A person in a
    hi-vis vest is taller, a train ahead is larger: both keep their zone."""
    if not (cfg.retro_intensity > 0 and intensity is not None and b.idx.size):
        return False
    size = b.size
    frac = float((intensity[b.idx] >= cfg.retro_intensity).mean())
    return frac >= cfg.retro_min_fraction and size[2] < cfg.retro_max_height and size[1] < cfg.retro_max_width


def _gauge_part(b: _Blob, in_gauge, inv, cfg: ClusterConfig) -> Optional[_Blob]:
    """The part of an oversized cluster inside the strict gauge (25.09,
    ``oversize_split_max_length``), when it is at most that long along the track: an object
    in the envelope that touches a long line at the corridor edge (a conductor rail, a duct
    edge) forms one cluster longer than ``max_extent`` with it and would be dropped whole.
    Only within ``oversize_split_max_distance``: the far corridor holds long sparse clusters
    with a few gauge voxels. ``None`` = no such part (the cluster stays dropped)."""
    m = in_gauge[b.idx]
    if not m.any():
        return None
    idx, pts = b.idx[m], b.pts[m]
    part = _Blob(idx, int(np.unique(inv[idx]).size), pts, pts.min(axis=0), pts.max(axis=0))
    if float(part.size[0]) > cfg.oversize_split_max_length or float(part.bmin[0]) > cfg.oversize_split_max_distance:
        return None
    return part


def _split_part(b: _Blob, in_gauge, in_rail, inv, cfg: ClusterConfig) -> Optional[_Blob]:
    """The 25.09 oversize split of :func:`_corridor_cluster`: the part in ``in_gauge``, else the part in
    ``in_rail`` (``None`` = ``in_gauge``). Safety review of 26.09 (gauge.axis_union): the sensor-axis
    envelope can take in a long line at the corridor edge beside an object, so the part grows past the
    split length; the part inside the envelope measured from the rails alone is then the object.
    ``None`` = the split refuses the cluster."""
    part = _gauge_part(b, in_gauge, inv, cfg)
    if part is None and in_rail is not None and in_rail is not in_gauge:
        part = _gauge_part(b, in_rail, inv, cfg)
    return part


_SURFACE_MIN_POINTS = 20    # points of a structure-cut surface fit (5 coefficients x 4)
# 14.10: |d y_w / dx| of a structure-cut surface at most this (45 deg to the track): the cut measures
# "in front" as the lateral residual, which overstates the distance from the surface by
# sqrt(1 + slope^2); a face across the track seen obliquely fits y(x, h) as well, and there a few cm
# in front of it would pass structure_cut_tol (at slope 5, 0.16 m); and a near-exact fit of a few scan
# lines has meaningless slopes (C, 14.10: 20 points over 8 m, slope -21). The walls of C where parts
# were cut: |slope| <= 0.25
_SURFACE_MAX_SLOPE = 1.0


def _off_structure_parts(b: _Blob, xyz: np.ndarray, h: np.ndarray, in_gauge: np.ndarray, vox: np.ndarray,
                         inv: np.ndarray, cfg: ClusterConfig) -> List[_Blob]:
    """The parts of an oversize cluster that stand in front of the smooth surface it lies on (13.10,
    ``structure_cut_tol``; judge 13.10 problem 2).

    On a curve the lagging far axis lays the tunnel wall diagonally across the envelope (70-150 m on
    roundT_pressureGate_roundT); an object there touches the wall within the DBSCAN radius (0.2-1.1 m at
    80-120 m: no thin bridge to cut, no gap in x or height, the strict-gauge points alone still one 23-40 m
    cluster) and the two are one cluster longer than ``max_extent``, dropped whole. The wall is a smooth
    surface: its lateral position is a function of the along-track distance and the height (the round
    tunnel's profile), ``y = a + b x + c x^2 + d h + e h^2`` in the vehicle frame, fitted robustly; the
    wall's own points stay within 0.1 m of it (robust spread 0.08-0.11 m), an object stands off it toward
    the sensor (it occludes the wall behind it; a niche behind the wall is not in front). The points at
    least ``structure_cut_tol`` in front of the surface are linked again at the corridor radius (their
    links to the surface cut); the parts at most ``oversize_split_max_length`` long along the track, not
    flatter than ``min_height`` and with points in the strict gauge are returned. Nothing is returned
    unless the cluster is such a surface: a robust spread of at most ``structure_cut_max_spread`` with at
    least ``structure_cut_min_fit`` of its points on it, running along the track (``_SURFACE_MAX_SLOPE``:
    within 45 deg of it, 14.10). Equipment fixed to the wall stands up to ~1.2 m
    in front of it, so the tolerance only separates an object well clear of the wall; nearer it the
    object and the wall equipment look alike and both stay dropped (configs/default.yaml). 14.10 (review):
    the tolerance is also more than the wall stands outside the strict envelope (C: 2.25-2.3 m from the
    axis, 1.05 m half width) - an object nearer the wall than that is outside the envelope, and where the
    far axis lags it was placed inside it. A part needs at least ``structure_cut_min_points`` voxels
    (14.10): the parts carved out of wall equipment on the empty recordings had 3-7. :func:`find_clusters`
    calls this only for a cluster the 25.09 split refused (:func:`_split_part`); a cluster without a
    strict-gauge point is not fitted. H2 (15.10): the part must also span one full sensor azimuth
    step (two resolved columns); vertically stacked voxels on one ray column are not a resolved body."""
    tol = float(cfg.structure_cut_tol)
    # every part needs a strict-gauge point: a cluster without one is not fitted (on the ride 7 890 of the
    # 14 141 clusters the split refused; the cut costs 0.43 ms per ride frame)
    if tol <= 0 or b.idx.size < _SURFACE_MIN_POINTS or not in_gauge[b.idx].any():
        return []
    x = b.pts[:, 0].astype(np.float64)
    y = b.pts[:, 1].astype(np.float64)
    u = (x - x.mean()) / 10.0
    fit = _surface_fit(u, h[b.idx].astype(np.float64), y, 0.5 * tol)
    if fit is None:
        return []
    coef, res, spread, on = fit
    if spread > cfg.structure_cut_max_spread or float(on.mean()) < cfg.structure_cut_min_fit:
        return []
    # the side the sensor sees the surface from: the ray to a point comes in from the side where y - y_w
    # has the sign of (surface slope - ray slope) (the slopes of the two lines in the horizontal plane).
    # The ray slope is the point's own: an object point near the tangent through the sensor (the
    # surface seen at grazing incidence) may get the far side and stay merged, a point behind the
    # surface never gets the near side
    slope = (coef[1] + 2.0 * coef[2] * u) / 10.0
    if float(np.abs(slope).max()) > _SURFACE_MAX_SLOPE:
        return []
    front = np.sign(slope - y / np.maximum(x, 1.0))
    off = res * front > tol
    if int(off.sum()) < cfg.min_samples or not in_gauge[b.idx[off]].any():
        return []
    idx = b.idx[off]
    vi, back = np.unique(inv[idx], return_inverse=True)
    if vi.size < max(cfg.structure_cut_min_points, cfg.min_samples):
        return []
    labels = dbscan_labels(_scaled(vox[vi], cfg.range_scale), cfg.eps, cfg.min_samples)[back.ravel()]
    parts = []
    for lab in np.unique(labels):
        pidx = idx[labels == lab]
        if lab < 0 or not in_gauge[pidx].any():
            continue
        part = _Blob.of(xyz, pidx, int(np.unique(inv[pidx]).size))
        # 14.10 (structure_cut_min_points): a few voxels picked off a surface of hundreds are weak
        # evidence; wall equipment gave parts of 3-7 voxels on the empty recordings, the objects 8-42
        if part.n_vox < cfg.structure_cut_min_points:
            continue
        # Physical horizontal support, independent of duplicate echoes and voxel
        # placement. A single vertical scan column can fill the voxel bar by itself.
        azimuth = np.arctan2(part.pts[:, 1].astype(np.float64), part.pts[:, 0].astype(np.float64))
        if float(np.ptp(azimuth)) < np.radians(AZIMUTH_STEP_DEG):
            continue
        if float(part.size[0]) <= cfg.oversize_split_max_length and float(part.size[2]) >= cfg.min_height:
            parts.append(part)
    return parts


def _surface_fit(u: np.ndarray, hh: np.ndarray, y: np.ndarray, band: float):
    """The robust fit of the structure cut (:func:`_off_structure_parts`): ``y = a + b u + c u^2 + d h + e h^2``
    by least squares, four times on the points within ``max(3 spread, band)`` of the previous fit
    (``spread`` = 1.4826 x the median absolute residual of the points it was fitted on). Returns
    ``(coef, res, spread, on)`` with the residuals of all points and the final inlier mask, or ``None``:
    fewer than ``_SURFACE_MIN_POINTS`` points (or inliers), a non-finite input, or a fit that does not
    converge. A surface that is not a function of (x, h) - a face across the track, a floor or roof
    strip, two walls - is not refused here: it fits badly, and the caller's spread and inlier tests
    refuse it (rank-deficient columns, e.g. a constant height, give the minimum-norm solution)."""
    if y.size < _SURFACE_MIN_POINTS or not (np.isfinite(u).all() and np.isfinite(hh).all() and np.isfinite(y).all()):
        return None
    A = np.stack([np.ones_like(u), u, u * u, hh, hh * hh], axis=1)
    on = np.ones(y.size, dtype=bool)
    coef = res = None
    spread = 0.0
    for _ in range(4):
        if int(on.sum()) < _SURFACE_MIN_POINTS:
            return None
        try:
            coef = np.linalg.lstsq(A[on], y[on], rcond=None)[0]
        except np.linalg.LinAlgError:
            return None
        res = y - A @ coef
        spread = 1.4826 * float(np.median(np.abs(res[on])))
        on = np.abs(res) <= max(3.0 * spread, band)
    if not (np.isfinite(coef).all() and np.isfinite(spread)):
        return None
    return coef, res, spread, on


def _corridor_cluster(b: _Blob, dy, h, in_gauge, intensity, inv, frame_idx, cfg: ClusterConfig,
                      factor: float, factor_range: float, axis_valid: float,
                      height_valid: Optional[float], gauge: Optional[GaugeConfig] = None,
                      dy_alt: Optional[np.ndarray] = None, in_rail: Optional[np.ndarray] = None,
                      keep_thin: bool = False, dy_report: Optional[np.ndarray] = None,
                      weak_from: float = 0.0, ring: Optional[np.ndarray] = None,
                      rays: Optional[FrameRays] = None) -> Optional[Cluster]:
    """A corridor cluster: size and point-count bars, the infrastructure shapes, then the zone
    (enough voxels in the strict gauge) and the reason that demotes it to advisory. ``in_rail``: the
    strict membership from the rails only (``find_clusters``). With ``keep_thin`` a cluster flatter
    than ``min_height`` is described with ``thin`` set instead of dropped (:func:`find_clusters`).
    ``rays``: the whole frame for the column signature's free-top test (:func:`find_clusters`)."""
    if in_rail is None:
        in_rail = in_gauge
    size = b.size
    if size.max() > cfg.max_extent and cfg.oversize_split_max_length > 0:
        part = _split_part(b, in_gauge, in_rail, inv, cfg)
        if part is None:
            return None
        b = part
        size = b.size
    thin = bool(size[2] < cfg.min_height)
    if size.max() > cfg.max_extent or (thin and not keep_thin):
        return None
    dist = float(b.pts[:, 0].min())
    min_pts = cfg.min_points if dist < cfg.far_range else cfg.min_points_far
    gauge_min = cfg.gauge_min_points
    if factor > 1.0 and dist >= factor_range:
        min_pts = int(np.ceil(min_pts * factor))
        gauge_min = int(np.ceil(gauge_min * factor))
    ring_count = 0
    if ring is not None and b.idx.size:
        current_gauge = b.idx[in_gauge[b.idx] & (frame_idx[b.idx] >= 0)]
        rr = ring[current_gauge]
        ring_count = int(np.unique(rr[rr >= 0]).size)
    weak = False
    if b.n_vox < min_pts:
        # 27.09 (cluster.weak_min_points, on): kept as weak far evidence (find_clusters)
        ordinary = (weak_from > 0 and cfg.weak_min_points > 0
                    and b.n_vox >= cfg.weak_min_points and dist >= weak_from)
        cross_ring = (weak_from > 0 and cfg.weak_min_rings > 0
                      and ring_count >= cfg.weak_min_rings
                      and b.n_vox >= cfg.weak_min_points_with_rings and dist >= weak_from)
        if not (ordinary or cross_ring):
            return None
        weak = True
    lateral = float(dy[b.idx].mean())
    h_max = float(h[b.idx].max())
    # 26.09 (gauge.axis_union 3, off by default): the shape rules read the lateral from the sensor
    # axis when that places the cluster nearer the centre (the envelope is the union of the two)
    lat_rules, dy_rules = lateral, dy
    if dy_alt is not None:
        lat_alt = float(dy_alt[b.idx].mean())
        if abs(lat_alt) < abs(lateral):
            lat_rules, dy_rules = lat_alt, dy_alt
    spare = False
    if cfg.wall_keep_gauge_voxels > 0 and dist <= cfg.wall_keep_distance:
        # 26.09 (P3 near escalation, candidate D): a tall cluster at the corridor side with this many
        # voxels inside the strict envelope near the train is not dropped as a wall (set O #6, the
        # 2 x 2 m box at the envelope edge: 10-31 such voxels at 14-8 m); the signatures still apply.
        # The voxels are counted in the envelope measured from the rails (in_rail; safety review of
        # 26.09: the wall keep does not change with gauge.axis_union)
        spare = int(np.unique(inv[b.idx][in_rail[b.idx]]).size) >= cfg.wall_keep_gauge_voxels
    # 27.09 (gauge.reference_along_rails, on): with the envelope measured from the sensor
    # axis, the rules for structure along the track (the linear infrastructure and the edge signature:
    # both need a cluster elongated along the track) read the lateral from the rails, which such
    # structure follows
    lat_along = None
    if dy_report is not None and gauge is not None and gauge.reference_along_rails:
        lat_along = float(dy_report[b.idx].mean())
    if _is_infrastructure(size, lat_rules, h_max, cfg, spare_wall=spare, lat_along=lat_along):
        return None
    wall_kept = spare and _is_infrastructure(size, lat_rules, h_max, cfg, lat_along=lat_along)
    n_gauge = int(np.unique(inv[b.idx][in_gauge[b.idx]]).size)
    zone = "gauge" if n_gauge >= gauge_min else "warning"
    free_top = None
    seen_free: List[bool] = []
    tall = cfg.column_free_tall_gap > 0 and h_max > cfg.column_free_max_top
    if (rays is not None and cfg.column_free_max_top > 0 and (h_max <= cfg.column_free_max_top or tall)
            and n_gauge >= cfg.column_free_min_core * b.n_vox):
        # 13.10: a column-shaped cluster mostly inside the envelope, its top under the envelope top, is a
        # column only if its top is not seen free (top_is_free; asked by the column rule alone). 14.10: the
        # answer is kept (Cluster.spared): the tracker does not let one such hit release a column hold
        # (tracking.column_free_min_spares). 15.10: the continuation over a window above the top
        # (column_free_window), and a cluster reaching the candidates' cut followed to its true top
        # (column_free_tall_gap)
        cur = frame_idx[b.idx]
        ask = partial(top_is_free, rays, cur[cur >= 0], cfg.column_free_min_returns,
                      window=cfg.column_free_window, vault_margin=cfg.column_free_vault_margin,
                      tall_gap=cfg.column_free_tall_gap if tall else 0.0)

        def free_top() -> bool:
            seen_free.append(bool(ask()))
            return seen_free[-1]
    reason = _advisory_reason(b, dist, lat_rules, zone, dy_rules, h, cfg, axis_valid, height_valid, lat_along,
                              free_top)
    demoted = zone == "gauge" and reason in SHAPE_SIGNATURES
    if reason:
        zone = "warning"
    retro = _is_retro(b, intensity, cfg)
    if retro:
        zone = "warning"
        reason = reason or "retro"
    n_exp, score = _visibility(b, max(float(size[1]), 0.15), max(float(size[2]), 0.15), cfg)
    fi = frame_idx[b.idx]
    if cfg.gauge_distance and zone == "gauge" and gauge is not None:
        # 25.09: an obstacle is as near as its part inside the envelope, not as a line at the
        # corridor edge it touches (set O: a conductor-rail line 3-8 m ahead of the box at 5-8 m).
        # Review 25.09: measured on the envelope widened by the axis-uncertainty margin, not on the
        # strict-gauge mask (shrunk by it: an oblique object was reported 0.3 / 0.55 / 1.2 m beyond
        # its entry at 40 / 80 / 120 m); never farther than the nearest point inside the envelope.
        # Without the gauge profile the nearest point of the cluster stays the distance.
        # 27.09 (gauge.reference): the reach is measured from the rail axis (dy_report), the strict
        # membership from the reference: never farther than where the object enters either
        dyr = dy if dy_report is None else dy_report
        reach = in_gauge[b.idx] | gauge_reach_mask(dyr[b.idx], h[b.idx], b.pts[:, 0], gauge)
        if reach.any():
            dist = float(b.pts[reach, 0].min())
    if dy_report is not None:
        # 27.09 (gauge.reference 1): the reported lateral stays the one from the rail axis
        lateral = float(dy_report[b.idx].mean())
    return Cluster(
        points_idx=fi[fi >= 0], n=b.n_vox, n_raw=int(b.idx.size), centroid=b.pts.mean(axis=0),
        bbox_min=b.bmin, bbox_max=b.bmax, distance=dist, lateral=lateral,
        height_min=float(h[b.idx].min()), height_max=h_max,
        intensity=float(intensity[b.idx].mean()) if intensity is not None else 0.0,
        n_expected=n_exp, score=score, zone=zone, n_gauge=n_gauge, retro=retro, reason=reason,
        wall_kept=wall_kept, demoted=demoted and not retro, thin=thin, weak=weak,
        ring_count=ring_count, spared=bool(seen_free and seen_free[-1]),
    )
