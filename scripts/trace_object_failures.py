#!/usr/bin/env python3
"""Diagnose frozen set O and preregistered novel-placement point survival.

Only the observer is new. No detector/config changes are made. Output decisions must
match an existing frozen replay. The diagnostic timings are intentionally not scored.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from resense import _native  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
from resense.io import load_cache_stamps  # noqa: E402
from resense.pointcloud import COMPACT16_SCALE, compact_to_compact16, pointcloud2_to_structured, structured_to_compact  # noqa: E402
from label_fake_objects import group_frame  # noqa: E402
from novel_placement_eval import cache_path, sha, target_match, transplant, validate_plan  # noqa: E402
from score_clear_distance import decision, overclaim  # noqa: E402
from score_fake_objects import score  # noqa: E402
from trace_detector_stages import TraceDetector  # noqa: E402

RUNNER_SHA256 = sha(__file__)
OBSERVER_SHA256 = sha(ROOT / "scripts/trace_detector_stages.py")


def semantic(row):
    return {key: row.get(key) for key in ("obstacle", "warning", "nearest_distance", "detections", "warnings",
                                        "clear_distance", "track", "mount", "n_candidates", "n_corridor")}


def point_keys(frame):
    """All five quantized cache fields, preserving the detector's point multiset."""
    ring = frame.ring if frame.ring is not None else np.zeros(frame.n)
    values = np.column_stack([np.rint(frame.xyz / COMPACT16_SCALE),
                              np.clip(np.rint(frame.intensity), 0, 255), np.clip(ring, 0, 255)])
    return np.ascontiguousarray(values, dtype=np.int32).view(np.dtype((np.void, 20))).ravel()


def source_indices(cache_keys, source_keys):
    """Match exact quantized rows with multiplicity, never a spatial nearest neighbour.

    When source and background have identical rows, attribution among their equal copies is
    unobservable after cache deduplication. The selected copies have identical XYZ/intensity/
    ring; record the ambiguity rather than counting background copies as extra object points.
    """
    order = np.argsort(cache_keys)
    ordered = cache_keys[order]
    keys, counts = np.unique(source_keys, return_counts=True)
    ids, extra = [], 0
    for key, count in zip(keys, counts):
        lo, hi = np.searchsorted(ordered, key, side="left"), np.searchsorted(ordered, key, side="right")
        if hi - lo < count:
            raise RuntimeError("source return missing from cache's exact quantized multiset")
        ids.extend(order[lo:lo + count].tolist())
        extra += int(hi - lo - count)
    return np.asarray(sorted(ids), dtype=np.int64), extra


def base_record(mode):
    return {"created_utc": datetime.now(timezone.utc).isoformat(), "mode": mode,
            "detector_module": str(sys.modules["resense.detector"].__file__), "native_library": _native.LIBRARY,
            "detector_sha256": sha(ROOT / "resense/detector.py"),
            "observer_sha256": OBSERVER_SHA256,
            "runner_sha256": RUNNER_SHA256,
            "limitations": ["Read-only observer; instrumented latency is not scored.",
                            "Object membership follows explicit source returns, not a detector prediction.",
                            "Existing inspected data; diagnostic results are not a holdout score."]}


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")


def novel(args):
    plan = json.loads(Path(args.plan).read_text())
    validate_plan(plan, args.cache, args.source)
    prior = json.loads(Path(args.baseline).read_text())
    points = np.load(Path(args.source or plan["source"]) / "points.npz")
    cfg = DetectorConfig.from_dict(plan["config"])
    cases = []
    for ci, case in enumerate(plan["cases"]):
        detector, rows = TraceDetector(cfg), []
        for k, path in enumerate(case["background"]):
            frame = frame_from_compact(np.load(cache_path(path, args.cache)), cfg.sensor,
                                       stamp=plan["inputs"][path]["stamp"])
            j = k - plan["warmup_frames"]
            source = (points[f"{case['object']}_{case['source_frames'][j]}"] if j >= 0 else np.zeros((0, 4), np.float32))
            augmented, visible = transplant(frame, source, case["lateral_m"], plan["angular_cell_deg"])
            target_ids = np.arange(augmented.n - len(visible), augmented.n)
            result = detector.process_target(augmented, {case["object"]: target_ids}).to_dict()
            if j < 0:
                continue
            expected = prior["cases"][ci]["rows"][j]
            matched = target_match(result["detections"], detector.calib.apply(visible))
            if matched != expected["target_matched"] or result["obstacle"] != expected["injected_stop"]:
                raise RuntimeError(f"instrumented novel output differs: case {ci}, frame {j}")
            rows.append({"frame": Path(path).name, "source_frame": case["source_frames"][j],
                         "target_matched": matched, "decision": decision(result),
                         "clear_distance": result["clear_distance"], "health": result["health"],
                         "trace": detector.trace})
        record = {key: case[key] for key in ("bag", "object", "lateral_m")}
        record["rows"] = rows
        cases.append(record)
        print(f"novel case {ci + 1}/{len(plan['cases'])}; baseline decisions match", flush=True)
    out = base_record("novel")
    out.update(plan_sha256=sha(args.plan), baseline_sha256=sha(args.baseline), cases=cases,
               cases_verified=len(cases), target_matches=sum(r["target_matched"] for c in cases for r in c["rows"]))
    write(args.out, out)


