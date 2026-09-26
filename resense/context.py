"""D1 candidate: recover compact-object context lost by the corridor crop.

The fixed experiment is registered in quality_cycle_2026-09-26_D1_protocol.json.
Context can promote existing supported candidates; it never suppresses an existing one.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

import numpy as np

from resense.clustering import (
    _Blob, _advisory_reason, _is_infrastructure, _is_retro, cluster_labels, voxelize,
)


def compact_context(cluster, xyz, intensity, dy, height, cfg, axis_valid, height_valid):
    """Return (accepted, reason) without modifying the candidate or the input cloud."""
    if cluster.kind or cluster.retro or cluster.reason not in ("", "floating", "elevated"):
        return False, "excluded_kind_or_reason"
    if not cluster.thin and cluster.reason not in ("floating", "elevated"):
        return False, "already_ordinary"
    if cluster.n_gauge < cfg.gauge_min_points:
        return False, "insufficient_original_strict_support"
    if cluster.distance > min(axis_valid, height_valid):
        return False, "unsupported_geometry"
    seed = np.unique(cluster.points_idx)
    if not len(seed) or seed.min() < 0 or seed.max() >= len(xyz):
        return False, "no_current_seed"
    limit = float(cfg.oversize_split_max_length)
    if limit <= 0:
        return False, "compact_bound_disabled"
    points = xyz[seed]
    radius = float(np.linalg.norm(points, axis=1).max()) + np.sqrt(3.0) * limit
    scale = float(cfg.range_scale)
    epsilon = float(cfg.eps) + 2.0 * np.sqrt(3.0) * float(cfg.voxel)
    normalized_radius = radius / (1.0 + radius / scale)
    if normalized_radius + epsilon >= scale:
        return False, "unbounded_query"
    reach = epsilon / (1.0 - (normalized_radius + epsilon) / scale) ** 2
    lower, upper = points.min(axis=0) - (limit + reach), points.max(axis=0) + (limit + reach)
    ids = np.flatnonzero(((xyz >= lower) & (xyz <= upper)).all(axis=1))
    local_seed = np.searchsorted(ids, seed)
    if np.any(local_seed >= len(ids)) or not np.array_equal(ids[local_seed], seed):
        return False, "seed_outside_query"
    voxels, inverse = voxelize(xyz[ids], cfg)
    labels = cluster_labels(voxels, cfg)
    seed_labels = labels[inverse[local_seed]]
    if np.any(seed_labels < 0) or np.unique(seed_labels).size != 1:
        return False, "fragmented_or_noise_seed"
    selected = labels[inverse] == seed_labels[0]
    component_ids = ids[selected]
    component = xyz[component_ids]
    size = np.ptp(component, axis=0)
    if float(size.max()) > min(limit, float(cfg.max_extent)):
        return False, "extended_component"
    if np.any(component - lower <= reach) or np.any(upper - component <= reach):
        return False, "query_boundary"
    if size[2] < cfg.min_height:
        return False, "context_still_thin"
    lateral = dy[component_ids]
    heights = height[component_ids]
    mean_lateral, max_height = float(lateral.mean()), float(heights.max())
    if _is_infrastructure(size, mean_lateral, max_height, cfg):
        return False, "full_context_infrastructure"
    blob = _Blob.of(component, np.arange(len(component)), int(np.unique(inverse[selected]).size))
    if _is_retro(blob, intensity[component_ids], cfg):
        return False, "full_context_retro"
    reason = _advisory_reason(blob, cluster.distance, mean_lateral, "gauge", lateral, heights,
                              cfg, axis_valid, height_valid)
    if reason not in ("", "floating", "elevated"):
        return False, "full_context_" + reason
    return True, "compact_full_context"


def restore_context(clusters, thin, xyz, intensity, dy, height, cfg, axis_valid, height_valid,
                    accumulation_count=1):
    """Promote the fixed eligible subset; preserve every other cluster object unchanged."""
    stats = Counter()
    if accumulation_count != 1:
        return clusters, thin, {"accumulated_frame_unchanged": 1}
    outputs, remaining = [], []
    for candidates, destination in ((clusters, outputs), (thin, remaining)):
        for cluster in candidates:
            # The cheap eligibility checks precede any full-cloud query.
            if not cluster.thin and cluster.reason not in ("floating", "elevated"):
                destination.append(cluster)
                continue
            accepted, reason = compact_context(cluster, xyz, intensity, dy, height, cfg,
                                                axis_valid, height_valid)
            stats[reason] += 1
            if accepted:
                outputs.append(replace(cluster, thin=False, zone="gauge", reason="", demoted=False))
            else:
                destination.append(cluster)
    return outputs, remaining, dict(stats)
