#!/usr/bin/env python3
"""Registered source-motion upper bound; no Detector.process or tracker replay."""
from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
from dataclasses import fields
import gzip
import inspect
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from resense import clustering  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector, _clusters_of  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.pointcloud import compact_to_compact16, pointcloud2_to_structured, structured_to_compact  # noqa: E402
from resense.track import TrackModel  # noqa: E402
from scripts.cache_io import load_cache_array  # noqa: E402
from scripts.diagnose_range_metric import neighbor_pairs, sha  # noqa: E402
from scripts.label_fake_objects import group_frame  # noqa: E402
from scripts.trace_detector_stages import _return_conditions  # noqa: E402
from scripts.trace_object_failures import point_keys, source_indices  # noqa: E402


def oracle_speed(stamps, positions):
    """Preregistered causal median slopes; duplicates retained, no outcome inputs."""
    t, x = np.asarray(stamps[-5:]), np.asarray(positions[-5:])
    if len(t) < 2:
        return None, None
    if np.any(np.diff(t) <= 0):
        raise ValueError("timestamps must be strictly increasing")
    gap = 2 if len(t) >= 3 else 1
    slopes = [(x[i] - x[j]) / (t[j] - t[i])
              for i in range(len(t)) for j in range(i + gap, len(t))]
    raw = float(np.median(slopes))
    return float(np.clip(raw, 0, 30)), raw


def bounded_labels(vox, cfg):
    """DBSCAN core/border semantics on the filtered production neighbor graph."""
    pairs, d, bound, _ = neighbor_pairs(vox, cfg)
    pairs = pairs[d <= bound]
    n = len(vox)
    labels = np.full(n, -1, np.intp)
    if not n:
        return labels
    a, b = pairs.T
    degree = np.bincount(a, minlength=n) + np.bincount(b, minlength=n) + 1
    core = degree >= cfg.min_samples
    ci = np.flatnonzero(core)
    if not len(ci):
        return labels
    pos = np.full(n, -1, np.intp)
    pos[ci] = np.arange(len(ci))
    cc = core[a] & core[b]
    graph = coo_matrix((np.ones(int(cc.sum())), (pos[a[cc]], pos[b[cc]])), shape=(len(ci), len(ci)))
    nc, comp = connected_components(graph, directed=False)
    first = np.full(nc, len(ci))
    np.minimum.at(first, comp, np.arange(len(ci)))
    rank = np.empty(nc, np.intp)
    rank[np.argsort(first, kind="stable")] = np.arange(nc)
    labels[ci] = rank[comp]
    m1, m2 = core[a] & ~core[b], core[b] & ~core[a]
    border = np.concatenate((b[m1], a[m2]))
    lab = np.concatenate((labels[a[m1]], labels[b[m2]]))
    best = np.full(n, nc, np.intp)
    np.minimum.at(best, border, lab)
    labels[np.unique(border)] = best[np.unique(border)]
    return labels


@contextmanager
def observe_clusters(target, origins, bounded):
    """Wrap production cluster returns; restore module globals even on failure."""
    original, original_labels = clustering._corridor_cluster, clustering.cluster_labels
    signature = inspect.signature(original)
    conditions = _return_conditions(original)
    records = []

    def wrapped(*args, **kwargs):
        p = signature.bind(*args, **kwargs).arguments
        blob, inv = p["b"], p["inv"]
        m = target[blob.idx]
        ids = blob.idx[m]
        strict = p["in_gauge"]
        record = {"source_raw": int(m.sum()), "raw": len(blob.idx), "voxels": blob.n_vox,
                  "source_voxels": len(np.unique(inv[ids])),
                  "source_strict_voxels": len(np.unique(inv[ids[strict[ids]]])),
                  "strict_voxels": len(np.unique(inv[blob.idx[strict[blob.idx]]])),
                  "source_frames": sorted(set(origins[ids].tolist())),
                  "size_m": blob.size.tolist(), "distance_m": float(blob.bmin[0]),
                  "count_factor": float(p["factor"])}
        previous = sys.getprofile()

        def profiler(frame, event, value):
            if frame.f_code is original.__code__ and event == "return":
                record["return_condition"] = conditions.get(frame.f_lineno, {}).get("condition")
        try:
            sys.setprofile(profiler)
            result = original(*args, **kwargs)
        finally:
            sys.setprofile(previous)
        record["result"] = None if result is None else {
            "zone": result.zone, "reason": result.reason, "thin": result.thin,
            "weak": result.weak, "n_gauge": result.n_gauge, "n": result.n}
        records.append(record)
        return result

    try:
        clustering._corridor_cluster = wrapped
        if bounded:
            clustering.cluster_labels = bounded_labels
        yield records
    finally:
        clustering._corridor_cluster, clustering.cluster_labels = original, original_labels


