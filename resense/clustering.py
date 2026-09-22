"""Range-adaptive clustering of corridor candidates and cluster descriptors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
from sklearn.cluster import DBSCAN

from resense.config import ClusterConfig
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


def cluster_labels(xyz: np.ndarray, cfg: ClusterConfig) -> np.ndarray:
    """DBSCAN in range-normalised coordinates so that eps grows linearly with range.

    p' = p / (1 + r / range_scale)  =>  eps_metric(r) = eps * (1 + r / range_scale)
    """
    if xyz.shape[0] == 0:
        return np.zeros(0, dtype=int)
    p = _scaled(xyz, cfg.range_scale)
    return DBSCAN(eps=cfg.eps, min_samples=cfg.min_samples, algorithm="kd_tree").fit_predict(p)


def find_clusters(xyz: np.ndarray, intensity: np.ndarray, dy: np.ndarray, h: np.ndarray,
                  in_gauge: np.ndarray, cfg: ClusterConfig,
                  frame_idx: Optional[np.ndarray] = None, axis_valid: float = 1e9,
                  min_points_factor: float = 1.0, factor_range: float = 0.0,
                  smear_max_length: float = 0.0, smear_max_width: float = 0.0,
                  low: Optional[np.ndarray] = None, low_cfg=None,
                  height_valid: Optional[float] = None) -> List[Cluster]:
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
    axis is an obstacle whatever its shape (organizers' Q&A: hanging cables must be detected).

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
        idx = np.flatnonzero(labels == lab)
        n_vox = int((vlabels == lab).sum())
        pts = xyz[idx]
        bmin, bmax = pts.min(axis=0), pts.max(axis=0)
        size = bmax - bmin
        factor = min_points_factor
        merged = smear_max_length > 0 and (frame_idx[idx] < 0).any()
        if merged and (size[0] > smear_max_length or (smear_max_width > 0 and size[1] > smear_max_width)):
            idx = idx[frame_idx[idx] >= 0]
            if idx.size == 0:
                continue
            n_vox = int(np.unique(inv[idx]).size)
            pts = xyz[idx]
            bmin, bmax = pts.min(axis=0), pts.max(axis=0)
            size = bmax - bmin
            factor = 1.0
        is_low = low is not None and low_cfg is not None and bool(low[idx].mean() >= 0.5)
        if is_low:
            if (size[0] > low_cfg.max_length or size[1] > low_cfg.max_width or size[2] < low_cfg.min_height
                    or n_vox < low_cfg.min_points):
                continue
            # rail-head slivers, fastenings and joint bars are narrow across the track; a 30 cm object is not
            if size[1] < low_cfg.min_width:
                continue
            dist = float(pts[:, 0].min())
            width = max(float(size[1]), 0.15)
            height = max(float(size[2]), 0.1)
            n_exp = float(expected_points(np.linalg.norm(pts.mean(axis=0)), width, height))
            score = float(np.clip(n_vox / max(n_exp, 1.0) / cfg.visibility_ratio, 0.0, 1.0)) if n_exp > 1.0 else 1.0
            fi = frame_idx[idx]
            out.append(Cluster(
                points_idx=fi[fi >= 0], n=n_vox, n_raw=int(idx.size), centroid=pts.mean(axis=0),
                bbox_min=bmin, bbox_max=bmax, distance=dist, lateral=float(dy[idx].mean()),
                height_min=float(h[idx].min()), height_max=float(h[idx].max()),
                intensity=float(intensity[idx].mean()) if intensity is not None else 0.0,
                n_expected=n_exp, score=score, zone="gauge", n_gauge=n_vox, kind="low",
            ))
            continue
        if size.max() > cfg.max_extent or size[2] < cfg.min_height:
            continue
        dist = float(pts[:, 0].min())
        min_pts = cfg.min_points if dist < cfg.far_range else cfg.min_points_far
        gauge_min = cfg.gauge_min_points
        if factor > 1.0 and dist >= factor_range:
            min_pts = int(np.ceil(min_pts * factor))
            gauge_min = int(np.ceil(gauge_min * factor))
        if n_vox < min_pts:
            continue
        # linear infrastructure along the track: rails, pipes, cables, duct edges
        if size[0] > cfg.thin_min_length and size[1] < cfg.thin_max_width and size[2] < cfg.thin_max_height:
            continue
        lateral = float(dy[idx].mean())
        h_max = float(h[idx].max())
        # low, narrow track hardware (rail clamps, cables, joint bars) — tune with injected data
        if h_max < cfg.hardware_max_top and size[1] < cfg.hardware_max_width and size[2] < cfg.hardware_max_height:
            continue
        # wall-like structure at the side (columns, gate frames, platform walls) or a tall,
        # long, narrow wall segment that a mis-estimated axis pulled into the corridor
        if size[2] > cfg.wall_min_height and abs(lateral) > cfg.wall_min_lateral:
            continue
        if size[2] > cfg.wall_min_height and size[0] > cfg.wall_segment_min_length and size[1] < cfg.wall_segment_max_width:
            continue
        # long linear structure along the track at the side (platform edge, duct, cabinet row)
        if (size[0] > cfg.linear_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.linear_max_height
                and abs(lateral) > cfg.linear_min_lateral):
            continue
        n_gauge = int(np.unique(inv[idx][in_gauge[idx]]).size)
        zone = "gauge" if n_gauge >= gauge_min else "warning"
        h_min = float(h[idx].min())
        reason = ""
        # beyond the range where the axis is supported by observed tunnel boundaries, or
        # hanging entirely in the top zone (cables, lamps): advisory only
        if dist > axis_valid:
            reason = "beyond_axis"
        elif height_valid is not None and dist > height_valid and (
                size[2] < cfg.far_min_height or size[0] > cfg.far_max_length or float(h[idx].min()) > cfg.far_max_bottom):
            reason = "beyond_height_ref"
        elif h_min > cfg.overhead_min_height:
            reason = "overhead"
        elif zone == "gauge":
            # v0.5 infrastructure signatures (measured on the organizer bags, EXPERIMENTS.md 1b)
            hh = h[idx]
            ady = np.abs(dy[idx])
            off_centre = abs(lateral) > cfg.signature_min_lateral
            if cfg.column_min_height > 0 and size[2] > cfg.column_min_height and size[1] < cfg.column_max_width \
                    and (off_centre or size[1] >= cfg.column_min_width):
                reason = "column"                  # column, post, gate leg: taller than any listed object, narrow
            elif cfg.elevated_min_height > 0 and h_min > cfg.elevated_min_height and size[1] > cfg.elevated_min_width:
                reason = "elevated"                # beam / roof strip / gantry spanning the corridor above the rails
            elif cfg.floating_min_height > 0 and h_min > cfg.floating_min_height and size[2] < cfg.floating_max_height \
                    and size[1] < cfg.floating_max_width and off_centre:
                reason = "floating"                # sign, lamp, bracket: small and not touching the ground
            elif cfg.edge_min_lateral > 0 and abs(lateral) > cfg.edge_min_lateral \
                    and size[0] > cfg.edge_min_aspect * max(float(size[1]), 0.05) and size[2] < cfg.edge_max_height:
                reason = "edge"                    # duct / bench / platform-edge fragment along the corridor edge
            elif cfg.wall_face_min_height > 0 and size[2] > cfg.wall_face_min_height and h_max > cfg.wall_face_min_top:
                low = hh < cfg.wall_face_min_top
                if low.sum() >= 3 and ady[low].min() > cfg.wall_face_min_inner and ady[low].max() > cfg.wall_face_edge:
                    reason = "wall_face"           # wall / portal face pulled in by the axis: hugs the edge, centre clear
        if reason:
            zone = "warning"
        mean_int = float(intensity[idx].mean()) if intensity is not None else 0.0
        # retro-reflective plate / sign / marker: intensity is reflectivity %, > 100 only from
        # retro-reflective material; small and low -> infrastructure, advisory only. A person
        # in a hi-vis vest is taller, a train ahead is larger: both keep their zone.
        retro = False
        if cfg.retro_intensity > 0 and intensity is not None and idx.size:
            frac = float((intensity[idx] >= cfg.retro_intensity).mean())
            if (frac >= cfg.retro_min_fraction and size[2] < cfg.retro_max_height
                    and size[1] < cfg.retro_max_width):
                retro = True
                zone = "warning"
                reason = reason or "retro"
        width = max(float(size[1]), 0.15)
        height = max(float(size[2]), 0.15)
        n_exp = float(expected_points(np.linalg.norm(pts.mean(axis=0)), width, height))
        vis = n_vox / max(n_exp, 1.0)
        score = float(np.clip(vis / cfg.visibility_ratio, 0.0, 1.0)) if n_exp > 1.0 else 1.0
        fi = frame_idx[idx]
        out.append(Cluster(
            points_idx=fi[fi >= 0], n=n_vox, n_raw=int(idx.size), centroid=pts.mean(axis=0),
            bbox_min=bmin, bbox_max=bmax, distance=dist, lateral=lateral,
            height_min=h_min, height_max=h_max, intensity=mean_int,
            n_expected=n_exp, score=score, zone=zone, n_gauge=n_gauge, retro=retro, reason=reason,
        ))
    out.sort(key=lambda c: c.distance)
    return out
