#!/usr/bin/env python3
"""Measure voxel collapse and physical neighbor bridges without running the detector.

Uses organizer source identities from the 15–80 m fixture and serialized historical track
geometry. This is a conditional corridor diagnostic, not a historical/current replay or
candidate STOP score. Production modules are imported read-only.
"""
from __future__ import annotations

import argparse
from dataclasses import fields
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resense import _native  # noqa: E402
from resense.clustering import _scaled, voxelize  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.track import TrackModel  # noqa: E402
from scripts.cache_io import load_cache_array  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_fixture_indices(frame, source):
    """Exact XYZ/intensity cache-quantized multiset; fixture has no ring information.

    Extra identical copies are reported. A missing return is fatal, never nearest-matched.
    Default sensor mapping is a signed axis permutation, so XYZ quantization commutes.
    """
    def keys(xyz, intensity):
        a = np.column_stack((np.rint(xyz / np.float32(.01)),
                             np.clip(np.rint(intensity), 0, 255))).astype(np.int32)
        return np.ascontiguousarray(a).view(np.dtype((np.void, 16))).ravel()

    cache = keys(frame.xyz, frame.intensity)
    source = keys(source[:, :3], source[:, 3])
    order = np.argsort(cache)
    ordered = cache[order]
    ids, extras = [], 0
    unique, counts = np.unique(source, return_counts=True)
    for key, n in zip(unique, counts):
        lo, hi = np.searchsorted(ordered, key, side="left"), np.searchsorted(ordered, key, side="right")
        if hi - lo < n:
            raise ValueError("fixture return missing from exact XYZ/intensity multiset")
        ids.extend(order[lo:lo + n].tolist())
        extras += int(hi - lo - n)
    return np.asarray(ids, dtype=np.int64), extras


def radial_refinement(xyz, cfg):
    """Subdivide existing voxels by log-range; never merge formerly distinct cells.

    d[R log(1+r/R)]/dr = 1/(1+r/R), the intended linear local radial scale.
    This diagnostic changes no production voxelizer.
    """
    base = np.floor(_scaled(xyz, cfg.range_scale) / cfg.voxel).astype(np.int64)
    rho = cfg.range_scale * np.log1p(np.linalg.norm(xyz, axis=1) / cfg.range_scale)
    keys = np.column_stack((base, np.floor(rho / cfg.voxel).astype(np.int64)))
    _, inv = np.unique(keys, axis=0, return_inverse=True)
    inv = inv.ravel()
    n = int(inv.max()) + 1 if len(inv) else 0
    sums = np.zeros((n, 3), np.float64)
    np.add.at(sums, inv, xyz)
    counts = np.bincount(inv, minlength=n)
    return (sums / counts[:, None]).astype(np.float32), inv


def neighbor_pairs(vox, cfg):
    """Production transformed-radius neighbors and a conservative physical-edge filter."""
    p = np.asarray(_scaled(vox, cfg.range_scale), dtype=np.float64)
    pairs = cKDTree(p).query_pairs(cfg.eps * (1 + 1e-6), output_type="ndarray")
    d = p[pairs[:, 0]] - p[pairs[:, 1]]
    d2 = d[:, 0] * d[:, 0]
    d2 = d2 + d[:, 1] * d[:, 1]
    d2 = d2 + d[:, 2] * d[:, 2]
    pairs = pairs[d2 <= cfg.eps * cfg.eps]
    a, b = pairs.T
    r = np.linalg.norm(vox.astype(np.float64), axis=1)
    distance = np.linalg.norm(vox[a].astype(np.float64) - vox[b], axis=1)
    bound = cfg.eps * (1 + np.minimum(r[a], r[b]) / cfg.range_scale)
    return pairs, distance, bound, np.abs(r[a] - r[b])


def connected_target_background(n, pairs, target_voxels, background_counts):
    """All neighbor connectivity, before DBSCAN core tests; explicitly not detections."""
    if not len(target_voxels):
        return 0
    graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    _, labels = connected_components(graph, directed=False)
    reached = np.isin(labels, labels[target_voxels])
    return int(background_counts[reached].sum())


