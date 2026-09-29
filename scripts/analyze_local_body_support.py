"""Label-blind local-body diagnostic, never a detector rule or a temporal replay.

Run as ``python -m scripts.analyze_local_body_support --help``. The only new
geometric scale is the pre-existing far-structure diagnostic's 0.45 m window.
It is fixed here, not fitted to events. Labels enter score_parts only, after
every local subset and descriptor has been computed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import sys

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from resense.clustering import _Blob, _corridor_cluster, dbscan_labels, voxelize
from resense.config import ClusterConfig, GaugeConfig
from resense.gauge import gauge_core_mask, point_in_polygon, widened_profile


RADIUS_M = 0.45
MODES = ("corridor", "strict")
NEGATIVE_KEYS = ("new_data_1.jsonl:74", "new_data_1.jsonl:298",
                 "new_data_6.jsonl:331", "new_data_5.jsonl:330")
ROOT = Path(__file__).resolve().parents[1]
TEMP = Path("C:/Users/alikh/AppData/Local/Temp/opencode")


@dataclass(frozen=True)
class RuntimeSupport:
    """Runtime-only inputs: deliberately no target, event identity, or object kind."""

    xyz: np.ndarray
    dy: np.ndarray
    h: np.ndarray
    strict: np.ndarray
    candidate: np.ndarray
    frame_idx: np.ndarray
    inv: np.ndarray
    mask_source: str
    axis_valid: float | None = None
    height_valid: float | None = None

    def __post_init__(self):
        n = len(self.xyz)
        if self.xyz.shape != (n, 3) or not np.isfinite(self.xyz).all():
            raise ValueError("finite XYZ with shape (N, 3) required")
        for name in ("dy", "h", "strict", "candidate", "frame_idx", "inv"):
            if getattr(self, name).shape != (n,):
                raise ValueError(f"{name} does not align with XYZ")
        if not np.isfinite(self.dy).all() or not np.isfinite(self.h).all():
            raise ValueError("finite reference coordinates required")
        if np.any(self.strict & ~self.candidate):
            raise ValueError("strict membership must be a subset of candidates")


def local_parts(support: RuntimeSupport, cfg: ClusterConfig, mode: str) -> list[np.ndarray]:
    """Physical-XY DBSCAN on existing voxel memberships, current points only.

    One centroid per occupied voxel; projecting into XY does not collapse distinct
    vertical voxels. Z is deliberately not a link distance (a sparse vertical cable
    is the research target). min_samples remains cfg.min_samples. No seed/rank uses
    labels. The two modes measure the effect of using the supplied strict mask.
    """
    if mode not in MODES:
        raise ValueError(f"unknown mask mode: {mode}")
    eligible = support.candidate & (support.frame_idx >= 0)
    if mode == "strict":
        eligible &= support.strict
    ids = np.flatnonzero(eligible)
    if not len(ids):
        return []
    _, inv = np.unique(support.inv[ids], return_inverse=True)
    nv = int(inv.max()) + 1
    sums = np.zeros((nv, 3), dtype=np.float64)
    np.add.at(sums, inv, support.xyz[ids])
    centers = sums / np.bincount(inv)[:, None]
    centers[:, 2] = 0.0
    labels = dbscan_labels(centers, RADIUS_M, cfg.min_samples)[inv]
    return [ids[labels == lab] for lab in np.unique(labels) if lab >= 0]


def geometry(support, ids):
    xyz = support.xyz[ids]
    strict = support.strict[ids]
    return {
        "points": len(ids), "voxels": int(np.unique(support.inv[ids]).size),
        "strict_points": int(strict.sum()),
        "strict_voxels": int(np.unique(support.inv[ids[strict]]).size),
        "size_m": np.ptp(xyz, axis=0).astype(float).tolist() if len(ids) else None,
        "x_m": [float(xyz[:, 0].min()), float(xyz[:, 0].max())] if len(ids) else None,
        "dy_m": [float(support.dy[ids].min()), float(support.dy[ids].max())] if len(ids) else None,
        "h_m": [float(support.h[ids].min()), float(support.h[ids].max())] if len(ids) else None,
    }


def describe_proxy(support, ids, cfg, *, check_reference):
    """Call existing ordinary descriptor with explicit incomplete-input limits.

    Exact effective dy/h and strict masks are supplied for positive blobs. Saved
    blobs omit intensity, dy_report, in_rail, dy_alt, factor, ring and voxel IDs.
    This is a geometry proxy, NOT exact production descriptor replay. Ring/weak/
    thin rescue is disabled; no arbitrary intensity or reference is invented.
    Negative effective validity ranges are unavailable, so the reference-aware
    answer is unknown (None), independently of the geometry-only answer.
    """
    if check_reference and (support.axis_valid is None or support.height_valid is None):
        return None
    if not len(ids):
        return {"ordinary_gauge": False, "output": None}
    b = _Blob.of(support.xyz, ids, int(np.unique(support.inv[ids]).size))
    c = _corridor_cluster(
        b, support.dy, support.h, support.strict, None, support.inv,
        support.frame_idx, cfg, 1.0, 0.0,
        support.axis_valid if check_reference else float("inf"),
        support.height_valid if check_reference else None,
    )
    if c is None:
        return {"ordinary_gauge": False, "output": None}
    return {"ordinary_gauge": c.zone == "gauge" and not c.thin and not c.weak,
            "output": {"zone": c.zone, "reason": c.reason, "voxels": c.n,
                       "strict_voxels": c.n_gauge, "thin": c.thin, "weak": c.weak}}


def decompose(support, cfg):
    """All runtime outputs are finalized before the scoring mask is consulted."""
    result = {}
    for mode in MODES:
        result[mode] = [
            {"indices": ids.tolist(), "frame_indices": support.frame_idx[ids].tolist(),
             "geometry": geometry(support, ids),
             "geometry_proxy": describe_proxy(support, ids, cfg, check_reference=False),
             "reference_proxy": describe_proxy(support, ids, cfg, check_reference=True)}
            for ids in local_parts(support, cfg, mode)
        ]
    return result


def score_parts(parts, target, support):
    """Evaluation only: exact injected identity or saved false-track membership."""
    target = np.asarray(target, dtype=bool)
    if target.shape != (len(support.xyz),):
        raise ValueError("scoring mask does not align")
    nt = int(target.sum())
    strict_target = target & support.strict & (support.frame_idx >= 0)
    nst = int(strict_target.sum())
    scored = []
    for part in parts:
        ids = np.asarray(part["indices"], dtype=int)
        n = int(target[ids].sum())
        ns = int(strict_target[ids].sum())
        scored.append({**part, "scoring": {
            "target_points": n, "other_points": len(ids) - n,
            "target_fraction": n / len(ids), "target_recall": n / nt if nt else None,
            "strict_target_recall": ns / nst if nst else None,
            "complete_target": bool(nt and n == nt),
            "complete_strict_target": bool(nst and ns == nst),
        }})
    return scored


def evaluate(support, cfg, target):
    runtime = decompose(support, cfg)
    return {mode: score_parts(parts, target, support) for mode, parts in runtime.items()}


def positive_support(record, geometry_record, cfg):
    if record["strict_mask_source"] != "effective_corridor":
        raise ValueError("low-stage support is not a corridor strict mask")
    # Production b.pts was float32. Reconstruct its normalized voxel keys in that
    # dtype; float64 scaling can move returns at a voxel boundary into another cell.
    xyz = np.asarray(record["xyz"], dtype=np.float32)
    _, inv = voxelize(xyz, cfg)
    return RuntimeSupport(
        xyz, np.asarray(record["dy"]), np.asarray(record["h"]),
        np.asarray(record["strict_mask"], dtype=bool), np.ones(len(xyz), bool),
        np.asarray(record["frame_idx"], dtype=int), inv,
        "actual_effective_corridor_strict_including_active_reference_union",
        geometry_record["axis_valid"], geometry_record["height_valid"],
    )


def validate_saved_voxels(support, record, blob):
    """Fail closed if re-created voxel membership disagrees with saved counts."""
    target = np.asarray(record["target_mask"], dtype=bool)
    masks = {"target": target, "strict": support.strict,
             "target_strict": target & support.strict, "background": ~target,
             "background_strict": ~target & support.strict}
    if np.unique(support.inv).size != blob["voxels"]:
        raise ValueError("full blob voxel reconstruction mismatch")
    for name, mask in masks.items():
        if np.unique(support.inv[mask]).size != record[name]["voxels"]:
            raise ValueError(f"{name} voxel reconstruction mismatch")


def is_ordinary_oracle(oracle, cfg):
    if not oracle or oracle["zone"] != "gauge" or oracle["thin"]:
        return False
    # Old cluster_record omitted weak: independently enforce its ordinary bar.
    minimum = cfg.min_points if oracle["distance"] < cfg.far_range else cfg.min_points_far
    return oracle["voxels"] >= minimum


def positive_report(path, placement):
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved["schema"] != "range-shape-diagnostic-v2":
        raise ValueError("unexpected positive schema")
    cfg = ClusterConfig(**saved["config"]["cluster"])
    sequences = []
    for seq in saved["sequences"]:
        if not seq["prior_parity"] or not seq["paired_parity"]:
            raise ValueError("positive saved parity is not established")
        counts = Counter()
        frames = []
        for row, trace in zip(seq["rows"], seq["traces"], strict=True):
            if row["frame"] != trace["frame"]:
                raise ValueError("frame order mismatch")
            blobs = []
            for ordinal, blob in enumerate(trace["blobs"]):
                if blob["function"] != "_corridor_cluster":
                    counts["excluded_low_stage_blobs"] += 1
                    continue
                record = blob["support"]
                support = positive_support(record, trace["geometry"], cfg)
                validate_saved_voxels(support, record, blob)
                counts["validated_corridor_blobs"] += 1
                counts["historical_points"] += int((support.frame_idx < 0).sum())
                target = np.asarray(record["target_mask"], dtype=bool)
                parts = evaluate(support, cfg, target)
                blobs.append({
                    "ordinal": ordinal, "mask_source": support.mask_source,
                    "source_geometry": geometry(support, np.arange(len(support.xyz))),
                    "saved_target_geometry": record["target"],
                    "saved_strict_geometry": record["strict"],
                    "actual_output": blob["output"], "actual_returns": blob["returns"],
                    "saved_oracle_output": blob.get("oracle_target_only"),
                    "missed_rejected_ordinary_oracle": not row["hit"] and blob["output"] is None
                    and is_ordinary_oracle(blob.get("oracle_target_only"), cfg),
                    "parts": parts,
                })
            counts["frames"] += 1
            counts["visible_frames"] += bool(row["n"])
            counts["frames_with_corridor_blob"] += bool(blobs)
            oracle_blobs = [b for b in blobs if b["missed_rejected_ordinary_oracle"]]
            counts["missed_rejected_ordinary_oracle_frames"] += bool(oracle_blobs)
            for mode in MODES:
                good = [p for b in blobs for p in b["parts"][mode]
                        if p["reference_proxy"]["ordinary_gauge"] and p["scoring"]["target_points"]]
                counts[f"{mode}_ordinary_overlap_frames"] += bool(good)
                recovered = [p for b in oracle_blobs for p in b["parts"][mode]
                             if p["reference_proxy"]["ordinary_gauge"]
                             and p["scoring"]["complete_target"]]
                counts[f"{mode}_complete_oracle_recovery_frames"] += bool(recovered)
                counts[f"{mode}_pure_complete_oracle_recovery_frames"] += any(
                    p["scoring"]["other_points"] == 0 for p in recovered)
            frames.append({"frame": row["frame"], "distance_m": row["d"],
                           "saved_hit": row["hit"], "rendered_points": row["n"], "blobs": blobs})
        sequences.append({"placement": placement, "kind": seq["kind"], "file0": seq["file0"],
                          "counts": dict(counts), "frames": frames})
    return {"path": str(path), "config": saved["config"], "sequences": sequences}


def snapshot_support(xyz, dy, h, frame_idx, cfg, gauge):
    """Rail-only crop approximation; never claim the production union/strict mask."""
    xyz = np.asarray(xyz, dtype=np.float32)
    dy, h = np.asarray(dy), np.asarray(h)
    candidate = (point_in_polygon(dy, h, widened_profile(gauge, gauge.warning_margin))
                 & (xyz[:, 0] >= gauge.range_min) & (xyz[:, 0] <= gauge.range_max))
    strict = candidate & gauge_core_mask(dy, h, xyz[:, 0], gauge)
    _, inv = voxelize(xyz, cfg)
    return RuntimeSupport(xyz, dy, h, strict, candidate, np.asarray(frame_idx), inv,
                          "approximate_rail_only_masks_on_cropped_snapshot")


def negative_report(measurement):
    trace_path = measurement / "false_target_trace/trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if trace["frames"] != 11271 or trace["detection_mismatch_frames"]:
        raise ValueError("saved baseline negative trace parity failed")
    cfg, gauge = ClusterConfig(), GaugeConfig()
    events, paths = [], [trace_path]
    for key in NEGATIVE_KEYS:
        event = next(e for e in trace["events"] if e["key"] == key)
        onset_row = next(r for r in event["timeline"] if r["alarm"])
        snapshots = []
        counts = Counter()
        # Only the first alarm snapshot is an exact current-frame track support.
        # Later scheduled snapshots may intentionally record a missed association;
        # their target mask is empty while the historical cluster count is not.
        row = onset_row
        if "point_snapshot" not in row or row["misses"]:
            raise ValueError(f"missing exact onset snapshot: {key}")
        if "point_snapshot" in row:
            path = measurement / "false_target_trace/points" / row["point_snapshot"]
            paths.append(path)
            with np.load(path, allow_pickle=False) as z:
                target = np.asarray(z["target"], dtype=bool)
                if row["misses"] or int(target.sum()) != row["cluster"]["n_points_idx"]:
                    raise ValueError("snapshot lacks exact current mapped false-track support")
                support = snapshot_support(z["xyz"], z["dy"], z["h"], z["indices"], cfg, gauge)
                parts = evaluate(support, cfg, target)
            counts["snapshots"] += 1
            for mode in MODES:
                good = [p for p in parts[mode] if p["geometry_proxy"]["ordinary_gauge"]]
                counts[f"{mode}_ordinary_any_snapshots"] += bool(good)
                counts[f"{mode}_ordinary_false_overlap_snapshots"] += any(
                    p["scoring"]["target_points"] > 0 for p in good)
                counts[f"{mode}_complete_strict_false_snapshots"] += any(
                    p["scoring"]["complete_strict_target"] for p in good)
            snapshots.append({
                "frame": row["frame_id"], "path": str(path), "is_onset": True,
                "alarm": row["alarm"], "mask_source": support.mask_source,
                "crop_geometry": geometry(support, np.arange(len(support.xyz))),
                "false_track_geometry": geometry(support, np.flatnonzero(target)),
                "false_track_strict_geometry": geometry(support, np.flatnonzero(target & support.strict)),
                "actual_cluster": row["cluster"], "saved_track_reference": row["track"],
                "parts": parts,
            })
        if not any(s["is_onset"] for s in snapshots):
            raise ValueError(f"missing onset snapshot: {key}")
        events.append({"key": key, "counts": dict(counts), "snapshots": snapshots})
    return {"config": {"cluster": asdict(cfg), "gauge": asdict(gauge)}, "events": events}, paths


def summary(report):
    return {
        "status": report["status"],
        "positives": [{k: s[k] for k in ("placement", "kind", "file0", "counts")}
                      for p in report["positives"] for s in p["sequences"]],
        "negatives": [{"key": e["key"], "counts": e["counts"]}
                      for e in report["negatives"]["events"]],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--centre", type=Path, default=TEMP / "range-shape-centre-coordinator.json")
    parser.add_argument("--edge", type=Path, default=TEMP / "range-shape-edge-coordinator.json")
    parser.add_argument("--measurement", type=Path,
                        default=Path("D:/Datasets/ReSense/cross_ring_2026-09-28_measurement"))
    parser.add_argument("--out", type=Path, default=TEMP / "local-body-support.json")
    args = parser.parse_args()
    if not args.out.resolve().is_relative_to(TEMP.resolve()) or not args.out.parent.is_dir():
        parser.error("output must have an existing parent under the approved temporary root")
    positives = [positive_report(args.centre, "centre"), positive_report(args.edge, "edge")]
    negatives, negative_paths = negative_report(args.measurement)
    paths = [args.centre, args.edge, *negative_paths, Path(__file__),
             ROOT / "resense/clustering.py", ROOT / "resense/config.py", ROOT / "resense/gauge.py"]
    report = {
        "schema": "local-body-support-v1", "status": "diagnostic_only_no_justified_selector",
        "method": {"radius_xy_m": RADIUS_M, "min_samples": "unchanged cluster.min_samples",
                   "modes": MODES, "label_use": "post-decomposition scoring only",
                   "voxel_membership": "reconstructed normalized float32 keys, saved positive counts validated",
                   "descriptor": "ordinary geometry proxy; positive effective reference check also reported",
                   "threshold_sweep": False},
        "limits": ["Positive input contains only target-intersecting saved blobs, not all rejected background.",
                   "Negative masks are rail-only crop approximations, not actual production strict/union masks.",
                   "Negative effective validity limits are unknown; reference_proxy is null.",
                   "Proxy omits intensity, alternate/report laterals, rail fallback and accumulation factors.",
                   "No temporal replay, rings, common-reference motion, STOP gain or latency inference."],
        "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "positives": positives, "negatives": negatives,
    }
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(summary(report), indent=2))
    print(f"Output: {args.out}")


if __name__ == "__main__":
    main()
