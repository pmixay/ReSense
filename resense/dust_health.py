"""Experimental diffuse-return evidence; never an identification of physical dust.

No points are removed. Under a broad volumetric-clutter signal, a multi-return,
uniformly dim cluster without local spatial support can be marked advisory before
tracking. Sparse/strong/held evidence is protected. The intensity ceiling is an
explicit sensor-specific assumption; callers must not infer it for a new sensor.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def diffuse_evidence(xyz, intensity, dy, h, axis_valid, intensity_max=5.0):
    end = min(60.0, float(axis_valid))
    bins_x = max(0, int((end - 5.0) // 5.0)) if np.isfinite(end) else 0
    end = 5.0 + bins_x * 5.0
    x = xyz[:, 0]
    take = ((x >= 5.0) & (x < end) & (abs(dy) < 1.0) & (h >= .3) & (h < 2.7)
            & np.isfinite(intensity) & (intensity <= intensity_max))
    coords = np.column_stack((x[take], dy[take], h[take]))
    keys = np.floor((coords - [5.0, -1.0, .3]) / [5.0, .5, .5]).astype(np.int64)
    occupied = np.unique(keys, axis=0)
    fraction = len(occupied) / max(1, bins_x * 4 * 5)
    stations = int(np.unique(occupied[:, 0]).size) if len(occupied) else 0
    return {"active": bool(fraction >= .45 and stations >= 6),
            "occupied_fraction": float(fraction), "stations": stations,
            "low_intensity_returns": int(take.sum()), "examined_range": end,
            "intensity_ceiling": float(intensity_max), "identity": "diffuse_returns_not_dust_classification"}


def mark_unsupported_clusters(clusters, xyz, intensity, dy, h, evidence, intensity_max=5.0):
    """Mark unsupported dim clusters advisory, preserving every input point/cluster.

    A1/A2: up to three unique current returns are ambiguous sparse objects and protected.
    A3: any strong original return protects a cluster before spatial deduplication.
    A4: no current return means held/accumulated evidence, not evidence of absence.
    The caller must report degraded health and zero certified range while active.
    """
    result = {"marked": 0, "protected_sparse": 0, "protected_surface": 0, "protected_strong": 0,
              "protected_held": 0, "protected_outside": 0, "cluster_support": []}
    if not evidence["active"] or not clusters:
        return result
    roi = ((xyz[:, 0] > 2.5) & (xyz[:, 0] < 100.0) & (abs(dy) < 5.0)
           & (h > -.5) & (h < 5.0))
    pts = xyz[roi]
    if not len(pts):
        return result
    _, unique = np.unique(np.round(pts / .03).astype(np.int64), axis=0, return_index=True)
    tree = cKDTree(pts[unique])
    for cl in clusters:
        if cl.zone != "gauge":
            continue
        idx = np.asarray(cl.points_idx)
        idx = idx[(idx >= 0) & (idx < len(xyz))].astype(np.int64)
        if not len(idx):
            result["protected_held"] += 1
            continue
        # A near clutter field does not explain sparse evidence farther ahead.
        if np.any((xyz[idx, 0] < 5.0) | (xyz[idx, 0] >= evidence.get("examined_range", 60.0))):
            result["protected_outside"] += 1
            continue
        # Examine all original echoes before dedup; input order cannot hide a strong echo.
        if np.any(intensity[idx] > intensity_max) or not np.isfinite(intensity[idx]).all():
            result["protected_strong"] += 1
            continue
        raw = xyz[idx]
        _, distinct = np.unique(np.round(raw / .03).astype(np.int64), axis=0, return_index=True)
        raw = raw[distinct]
        if len(raw) <= 3:
            result["protected_sparse"] += 1
            continue
        # A thin cable or a sampled surface can be real despite widely spaced rays.
        # Protect line/plane support, including diagonal wires, rather than requiring
        # a dense blob. Four noncoplanar points are the minimum volumetric evidence.
        centered = raw - raw.mean(axis=0)
        _, _, vectors = np.linalg.svd(centered, full_matrices=False)
        plane_error = np.max(np.abs(centered @ vectors[-1]))
        if plane_error <= .10:
            result["protected_surface"] += 1
            continue
        radius = .15 + np.linalg.norm(raw, axis=1) * np.tan(np.radians(.2))
        neighbors = tree.query_ball_point(raw, radius, return_length=True)
        supported = int((neighbors >= 3).sum())
        result["cluster_support"].append({"distance": float(cl.distance), "distinct": len(raw),
                                         "supported": supported})
        if supported < 2:
            cl.zone, cl.reason, cl.demoted = "warning", "diffuse_low_support", False
            result["marked"] += 1
    return result


def mark_degraded_health(health, evidence, support):
    """Retain severity and STOP evidence while declining clear/monitored range claims."""
    out = dict(health)
    out["diffuse_returns"] = {**evidence, **support}
    if evidence["active"]:
        out["level"] = "error" if out.get("level") == "error" else "warn"
        out["decision_level"] = "error" if out.get("decision_level") == "error" else "warn"
        out["messages"] = list(out.get("messages", [])) + [
            "diffuse low-intensity volumetric returns: visibility degraded; range unverified"]
        out["monitored_range"] = out["clear_distance"] = 0.0
    return out
