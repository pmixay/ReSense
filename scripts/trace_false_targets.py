#!/usr/bin/env python3
"""Replay frozen output pieces and trace exact point support of every false target.

Diagnostic only: no detector/config mutation. Matches archived detections frame by frame,
records all tracked states for the 45 false-event identities, and saves full target points
with their surrounding cloud at selected times. Scene/cause classification is a review step.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.gauge import corridor_coordinates  # noqa: E402
from resense.io import _natural_key  # noqa: E402


def selection(rows):
    events = {}
    for k, row in enumerate(rows):
        for d in row["detections"]:
            events.setdefault(d["id"], []).append(k)
    schedule = {}
    for key, frames in events.items():
        chosen = {frames[0], frames[len(frames) // 2], frames[-1]}
        chosen.update(k for i in (frames[0], frames[-1]) for k in (i - 10, i - 5, i + 5, i + 10)
                      if 0 <= k < len(rows))
        schedule[key] = chosen
    return events, schedule


def cluster_record(c):
    return {"n_voxels": c.n, "n_raw": c.n_raw, "n_gauge": c.n_gauge,
            "distance": float(c.distance), "lateral": float(c.lateral),
            "centroid": c.centroid.tolist(),
            "size": c.size.tolist(), "bbox_min": c.bbox_min.tolist(), "bbox_max": c.bbox_max.tolist(),
            "height_min": float(c.height_min), "height_max": float(c.height_max),
            "kind": c.kind, "zone": c.zone, "reason": c.reason,
            "rail_line": c.rail_line, "wall_kept": c.wall_kept, "demoted": c.demoted,
            "thin": c.thin, "n_points_idx": int(c.points_idx.size)}


def observe_associations(tracker):
    """Wrap update to observe its inputs after any mount reseed, without changing matching."""
    original = tracker.update

    def update(clusters, ego_shift=0.0, frame_dt=None, **kwargs):
        before = {t.id: {"centroid": t.centroid.copy(), "velocity": t.velocity.copy(),
                         "hits": t.hits, "misses": t.misses, "reported": t.reported,
                         "zone": t.zone, "last": t.last} for t in tracker.tracks}
        tracks = original(clusters, ego_shift=ego_shift, frame_dt=frame_dt, **kwargs)
        observed = {}
        for t in tracks:
            old = before.get(t.id)
            if old is None or t.misses or t.hits <= old["hits"]:
                continue
            predicted = old["centroid"] + (old["velocity"] if old["hits"] > 1
                                           else np.array([-float(ego_shift), 0.0, 0.0]))
            residual = t.centroid - predicted
            base = tracker._gate(old["centroid"][0])
            dt = frame_dt if frame_dt is not None and frame_dt > 0 else tracker.cfg.frame_dt
            step = tracker.cfg.ego_speed_max * dt
            allowed = base + (step if residual[0] < 0 else 0.0)
            observed[t.id] = {
                "previous_centroid": old["centroid"].tolist(), "predicted": predicted.tolist(),
                "previous_velocity": old["velocity"].tolist(), "residual": residual.tolist(),
                "residual_3d": float(np.linalg.norm(residual)),
                "residual_yz": float(np.linalg.norm(residual[1:])),
                "base_gate": float(base), "original_allowed_3d": float(allowed),
                "previous_hits": old["hits"], "previous_misses": old["misses"],
                "previous_reported": old["reported"], "previous_zone": old["zone"],
                "previous_bbox_min": old["last"].bbox_min.tolist() if old["last"] else None,
                "previous_bbox_max": old["last"].bbox_max.tolist() if old["last"] else None,
            }
        tracker.observed_associations = observed
        return tracks

    tracker.update = update


def support_stats(xyz, dy, h, idx):
    if not len(idx):
        return {}
    points, lat, height = xyz[idx], dy[idx], h[idx]
    x0, x1 = float(points[:, 0].min()), float(points[:, 0].max())
    d0, d1 = float(lat.min()), float(lat.max())
    near = ((xyz[:, 0] >= x0 - 8) & (xyz[:, 0] <= x1 + 8)
            & (dy >= d0 - 0.10) & (dy <= d1 + 0.10) & (h > -0.3) & (h < 0.6))
    outside = near & ((xyz[:, 0] < x0 - 0.3) | (xyz[:, 0] > x1 + 0.3))
    bins = np.floor(xyz[outside, 0]).astype(int)
    values = [float(np.percentile(h[outside][bins == b], 90)) for b in np.unique(bins)
              if (bins == b).sum() >= 2]
    line = float(np.median(values)) if values else None
    return {"dy_min": d0, "dy_max": d1, "height_max": float(height.max()),
            "same_band_reference_bins": len(values), "same_band_reference_p90_median": line,
            "height_excess_over_same_band": None if line is None else float(height.max()) - line,
            "snapshot_points": int(len(idx))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", required=True)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    (out / "points").mkdir(parents=True, exist_ok=True)
    cfg = DetectorConfig()
    all_events, mismatches, total = [], [], 0
    for path in sorted(Path(args.archives).glob("new_data_*.jsonl.gz"), key=lambda p: _natural_key(str(p))):
        piece = path.name.removesuffix(".jsonl.gz")
        with gzip.open(path, "rt") as fh:
            rows = [json.loads(line) for line in fh]
        event_frames, schedule = selection(rows)
        events = {key: {"key": f"{piece}.jsonl:{key}", "alarm_frame_indices": frames, "timeline": []}
                  for key, frames in event_frames.items()}
        detector = Detector(cfg)
        observe_associations(detector.tracker)
        for k, row in enumerate(rows):
            frame = frame_from_compact(np.load(Path(args.cache) / f"{row['frame_id']}.npy"), cfg.sensor,
                                       stamp=row["stamp"], frame_id=row["frame_id"])
            result = detector.process(frame)
            actual = [d.to_dict() for d in result.detections]
            if actual != row["detections"]:
                mismatches.append(row["frame_id"])
            total += 1
            tracks = {t.id: t for t in detector.tracker.tracks if t.id in events}
            if not tracks:
                continue
            xyz = result.xyz
            dy, h = corridor_coordinates(xyz, result.track)
            alarm_ids = {d.id for d in result.detections}
            advisory_ids = {d.id for d in result.warnings}
            for key, track in tracks.items():
                cluster = track.last
                if cluster is None:
                    continue
                idx = cluster.points_idx if track.misses == 0 else np.zeros(0, dtype=int)
                record = {"frame_id": row["frame_id"], "piece_frame": k, "stamp": row["stamp"],
                          "alarm": key in alarm_ids, "advisory": key in advisory_ids,
                          "cluster": cluster_record(cluster), "track": result.track.to_dict(),
                          "mount": result.mount, "hits": track.hits, "misses": track.misses,
                          "span_s": track.span_s, "zone_hist": track.zone_hist.copy(),
                          "column_hist": track.column_hist.copy(), "near_hist": track.near_hist.copy(),
                          "hit_hist": track.hit_hist.copy(), "column_held": track.column_held,
                          "near_escalated": track.near_escalated,
                          "association": detector.tracker.observed_associations.get(key),
                          "support": support_stats(xyz, dy, h, idx)}
                if k in schedule[key]:
                    center = track.centroid
                    mask = ((np.abs(xyz[:, 0] - center[0]) <= max(15.0, float(cluster.size[0]) + 8))
                            & (np.abs(dy) <= 7) & (h >= -1.2) & (h <= 6))
                    context = np.flatnonzero(mask)
                    target = np.isin(context, idx)
                    name = f"{piece}_id{key}_{k:04d}.npz"
                    np.savez_compressed(out / "points" / name, xyz=xyz[context], dy=dy[context], h=h[context],
                                        intensity=frame.intensity[context], target=target,
                                        indices=context, rotation=detector.mount_rotation)
                    record["point_snapshot"] = name
                events[key]["timeline"].append(record)
        for event in events.values():
            event["archive_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        all_events.extend(events.values())
        print(f"{piece}: {len(rows)} frames, {len(events)} alarm identities, {len(mismatches)} total mismatches", flush=True)
    report = {"frames": total, "events": all_events, "detection_mismatch_frames": mismatches,
              "method": "Full chronological frozen replay; exact tracker.last point indices; no heuristic bbox target assignment.",
              "limitations": ["Model-relative heights and lateral coordinates are estimates, not independent ground truth.",
                              "Missing-track snapshots are absent; stale last-cluster indices are never used on later frames.",
                              "Same-band local height statistics are diagnostic observations, not an evaluated rejection rule."]}
    (out / "trace.json").write_text(json.dumps(report, indent=1) + "\n")
    if total != 11271 or len(all_events) != 45 or mismatches:
        raise SystemExit("trace does not reproduce the complete frozen ride")


if __name__ == "__main__":
    main()