def seto(args):
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore

    gt = json.loads(Path(args.gt).read_text())
    expected = {int(r["frame"]): r for r in (json.loads(line) for line in Path(args.baseline).read_text().splitlines())}
    cfg = DetectorConfig()
    detector, traces, results, mapping_counts = TraceDetector(cfg), [], [], Counter()
    ts = get_typestore(Stores.ROS2_HUMBLE)
    stamps = load_cache_stamps(str(Path(args.cache) / "cloud_with_fake_obj"))
    with Reader(Path(args.bag)) as reader:
        conns = [c for c in reader.connections if c.msgtype == "sensor_msgs/msg/PointCloud2"]
        for k, (conn, _stamp, raw) in enumerate(reader.messages(connections=conns)):
            st = pointcloud2_to_structured(ts.deserialize_cdr(raw, conn.msgtype))
            xyz = np.column_stack([st[n].ravel() for n in ("x", "y", "z")])
            zero = np.flatnonzero((xyz == 0).all(axis=1))
            if not len(zero):
                raise RuntimeError(f"frame {k}: organizer delimiter missing")
            appended = st[int(zero[-1]) + 1:]
            compact_object = structured_to_compact(appended)
            object_frame = frame_from_compact(compact_object, cfg.sensor)
            # Cache quantization happens before its range filter; near the 2.5/250 m limits
            # this legitimately changes which exact source returns survive into the detector.
            quantized_object = frame_from_compact(compact_to_compact16(compact_object), cfg.sensor)
            groups = sorted(group_frame(object_frame.xyz, 8.0), key=lambda g: object_frame.xyz[g, 0].min())
            quant_groups = list(group_frame(quantized_object.xyz, 8.0))
            labels = sorted(gt.get(f"{k:05d}", []), key=lambda r: r["distance"])
            if len(groups) != len(labels):
                raise RuntimeError(f"frame {k}: {len(groups)} source groups != {len(labels)} labels")
            name = f"cloud_with_fake_obj_{k:04d}"
            path = Path(args.cache) / "cloud_with_fake_obj" / (name + ".npy")
            frame = frame_from_compact(np.load(path), cfg.sensor, stamp=stamps[name])
            keys, object_keys, targets, mapping = point_keys(frame), point_keys(quantized_object), {}, []
            for group, label in zip(groups, labels):
                if len(group) != label["n_points"]:
                    raise RuntimeError(f"frame {k}: source point count differs from label {label['label']}")
                distances = [abs(float(quantized_object.xyz[g, 0].min() - object_frame.xyz[group, 0].min()))
                             for g in quant_groups]
                qgroup = quant_groups.pop(int(np.argmin(distances))) if distances and min(distances) < 2 else np.empty(0, int)
                try:
                    ids, extra = source_indices(keys, object_keys[qgroup])
                except RuntimeError as error:
                    raise RuntimeError(f"frame {k}, {label['label']}: {error}") from error
                mapping.append({"label": label["label"], "source_points": len(group), "cache_points": len(ids),
                                "quantized_range_filter_delta": len(qgroup) - len(group),
                                "indistinguishable_background_copies": extra})
                targets[label["label"]] = ids
                mapping_counts[label["label"]] += len(ids)
            if quant_groups:
                mapping.append({"unlabelled_quantized_groups": [len(g) for g in quant_groups]})
            result = detector.process_target(frame, targets).to_dict()
            result["frame"] = k
            if semantic(result) != semantic(expected[k]):
                raise RuntimeError(f"instrumented set O output differs at frame {k}")
            results.append(result)
            if labels:
                traces.append({"frame": k, "labels": labels, "mapping": mapping,
                               "decision": decision(result), "clear_distance": result["clear_distance"],
                               "health": result["health"], "trace": detector.trace})
            if k % 100 == 0:
                print(f"set O frame {k}; exact baseline output matches", flush=True)
    out = base_record("seto_cache_with_raw_source_identity")
    objs, background = score(results, gt)
    out.update(baseline_sha256=sha(args.baseline), gt_sha256=sha(args.gt), frames_verified=len(results),
               source_point_counts=dict(mapping_counts), objects=objs, background=background,
               clear_distance=overclaim(results, gt), frames=traces)
    write(args.out, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("novel")
    p.add_argument("--plan", required=True)
    p.add_argument("--source")
    p.add_argument("--cache")
    p.add_argument("--baseline", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("seto")
    p.add_argument("--bag", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--gt", default="labels/cloud_with_fake_obj.json")
    p.add_argument("--out", required=True)
    args = parser.parse_args()
    (novel if args.mode == "novel" else seto)(args)


if __name__ == "__main__":
    main()