def evaluate(cand, target, origins, cfg, n_acc, valid, floor_valid, bounded):
    vox, inv = clustering.voxelize(cand.xyz, cfg.cluster)
    factor = max(1., n_acc * cfg.accumulation.min_points_scale) if n_acc > 1 else 1.
    with observe_clusters(target, origins, bounded) as records:
        clusters = _clusters_of(cand, cfg.cluster, axis_valid=valid, height_valid=floor_valid,
            min_points_factor=factor, factor_range=cfg.accumulation.min_range,
            smear_max_length=cfg.accumulation.smear_max_length if n_acc > 1 else 0.,
            smear_max_width=cfg.accumulation.smear_max_width if n_acc > 1 else 0.,
            gauge=cfg.gauge, keep_thin=True, weak_from=cfg.tracking.thin_far_min_distance)
    labels = bounded_labels(vox, cfg.cluster) if bounded else clustering.cluster_labels(vox, cfg.cluster)
    raw_labels = labels[inv]
    source_dbscan = []
    for label in np.unique(raw_labels[target]):
        if label < 0:
            continue
        ii = np.flatnonzero((raw_labels == label) & target)
        source_dbscan.append({"source_voxels": len(np.unique(inv[ii])),
                              "source_strict_voxels": len(np.unique(inv[ii[cand.in_gauge[ii]]])),
                              "source_frames": sorted(set(origins[ii].tolist()))})
    return {"n_acc": n_acc, "source_raw": int(target.sum()),
            "source_voxels": len(np.unique(inv[target])),
            "source_strict_voxels": len(np.unique(inv[target & cand.in_gauge])),
            "factor": factor, "effective_gauge_min": int(np.ceil(cfg.cluster.gauge_min_points * factor)),
            "source_dbscan": source_dbscan, "cluster_records": records,
            "gauge_candidates": sum(c.zone == "gauge" for c in clusters)}