def measure(xyz, target, strict, cfg, refine=False):
    xyz = np.asarray(xyz, dtype=np.float32)
    target, strict = np.asarray(target, bool), np.asarray(strict, bool)
    if not len(xyz):
        return {"raw_points": 0, "target_raw": 0, "voxels": 0, "target_voxels": 0}
    vox, inv = radial_refinement(xyz, cfg) if refine else voxelize(xyz, cfg)
    n = len(vox)
    nt = np.bincount(inv[target], minlength=n)
    nb = np.bincount(inv[~target], minlength=n)
    tv = np.flatnonzero(nt)
    pairs, distance, bound, radial = neighbor_pairs(vox, cfg)
    a, b = pairs.T
    # Edges incident to a source-occupied voxel; mixed cells cannot isolate provenance.
    incident = (nt[a] > 0) | (nt[b] > 0)
    bridge = ((nt[a] > 0) & (nb[b] > 0)) | ((nt[b] > 0) & (nb[a] > 0))
    excess = distance > bound
    raw_r = np.linalg.norm(xyz.astype(np.float64), axis=1)
    lo, hi = np.full(n, np.inf), np.full(n, -np.inf)
    np.minimum.at(lo, inv, raw_r)
    np.maximum.at(hi, inv, raw_r)
    records = []
    for j in np.flatnonzero(incident & excess):
        records.append({"voxel_pair": pairs[j].tolist(), "distance_m": float(distance[j]),
                        "radial_gap_m": float(radial[j]), "linear_bound_m": float(bound[j]),
                        "background_bridge": bool(bridge[j])})
    return {"raw_points": len(xyz), "target_raw": int(target.sum()), "voxels": n,
            "target_voxels": len(tv), "target_strict_voxels": len(np.unique(inv[target & strict])),
            "target_mixed_voxels": int(((nt > 0) & (nb > 0)).sum()),
            "target_cell_max_radial_span_m": float((hi[tv] - lo[tv]).max()) if len(tv) else 0,
            "neighbor_edges": len(pairs), "edges_above_linear_bound": int(excess.sum()),
            "source_background_edges": int(bridge.sum()),
            "source_background_edges_above_linear_bound": int((bridge & excess).sum()),
            "connected_background_raw_baseline_graph": connected_target_background(n, pairs, tv, nb),
            "connected_background_raw_bounded_graph": connected_target_background(n, pairs[~excess], tv, nb),
            "source_incident_excess_edges": records}


def run(args):
    trace_path = Path(args.trace)
    with gzip.open(trace_path, "rt") if trace_path.suffix == ".gz" else open(trace_path) as stream:
        history = json.load(stream)
    manifest = json.loads((Path(args.fixture).parent / "manifest.json").read_text())
    if sha(args.fixture) != manifest["points_sha256"]:
        raise ValueError("source fixture SHA256 differs from extraction manifest")
    fixture = np.load(args.fixture, allow_pickle=False)
    cfg = DetectorConfig()
    detector = Detector(cfg)
    allowed = {f.name for f in fields(TrackModel)}
    requested = set(map(int, args.frames.split(","))) if args.frames else None
    rows = []
    for row in history["frames"]:
        k = int(row["frame"])
        if requested is not None and k not in requested:
            continue
        key = f"{args.object}_{k}"
        if key not in fixture:
            continue
        path = Path(args.cache) / f"cloud_with_fake_obj_{k:04d}.npy"
        if not path.exists():
            path = Path(str(path) + ".zst")
        frame = frame_from_compact(load_cache_array(path), cfg.sensor)
        source = fixture[key]
        ids, ambiguous = exact_fixture_indices(frame, source)
        detector.track = TrackModel(**{key: value for key, value in row["trace"]["track"].items() if key in allowed})
        cand = detector._corridor(frame.xyz, frame.intensity)[0]
        target = np.isin(cand.idx, ids)
        rows.append({"frame": k, "source_points": len(source), "indistinguishable_extra_copies": ambiguous,
                     "cache_sha256": sha(path),
                     "historical_track": row["trace"]["track"],
                     "historical_track_sha256": hashlib.sha256(json.dumps(
                         row["trace"]["track"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                     "source_distance_m": float(source[:, 0].min()) if len(source) else None,
                     "baseline_voxels": measure(cand.xyz, target, cand.in_gauge, cfg.cluster),
                     "radially_refined_voxels": measure(cand.xyz, target, cand.in_gauge, cfg.cluster, True)})
        if args.limit and len(rows) >= args.limit:
            break
    if not rows:
        raise ValueError("no requested trace frames overlap the organizer source fixture")
    return {"mode": "historical_geometry_conditional_corridor", "native": _native.status(),
            "object": args.object, "trace_sha256": sha(trace_path), "fixture_sha256": sha(args.fixture),
            "observer_sha256": sha(__file__),
            "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "resense").glob("*.py"))},
            "limitations": ["Trace geometry is serialized/rounded from 26 September, not current detector history.",
                            "Current default corridor code is applied to that fixed historical geometry.",
                            "Corridor only: low-object, accumulation, shape filters and tracking are not replayed.",
                            "Neighbor connectivity precedes DBSCAN core/point-count tests; it is not a STOP prediction.",
                            "Source fixture lacks ring; indistinguishable XYZ/intensity copies are reported.",
                            "The source fixture covers only 15–80 m; no inference about >80 m occupancy.",
                            "Previously inspected organizer synthetic objects; no unseen recall or false-alarm claim."],
            "rows": rows}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", required=True)
    p.add_argument("--trace", default=str(ROOT / "docs/evidence/results/quality_cycle_2026-09-26_missed_diagnosis/seto_trace.json.gz"))
    p.add_argument("--fixture", default=str(ROOT / "docs/evidence/results/p4_novel_source_2026-09-26/points.npz"))
    p.add_argument("--object", default="small_center")
    p.add_argument("--frames", help="Comma-separated frame IDs; default all overlapping source frames")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = run(args)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"frames": len(out["rows"]), "out": str(path)}))


if __name__ == "__main__":
    main()
