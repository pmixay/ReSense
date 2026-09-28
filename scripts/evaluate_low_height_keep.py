#!/usr/bin/env python3
"""Paired raw-bag continuity check and read-only diagnosis of an explicitly selected ROI.

The ROI is used only by the diagnostic observer. The production detector never sees
it. Input schedules retain the original timestamps and never synthesize missing frames.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from detector_freeze import source_digest, source_hashes  # noqa: E402
from regression_gate import labelled_hits  # noqa: E402
from trace_detector_stages import TraceDetector  # noqa: E402
from resense import _native  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.gauge import corridor_coordinates  # noqa: E402
from resense.io import iter_bag_frames  # noqa: E402
from resense.metrics import _assign_detections, gt_objects, load_gt  # noqa: E402


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path):
    with (gzip.open(path, "rt") if str(path).endswith(".gz") else open(path)) as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_gzip(path, rows):
    # Stable compressed bytes, including the header.
    data = "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows).encode()
    Path(path).write_bytes(gzip.compress(data, mtime=0))


def counts(rows, labels):
    gt = load_gt(str(labels))
    unmatched, misses = [], []
    for row in rows:
        gs = [g for g in gt_objects(gt.get(f"{row['frame']:05d}", [])) if g.in_gauge]
        assigned = _assign_detections(row["detections"], gs)
        used = set(assigned.values())
        unmatched.extend({"frame": row["frame"], **d} for j, d in enumerate(row["detections"]) if j not in used)
        misses.extend({"frame": row["frame"], "label": g.label} for j, g in enumerate(gs) if j not in assigned)
    return {"frames": len(rows), "labelled": labelled_hits(list(enumerate(rows)), str(labels)),
            "alarm_frames": sum(bool(r["obstacle"]) for r in rows), "unmatched": unmatched,
            "misses": misses,
            "weak_hit_frames": [r["frame"] for r in rows if any(
                d.get("reason") == "low_height_hold" for d in r["detections"])]}


class HeightTrace(TraceDetector):
    def __init__(self, cfg, roi, frames):
        super().__init__(cfg)
        self.roi, self.frames, self.frame_index = roi, frames, -1

    def _corridor(self, xyz, intensity):
        if self.frame_index in self.frames:
            dy, h = corridor_coordinates(xyz, self.track)
            x0, x1, y0, y1, z0, z1 = self.roi
            ids = np.flatnonzero((xyz[:, 0] >= x0) & (xyz[:, 0] <= x1)
                                 & (dy >= y0) & (dy <= y1) & (h >= z0) & (h <= z1))
            self.target_indices, self.target_groups = ids, {"diagnostic_roi": ids}
            self.trace["target_points"] = len(ids)
        return super()._corridor(xyz, intensity)


def selected(schedule, frame):
    if schedule == "full":
        return True
    if schedule == "half":
        return frame % 2 == 0
    if schedule == "bursty":
        return frame % 6 in (0, 1, 2, 5)
    if schedule.startswith("restart"):
        return frame >= int(schedule.removeprefix("restart"))
    raise ValueError(f"unknown schedule: {schedule}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bag", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=ROOT / "labels/doubleT_obstacle.json")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--schedules", default="full,half,bursty,restart75")
    parser.add_argument("--archive", type=Path, default=ROOT / "docs/evidence/results/p1_raw_continuity_2026-09-28/raw_default.jsonl.gz")
    parser.add_argument("--trace-roi", type=float, nargs=6, default=[55.9, 56.8, -1.3, -0.55, -0.15, 0.45],
                        metavar=("X0", "X1", "DY0", "DY1", "H0", "H1"))
    parser.add_argument("--trace-frames", default="109,110,111,112,115,116,117,118,195,196,197,198")
    args = parser.parse_args()
    names = args.schedules.split(",")
    for name in names:
        selected(name, 0)
    trace_frames = {int(k) for k in args.trace_frames.split(",") if k}
    cfg, candidate = DetectorConfig(), DetectorConfig.from_yaml(str(args.candidate))
    # Preserve the feature-off control when the proposed default becomes enabled.
    cfg.tracking.stop_keep_low_s = 0.0
    if cfg.sensor != candidate.sensor:
        raise ValueError("paired replay requires identical sensor preprocessing")
    args.out.mkdir(parents=True, exist_ok=True)
    files = source_hashes(ROOT)
    report = {"schema": "resense-low-height-replay-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "candidate_status": "provisional; full regression gate and independent reserved evaluation required",
              "source_sha256": source_digest(files), "source_files": files,
              "runner_sha256": sha(__file__), "candidate_file_sha256": sha(args.candidate),
              "config": {"baseline": cfg.to_dict(), "candidate": candidate.to_dict()},
              "bag": {str(path): sha(path) for path in sorted(args.bag.iterdir()) if path.is_file()},
              "labels_sha256": sha(args.labels),
              "runtime": {"python": sys.version, "native": _native.LIBRARY,
                          "packages": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "rosbags")}},
              "diagnostic_roi": args.trace_roi, "diagnostic_frames": sorted(trace_frames),
              "limitations": ["Known development recording, not holdout data.",
                              "Label matches use existing labels and assignment rules.",
                              "Observer timing and concurrent offline timing are not latency measurements."],
              "schedules": {}}
    engines, output, traces = {}, {}, []
    for name in names:
        engines[name] = (HeightTrace(cfg, args.trace_roi, trace_frames) if name == "full" else Detector(cfg),
                         Detector(candidate))
        output[name] = ([], [])
    for k, frame in iter_bag_frames(str(args.bag), cfg.sensor):
        for name, pair in engines.items():
            if not selected(name, k):
                continue
            for index, detector in enumerate(pair):
                if isinstance(detector, HeightTrace):
                    detector.frame_index = k
                    result = detector.process_target(frame, {}).to_dict()
                    if k in trace_frames:
                        traces.append({"frame": k, "trace": detector.trace,
                                       "low_tracks": [{"id": t.id, "misses": t.misses, "reported": t.reported,
                                                       "since_clean": t.since_clean, "centroid": t.centroid.tolist()}
                                                      for t in detector.tracker.tracks if t.last is not None
                                                      and t.last.kind == "low"]})
                else:
                    result = detector.process(frame).to_dict()
                result.update(frame=k, frame_id=frame.frame_id)
                output[name][index].append(result)
        if k % 25 == 0:
            print(f"raw frame {k}; schedules {','.join(names)}", flush=True)
    for name, (baseline, current) in output.items():
        a, b = counts(baseline, args.labels), counts(current, args.labels)
        unmatched_key = lambda r: (r["frame"], r["id"])  # noqa: E731
        previous = {unmatched_key(row) for row in a["unmatched"]}
        entry = {"baseline": a, "candidate": b,
                 "new_unmatched": [r for r in b["unmatched"] if unmatched_key(r) not in previous],
                 "new_labelled_misses": [r for r in b["misses"] if r not in a["misses"]],
                 "inputs": [{"frame": r["frame"], "stamp": r["stamp"]} for r in baseline]}
        entry["passed_no_regression"] = not entry["new_unmatched"] and not entry["new_labelled_misses"]
        entry["files"] = {}
        for variant, rows in (("baseline", baseline), ("candidate", current)):
            path = args.out / f"{name}_{variant}.jsonl.gz"
            write_gzip(path, rows)
            entry["files"][variant] = {"path": path.name, "sha256": sha(path)}
        if name == "full" and args.archive.exists():
            archive = {r["frame"]: r for r in read_rows(args.archive)}
            fields = ("obstacle", "warning", "nearest_distance", "detections", "warnings", "clear_distance", "mount", "n_candidates", "n_corridor")
            mismatches = Counter(key for r in baseline for key in fields if r.get(key) != archive[r["frame"]].get(key))
            entry["archive_comparison"] = {"sha256": sha(args.archive), "fields": fields,
                                           "mismatch_counts": dict(mismatches),
                                           "note": "Unrounded fitted track coefficients are excluded from exact comparison across numerical-library versions."}
        report["schedules"][name] = entry
        print(name, a["labelled"], "->", b["labelled"], "new unmatched", len(entry["new_unmatched"]), flush=True)
    trace_path = args.out / "height_trace.jsonl.gz"
    write_gzip(trace_path, traces)
    report["trace"] = {"path": trace_path.name, "sha256": sha(trace_path)}
    (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