def inputs(args):
    from rosbags.typesys import Stores, get_typestore
    types = get_typestore(Stores.ROS2_HUMBLE)
    cfg = DetectorConfig()
    labels = json.loads((ROOT / "labels/cloud_with_fake_obj.json").read_text())
    with gzip.open(ROOT / "docs/evidence/results/quality_cycle_2026-09-26_missed_diagnosis/seto_trace.json.gz", "rt") as f:
        traces = {r["frame"]: r["trace"]["track"] for r in json.load(f)["frames"]}
    allowed = {f.name for f in fields(TrackModel)}
    connection = sqlite3.connect(f"file:{Path(args.db).resolve()}?mode=ro", uri=True)
    topics = connection.execute("SELECT id FROM topics WHERE type='sensor_msgs/msg/PointCloud2'").fetchall()
    if len(topics) != 1:
        raise ValueError("expected exactly one point-cloud topic")
    messages = connection.execute("SELECT timestamp,data FROM messages WHERE topic_id=? ORDER BY timestamp,id LIMIT ? OFFSET ?",
                                  (topics[0][0], 44, 295))
    import hashlib
    for k, (stamp, raw) in enumerate(messages, 295):
        structured = pointcloud2_to_structured(types.deserialize_cdr(raw, "sensor_msgs/msg/PointCloud2"))
        xyz = np.column_stack([structured[n].ravel() for n in ("x", "y", "z")])
        zeros = np.flatnonzero((xyz == 0).all(axis=1))
        if not len(zeros):
            raise ValueError(f"organizer source delimiter missing at {k}")
        appended = structured[int(zeros[-1]) + 1:]
        compact = structured_to_compact(appended)
        source = frame_from_compact(compact_to_compact16(compact), cfg.sensor)
        original = frame_from_compact(compact, cfg.sensor)
        groups = sorted(group_frame(source.xyz, 8.), key=lambda g: source.xyz[g, 0].min())
        originals = sorted(group_frame(original.xyz, 8.), key=lambda g: original.xyz[g, 0].min())
        frame_labels = sorted(labels[f"{k:05d}"], key=lambda r: r["distance"])
        if len(groups) != len(frame_labels) or len(originals) != len(groups):
            raise ValueError(f"source group/label mismatch at {k}")
        path = Path(args.cache) / f"cloud_with_fake_obj_{k:04d}.npy.zst"
        frame = frame_from_compact(load_cache_array(path), cfg.sensor, stamp=stamp / 1e9)
        cache_keys, src_keys = point_keys(frame), point_keys(source)
        all_ids, targets, position = [], None, None
        for group, og, label in zip(groups, originals, frame_labels):
            ids, extra = source_indices(cache_keys, src_keys[group])
            if extra:
                raise ValueError("source/background identity ambiguous")
            all_ids.extend(ids.tolist())
            if label["label"] == "small_center":
                targets = ids
                position = float(original.xyz[og, 0].min())
        if targets is None:
            raise ValueError(f"small_center absent at {k}")
        yield {"frame": k, "cloud": frame, "target": targets, "all_source": np.asarray(all_ids),
               "position": position, "track": TrackModel(**{k: v for k, v in traces[k].items() if k in allowed}),
               "provenance": {"frame": k, "timestamp_ns": stamp, "raw_message_sha256": hashlib.sha256(raw).hexdigest(),
                              "cache_sha256": sha(path), "historical_track": traces[k]}}
    connection.close()


class AccumulationObserver:
    def __init__(self, n):
        self.detector = Detector()
        self.detector.cfg.accumulation.n_frames = n
        # Detector initializes the buffer before the diagnostic overrides its window.
        from resense.accumulate import CandidateBuffer
        self.detector.buffer = CandidateBuffer(n)
        self.n = n
        self.origin_buffer = deque(maxlen=max(0, n - 1))

    def run(self, cand, target, origins, track, speed, dt):
        d = self.detector
        d.track = track
        merged, n_acc = d._accumulate(cand, speed, dt)
        acc = d.cfg.accumulation
        if speed is None or speed < acc.min_speed or self.n == 1:
            self.origin_buffer.clear()
            return merged, target, origins, n_acc
        old_target, old_origins = [], []
        for item in self.origin_buffer:
            item[0] -= np.float32(speed * dt)
            keep = item[0] >= acc.min_range
            old_target.append(item[1][keep])
            old_origins.append(item[2][keep])
        targets = np.concatenate([target, *old_target])
        frame_ids = np.concatenate([origins, *old_origins])
        far = (cand.xyz[:, 0] >= acc.min_range) & ~cand.low
        if int(far.sum()) > acc.max_points_per_frame:
            raise ValueError("diagnostic provenance does not support buffer subsampling")
        self.origin_buffer.append([cand.xyz[far, 0].copy(), target[far].copy(), origins[far].copy()])
        if len(merged) != len(targets):
            raise AssertionError("accumulation provenance alignment differs")
        return merged, targets, frame_ids, n_acc


