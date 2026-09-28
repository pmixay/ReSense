#!/usr/bin/env python3
"""Four-config, common-source replay of the known 201-frame positive recording.

Source selection is explicit. Every variant receives an independent copy of each original
raw frame. Labels only enter the observer, never the detector. This is development evidence.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

VARIANTS = {"both_off": (0.0, False), "continuation_only": (0.3, False),
            "onset_only": (0.0, True), "both_on": (0.3, True)}
PAIRS = (("both_off", "continuation_only"), ("both_off", "onset_only"),
         ("continuation_only", "both_on"), ("onset_only", "both_on"))


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_native(library, status, expected, root):
    if not library or not status.startswith("native ("):
        raise ValueError("expected native backend is not active")
    path = Path(library).resolve()
    if not path.is_relative_to(root.resolve() / "resense") or sha(path) != expected:
        raise ValueError("native binary origin/hash does not match the declared runtime")
    return path


def intervals(frames):
    out = []
    for frame in frames:
        if out and frame == out[-1][1] + 1:
            out[-1][1] = frame
        else:
            out.append([frame, frame])
    return out


def validate_alignment(variants, expected):
    identities = None
    for name, rows in variants.items():
        current = [(r["frame"], r["stamp"], r["frame_id"]) for r in rows]
        if [r[0] for r in current] != list(range(expected)):
            raise ValueError(f"incomplete or reordered raw frames: {name}")
        if any(b[1] <= a[1] for a, b in zip(current, current[1:])):
            raise ValueError(f"non-increasing raw timestamps: {name}")
        if identities is not None and current != identities:
            raise ValueError(f"variant input identities differ: {name}")
        identities = current
    return identities


def analyse(rows, gt, gt_objects, assign):
    targets, unmatched, matched_ids, tracks = {}, [], set(), {}
    for row in rows:
        for det in row["detections"]:
            tracks.setdefault(det["id"], []).append(row["frame"])
        objects = [g for g in gt_objects(gt.get(f"{row['frame']:05d}", [])) if g.in_gauge]
        if len({g.label for g in objects}) != len(objects):
            raise ValueError("observer requires unique labels within each frame")
        matches = assign(row["detections"], objects)
        used = set(matches.values())
        row["label_matches"] = [{"label": objects[gi].label, "detection_index": di,
                                  "detection_id": row["detections"][di]["id"]}
                                 for gi, di in sorted(matches.items())]
        for gi, g in enumerate(objects):
            item = targets.setdefault(g.label, {"visible_frames": [], "matched_frames": [], "missed_frames": []})
            item["visible_frames"].append(row["frame"])
            item["matched_frames" if gi in matches else "missed_frames"].append(row["frame"])
            if gi in matches:
                matched_ids.add(row["detections"][matches[gi]]["id"])
        row["unmatched_detection_indices"] = [j for j in range(len(row["detections"])) if j not in used]
        unmatched.extend({"frame": row["frame"], "stamp": row["stamp"], **d}
                         for j, d in enumerate(row["detections"]) if j not in used)
    for target in targets.values():
        target.update(hits=len(target["matched_frames"]), frames=len(target["visible_frames"]),
                      first_stop_frame=next(iter(target["matched_frames"]), None),
                      stop_intervals=intervals(target["matched_frames"]),
                      missed_intervals=intervals(target["missed_frames"]))
    rail = targets.get("object_on_rail", {})
    alarms = [r["frame"] for r in rows if r["obstacle"]]
    return {"targets": targets, "alarm_frames": len(alarms), "alarm_intervals": intervals(alarms),
            "object_on_rail_from_frame_75": {
                "hits": sum(k >= 75 for k in rail.get("matched_frames", [])),
                "frames": sum(k >= 75 for k in rail.get("visible_frames", []))},
            "unmatched_detections": unmatched,
            "unmatched_detection_count": len(unmatched),
            "unmatched_frame_count": len({r["frame"] for r in unmatched}),
            "never_matched_stop_track_ids": sorted({r["id"] for r in unmatched} - matched_ids),
            "stop_tracks": [{"id": ident, "first_stop_frame": frames[0],
                             "stop_frames": frames, "stop_intervals": intervals(frames),
                             "ever_matched_label": ident in matched_ids}
                            for ident, frames in sorted(tracks.items())],
            "weak_hit_frames": [r["frame"] for r in rows if any(
                d.get("reason") == "low_height_hold" for d in r["detections"])]}


def unmatched_pairs(old, new):
    """One-to-one physical pairing; track IDs alone never establish cross-run equivalence."""
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    costs = np.full((len(new), len(old) + len(new)), len(new) + 1.0)
    for j, current in enumerate(new):
        for i, previous in enumerate(old):
            dx, dy = abs(current["distance"] - previous["distance"]), abs(current["lateral"] - previous["lateral"])
            if current.get("kind", "") == previous.get("kind", "") and dx <= 0.5 and dy <= 0.25:
                costs[j, i] = dx + dy
    a, b = linear_sum_assignment(costs)
    matched = {int(j): int(i) for j, i in zip(a, b) if i < len(old) and costs[j, i] <= 0.75}
    return matched


def compare(old, new):
    changes, added_unmatched = [], []
    for before, after in zip(old, new):
        a = {m["label"] for m in before["label_matches"]}
        b = {m["label"] for m in after["label_matches"]}
        if a != b:
            changes.append({"frame": before["frame"], "stamp": before["stamp"],
                            "lost_labels": sorted(a - b), "gained_labels": sorted(b - a)})
        prev = [before["detections"][i] for i in before["unmatched_detection_indices"]]
        curr = [after["detections"][i] for i in after["unmatched_detection_indices"]]
        pairs = unmatched_pairs(prev, curr)
        added_unmatched.extend({"frame": after["frame"], **d} for i, d in enumerate(curr) if i not in pairs)
    return {"label_changes": changes, "new_unmatched_detections": added_unmatched,
            "lost_label_frames": sum(len(r["lost_labels"]) for r in changes),
            "gained_label_frames": sum(len(r["gained_labels"]) for r in changes),
            "passed_frame_recall_and_no_new_unmatched": not added_unmatched and not any(r["lost_labels"] for r in changes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--expect-commit", required=True)
    parser.add_argument("--expect-native-sha256", required=True)
    parser.add_argument("--bag", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    sys.path[:0] = [str(root), str(root / "scripts")]
    from detector_freeze import source_hashes, source_digest, _scope
    from resense import _native
    import resense.detector
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.io import iter_bag_frames
    from resense.metrics import _assign_detections, gt_objects, load_gt
    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "")
        filename = getattr(module, "__file__", None)
        if name.startswith("resense.") and filename and not Path(filename).resolve().is_relative_to(root / "resense"):
            raise ValueError(f"imported detector module outside selected source: {name} {filename}")
    native_path = validate_native(_native.LIBRARY, _native.status(), args.expect_native_sha256, root)
    native_sha = sha(native_path)
    def git(*cmd):
        return subprocess.check_output(["git", "-C", str(root), *cmd])
    if git("rev-parse", "HEAD").decode().strip() != args.expect_commit:
        raise ValueError("selected source HEAD does not match expected commit")
    files = source_hashes(root)
    committed = {p for p in git("ls-tree", "-r", "--name-only", args.expect_commit).decode().splitlines() if _scope(p)}
    if committed != set(files):
        raise ValueError("source inventory differs from expected commit")
    for path, checksum in files.items():
        if hashlib.sha256(git("show", f"{args.expect_commit}:{path}")).hexdigest() != checksum:
            raise ValueError(f"production file differs from expected commit: {path}")
    runner_sha = sha(__file__)
    observer_hashes = {"detector_freeze.py": sha(root / "scripts/detector_freeze.py")}
    labels = args.labels or root / "labels/doubleT_obstacle.json"
    labels_sha = sha(labels)
    label_payload = json.loads(labels.read_text())
    if label_payload["_meta"]["frames"] != 201 or label_payload["_meta"]["bag"] != "doubleT_obstacle":
        raise ValueError("expected original 201-frame doubleT_obstacle labels")
    gt = load_gt(str(labels))
    inputs = {p.name: sha(p) for p in sorted(args.bag.iterdir()) if p.is_file()}
    if not any(p.endswith(".db3") for p in inputs):
        raise ValueError("original raw bag required")
    configs, engines, outputs = {}, {}, {}
    base = DetectorConfig.from_yaml(str(root / "configs/default.yaml"))
    for name, (continuation, onset) in VARIANTS.items():
        cfg = deepcopy(base)
        cfg.tracking.stop_keep_low_s = continuation
        cfg.tracking.fresh_stop_evidence = onset
        cfg.cluster.weak_min_rings = 0
        cfg.tracking.far_min_ring_count = 0
        cfg.lowobj.local_support_enabled = False
        configs[name] = {"effective": cfg.to_dict(), "sha256": digest(cfg.to_dict())}
        engines[name], outputs[name] = Detector(cfg), []
    print(json.dumps({"commit": args.expect_commit, "source_sha256": source_digest(files),
                      "import": resense.detector.__file__, "native": str(native_path),
                      "configs": {k: v["sha256"] for k, v in configs.items()}}), flush=True)
    manifest = []
    for index, frame in iter_bag_frames(str(args.bag), base.sensor):
        parts = {key: None if getattr(frame, key) is None else hashlib.sha256(getattr(frame, key).tobytes()).hexdigest()
                 for key in ("xyz", "intensity", "ring")}
        manifest.append({"frame": index, "stamp": frame.stamp, "frame_id": frame.frame_id,
                         "points": frame.n, "arrays_sha256": parts})
        for name, detector in engines.items():
            result = detector.process(deepcopy(frame)).to_dict()
            if result["stamp"] != frame.stamp:
                raise ValueError("detector output timestamp differs from input")
            result.update(frame=index, frame_id=frame.frame_id)
            outputs[name].append(result)
        if index % 25 == 0:
            print(f"raw frame {index}; four sequential variants", flush=True)
    validate_alignment(outputs, 201)
    if source_hashes(root) != files or sha(__file__) != runner_sha or sha(labels) != labels_sha:
        raise ValueError("source, observer, or labels changed during replay")
    if any(sha(root / "scripts" / path) != checksum for path, checksum in observer_hashes.items()):
        raise ValueError("observer dependency changed during replay")
    if native_path and sha(native_path) != native_sha:
        raise ValueError("native implementation changed during replay")
    if {p.name: sha(p) for p in sorted(args.bag.iterdir()) if p.is_file()} != inputs:
        raise ValueError("raw input changed during replay")
    report = {"schema": "resense-four-config-raw-positive-v1", "created_utc": datetime.now(timezone.utc).isoformat(),
              "source": {"commit": args.expect_commit, "sha256": source_digest(files), "files": files,
                         "import": resense.detector.__file__, "unchanged_at_end": True},
              "runner_sha256": runner_sha, "observer_dependencies": observer_hashes,
              "inputs": {"bag": str(args.bag), "files": inputs, "labels_sha256": labels_sha,
                         "manifest_sha256": digest(manifest), "manifest": manifest},
              "runtime": {"python": sys.version, "native": str(native_path), "native_sha256": native_sha,
                          "backend_status": _native.status(),
                          "packages": {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "rosbags")},
                          "thread_env": {p: os.environ.get(p) for p in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")}},
              "configs": configs, "variants": {}, "pairs": {},
              "limitations": ["Known development recording; not unseen/holdout data.",
                              "Existing labels and matching tolerance; unmatched means unmatched to those labels.",
                              "Concurrent full gate: all timings diagnostic, not deployment or comparative latency.",
                              "Partial acceptance only: other bags, ride, O/F and history still required for opt-in candidates."]}
    args.out.mkdir(parents=True, exist_ok=True)
    for name, rows in outputs.items():
        report["variants"][name] = analyse(rows, gt, gt_objects, _assign_detections)
        path = args.out / f"{name}.jsonl.gz"
        path.write_bytes(gzip.compress("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in rows).encode(), mtime=0))
        report["variants"][name]["capture"] = {"path": path.name, "sha256": sha(path), "frames": len(rows)}
    for before, after in PAIRS:
        report["pairs"][f"{before}__{after}"] = compare(outputs[before], outputs[after])
    (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: {"targets": {n: [v["hits"], v["frames"]] for n, v in r["targets"].items()},
                           "unmatched": r["unmatched_detection_count"]} for k, r in report["variants"].items()}), flush=True)


if __name__ == "__main__":
    main()
