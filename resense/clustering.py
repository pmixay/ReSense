"""Range-adaptive clustering of corridor candidates and cluster descriptors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from resense.config import ClusterConfig, GaugeConfig
from resense.gauge import gauge_reach_mask
from resense.sensor import expected_points


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

    @property
    def size(self) -> np.ndarray:
        return self.bbox_max - self.bbox_min


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
                  height_valid: Optional[float] = None, gauge: Optional[GaugeConfig] = None) -> List[Cluster]:
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
    """
    out: List[Cluster] = []
    if xyz.shape[0] == 0:
        return out
    if frame_idx is None:
        frame_idx = np.arange(xyz.shape[0])
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
            c = _low_cluster(b, dy, h, intensity, frame_idx, cfg, low_cfg)
        else:
            c = _corridor_cluster(b, dy, h, in_gauge, intensity, inv, frame_idx, cfg, factor, factor_range,
                                  axis_valid, height_valid, gauge)
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


def _low_cluster(b: _Blob, dy, h, intensity, frame_idx, cfg: ClusterConfig, low_cfg) -> Optional[Cluster]:
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
    if low_cfg.min_top > -1.0 and float(h[b.idx].max()) < low_cfg.min_top:
        return None
    n_exp, score = _visibility(b, max(float(size[1]), 0.15), max(float(size[2]), 0.1), cfg)
    fi = frame_idx[b.idx]
    return Cluster(
        points_idx=fi[fi >= 0], n=b.n_vox, n_raw=int(b.idx.size), centroid=b.pts.mean(axis=0),
        bbox_min=b.bmin, bbox_max=b.bmax, distance=float(b.pts[:, 0].min()), lateral=float(dy[b.idx].mean()),
        height_min=float(h[b.idx].min()), height_max=float(h[b.idx].max()),
        intensity=float(intensity[b.idx].mean()) if intensity is not None else 0.0,
        n_expected=n_exp, score=score, zone="gauge", n_gauge=b.n_vox, kind="low",
    )


def _is_infrastructure(size: np.ndarray, lateral: float, h_max: float, cfg: ClusterConfig) -> bool:
    """Shapes dropped outright: linear infrastructure along the track (rails, pipes, cables,
    duct edges), low narrow track hardware, wall-like structure at the side, a tall long narrow
    wall segment that a mis-estimated axis pulled into the corridor, and long linear structure
    at the side (platform edge, duct, cabinet row)."""
    if size[0] > cfg.thin_min_length and size[1] < cfg.thin_max_width and size[2] < cfg.thin_max_height:
        return True
    # rail clamps, cables, joint bars — tune with injected data
    if h_max < cfg.hardware_max_top and size[1] < cfg.hardware_max_width and size[2] < cfg.hardware_max_height:
        return True
    if size[2] > cfg.wall_min_height and abs(lateral) > cfg.wall_min_lateral:
        return True
    if size[2] > cfg.wall_min_height and size[0] > cfg.wall_segment_min_length and size[1] < cfg.wall_segment_max_width:
        return True
    return (size[0] > cfg.linear_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.linear_max_height
            and abs(lateral) > cfg.linear_min_lateral)


def _advisory_reason(b: _Blob, dist: float, lateral: float, zone: str, dy, h, cfg: ClusterConfig,
                     axis_valid: float, height_valid: Optional[float]) -> str:
    """Why a cluster is advisory although it may have gauge voxels ('' = it is an obstacle):
    beyond the range where the axis or the height reference is supported, hanging entirely in
    the top zone (cables, lamps), or a v0.5 infrastructure signature (EXPERIMENTS.md 1b)."""
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
    if cfg.column_min_height > 0 and size[2] > cfg.column_min_height and size[1] < cfg.column_max_width \
            and (off_centre or size[1] >= cfg.column_min_width):
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
    if cfg.floating_min_height > 0 and h_min > cfg.floating_min_height and size[2] < cfg.floating_max_height \
            and size[1] < cfg.floating_max_width and (off_centre or along):
        return "" if short else "floating"   # sign, lamp, bracket: small and not touching the ground
    if cfg.edge_min_lateral > 0 and abs(lateral) > cfg.edge_min_lateral \
            and size[0] > cfg.edge_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.edge_max_height:
        return "edge"                      # duct / bench / platform-edge fragment along the corridor edge
    if cfg.wall_face_min_height > 0 and size[2] > cfg.wall_face_min_height and h_max > cfg.wall_face_min_top:
        below = hh < cfg.wall_face_min_top
        if below.sum() >= 3 and ady[below].min() > cfg.wall_face_min_inner and ady[below].max() > cfg.wall_face_edge:
            return "wall_face"             # wall / portal face pulled in by the axis: hugs the edge, centre clear
    return ""


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


def _corridor_cluster(b: _Blob, dy, h, in_gauge, intensity, inv, frame_idx, cfg: ClusterConfig,
                      factor: float, factor_range: float, axis_valid: float,
                      height_valid: Optional[float], gauge: Optional[GaugeConfig] = None) -> Optional[Cluster]:
    """A corridor cluster: size and point-count bars, the infrastructure shapes, then the zone
    (enough voxels in the strict gauge) and the reason that demotes it to advisory."""
    size = b.size
    if size.max() > cfg.max_extent and cfg.oversize_split_max_length > 0:
        b = _gauge_part(b, in_gauge, inv, cfg)
        if b is None:
            return None
        size = b.size
    if size.max() > cfg.max_extent or size[2] < cfg.min_height:
        return None
    dist = float(b.pts[:, 0].min())
    min_pts = cfg.min_points if dist < cfg.far_range else cfg.min_points_far
    gauge_min = cfg.gauge_min_points
    if factor > 1.0 and dist >= factor_range:
        min_pts = int(np.ceil(min_pts * factor))
        gauge_min = int(np.ceil(gauge_min * factor))
    if b.n_vox < min_pts:
        return None
    lateral = float(dy[b.idx].mean())
    h_max = float(h[b.idx].max())
    if _is_infrastructure(size, lateral, h_max, cfg):
        return None
    n_gauge = int(np.unique(inv[b.idx][in_gauge[b.idx]]).size)
    zone = "gauge" if n_gauge >= gauge_min else "warning"
    reason = _advisory_reason(b, dist, lateral, zone, dy, h, cfg, axis_valid, height_valid)
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
        reach = in_gauge[b.idx] | gauge_reach_mask(dy[b.idx], h[b.idx], b.pts[:, 0], gauge)
        if reach.any():
            dist = float(b.pts[reach, 0].min())
    return Cluster(
        points_idx=fi[fi >= 0], n=b.n_vox, n_raw=int(b.idx.size), centroid=b.pts.mean(axis=0),
        bbox_min=b.bmin, bbox_max=b.bmax, distance=dist, lateral=lateral,
        height_min=float(h[b.idx].min()), height_max=h_max,
        intensity=float(intensity[b.idx].mean()) if intensity is not None else 0.0,
        n_expected=n_exp, score=score, zone=zone, n_gauge=n_gauge, retro=retro, reason=reason,
    )