def run(args):
    cfg, geometry = DetectorConfig(), Detector()
    buffers = {(n, name): AccumulationObserver(n) for n in range(1, 6) for name in ("present", "background")}
    stamps, positions, history, results, provenance = [], [], [], [], []
    displacement = 0.
    for item in inputs(args):
        frame, k, track = item["cloud"], item["frame"], item["track"]
        stamps.append(frame.stamp)
        positions.append(item["position"])
        speed, raw_speed = oracle_speed(stamps, positions)
        dt = stamps[-1] - stamps[-2] if len(stamps) > 1 else .1
        displacement += (speed or 0.) * dt
        source_xyz = frame.xyz[item["target"]].copy()
        source_intensity = frame.intensity[item["target"]].copy()
        history.append((k, displacement, source_xyz, source_intensity))
        history = history[-5:]
        geometry.track = track
        cand, _, _, _, (_, valid, floor_valid) = geometry._corridor(frame.xyz, frame.intensity)
        target = np.isin(cand.idx, item["target"])
        not_source = ~np.isin(cand.idx, item["all_source"])
        row = {"frame": k, "source_distance_m": item["position"], "speed_raw_mps": raw_speed,
               "speed_supplied_mps": speed, "dt_s": dt, "source_points": len(source_xyz), "variants": []}
        for n in range(1, 6):
            physical_xyz, physical_i, origins = [], [], []
            selected = history[-n:]
            for old_k, old_shift, xyz, intensity in selected:
                moved = xyz.copy()
                moved[:, 0] -= displacement - old_shift
                physical_xyz.append(moved)
                physical_i.append(intensity)
                origins.extend([old_k] * len(xyz))
            raw_physical = np.concatenate(physical_xyz)
            origins = np.asarray(origins)
            source_cand = geometry._corridor(raw_physical, np.concatenate(physical_i))[0]
            source_origins = origins[source_cand.idx]
            source_cand.idx = np.where(source_origins == k, source_cand.idx, -1)
            for bounded in (False, True):
                result = evaluate(source_cand, np.ones(len(source_cand), bool), source_origins,
                                  cfg, len(selected), valid, floor_valid, bounded)
                result.update(mode="physical_source_only", window=n, bounded=bounded,
                              physical_xyz_extent_m=np.ptp(raw_physical, axis=0).tolist())
                row["variants"].append(result)
            for name in ("present", "background"):
                select = np.ones(len(cand), bool) if name == "present" else not_source
                current = cand.subset(select)
                current_target = target[select]
                current_origins = np.where(current_target, k, -1)
                merged, merged_target, merged_origins, n_acc = buffers[n, name].run(
                    current, current_target, current_origins, track, speed, dt)
                for bounded in (False, True):
                    result = evaluate(merged, merged_target, merged_origins, cfg, n_acc, valid, floor_valid, bounded)
                    result.update(mode="production_" + name, window=n, bounded=bounded)
                    row["variants"].append(result)
        results.append(row)
        provenance.append(item["provenance"])
        print(f"diagnosed frame {k}", flush=True)
    return {"protocol_sha256": sha(ROOT / "docs/ORACLE_ACCUMULATION_PROTOCOL_2026-09-28.md"),
            "observer_sha256": sha(__file__), "source_hashes": {str(p.relative_to(ROOT)): sha(p) for p in sorted((ROOT / "resense").glob("*.py"))},
            "mode": "oracle_source_relative_motion_historical_geometry_conditional_clustering",
            "limitations": ["No real odometry; source motion need not match background motion.",
                            "Historical rounded geometry; no current detector replay parity.",
                            "No low-object stage, calibration updates or tracker; gauge candidates are not STOPs.",
                            "All original source frames and timestamps preserved; no placement from detector geometry."],
            "inputs": provenance, "rows": results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    output = run(args)
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(json.dumps(output, separators=(",", ":")).encode(), mtime=0))


if __name__ == "__main__":
    main()
