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
                  smear_max_length: float = 0.0) -> List[Cluster]:
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
    ``max_extent`` rule.
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
        if smear_max_length > 0 and size[0] > smear_max_length and (frame_idx[idx] < 0).any():
            idx = idx[frame_idx[idx] >= 0]
            if idx.size == 0:
                continue
            n_vox = int(np.unique(inv[idx]).size)
            pts = xyz[idx]
            bmin, bmax = pts.min(axis=0), pts.max(axis=0)
            size = bmax - bmin
            factor = 1.0
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
        # beyond the range where the axis is supported by observed tunnel boundaries, or
        # hanging entirely in the top zone (cables, lamps): advisory only
        if dist > axis_valid or h_min > cfg.overhead_min_height:
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
            n_expected=n_exp, score=score, zone=zone, n_gauge=n_gauge, retro=retro,
        ))
    out.sort(key=lambda c: c.distance)
    return out
