"""Direct fresh-STOP replay with read-only hit provenance and exact component support.

Every selected piece is warmed from its original reset boundary. Two independent detectors
are replayed: instrumented and plain. Both must match the saved fresh output semantically.
Point indices are frame-local, never cross-frame object identities. Instrumented timing is
not a latency measurement. Run workers in separate processes: descriptor hooks are global.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import ExitStack
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense import clustering, detector as detector_module
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import frame_from_compact
from resense.gauge import corridor_coordinates
from resense.track import TrackModel
from scripts.analyze_quality_candidates import expected_pieces, semantic, validate_piece
from scripts.trace_false_targets import cluster_record

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVENTS = "1:74,1:286,1:292,1:293,1:298,1:310,1:306,5:330,6:331"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonable(value):
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def track_state(t):
    names = ("id", "centroid", "velocity", "hits", "misses", "age", "confidence", "span_s",
             "gauge_hits", "zone_hist", "hit_hist", "column_hist", "near_hist", "hold",
             "reported", "seen_reported", "kept", "since_clean", "evidence_hist", "stop_earned",
             "fresh_blocked", "thin_hist", "approach", "far_evidence", "was_stop", "approach_block",
             "obs", "doubt", "withheld", "stop_prev", "zone", "rule_zone", "vote_zone")
    return jsonable({name: getattr(t, name) for name in names})


def interval(values):
    return [float(np.min(values)), float(np.max(values))] if len(values) else None


def gap(a, b):
    if a is None or b is None:
        return None
    return max(0.0, b[0] - a[1], a[0] - b[1])


def common_reference(previous, current):
    """Reproject both visible subsets under the current mount rotation and rail model.

    This removes coordinate-reference differences, not train motion. There is no external
    pose/odometry or point correspondence here; it is NOT registration or object identity.
    """
    a, b = previous["support"], current["support"]
    if a is None or b is None:
        raise ValueError("current support required on both matched observations")
    old_xyz = np.asarray(a["xyz"], float)
    new_xyz = np.asarray(b["xyz"], float)
    ra, rb = np.asarray(previous["rotation"]), np.asarray(current["rotation"])
    old_common = old_xyz @ ra @ rb.T
    tm = TrackModel(**current["model"])
    old_dy, old_h = corridor_coordinates(old_common, tm)
    new_dy, new_h = corridor_coordinates(new_xyz, tm)
    old_own_dy, old_own_h = corridor_coordinates(old_xyz, TrackModel(**previous["model"]))
    out = {"previous_frame": previous["frame_id"], "frame": current["frame_id"],
           "dt_s": (current["stamp"] - previous["stamp"]
                    if current.get("stamp") is not None and previous.get("stamp") is not None else None),
           "mount_changed": not np.array_equal(ra, rb),
           "ego_translation_applied": False, "identity_established": False,
           "old_reference_delta_on_old_points": {
               "dy": interval(old_dy - old_own_dy), "h": interval(old_h - old_own_h)}}
    for name, ma, mb in (("whole", np.ones(len(old_xyz), bool), np.ones(len(new_xyz), bool)),
                         ("stage_strict", np.asarray(a["strict"], bool), np.asarray(b["strict"], bool))):
        # stage_strict for low support is stage eligibility, NOT polygon membership.
        out[name] = {
            "points": [int(ma.sum()), int(mb.sum())],
            "common_sensor_y_gap_m": gap(interval(old_common[ma, 1]), interval(new_xyz[mb, 1])),
            "common_sensor_z_gap_m": gap(interval(old_common[ma, 2]), interval(new_xyz[mb, 2])),
            "common_rail_dy_gap_m": gap(interval(old_dy[ma]), interval(new_dy[mb])),
            "common_rail_h_gap_m": gap(interval(old_h[ma]), interval(new_h[mb])),
            "own_rail_dy_gap_m": gap(interval(old_own_dy[ma]), interval(new_dy[mb])),
            "own_rail_h_gap_m": gap(interval(old_own_h[ma]), interval(new_h[mb])),
        }
    return out


class SupportTraceDetector(Detector):
    """Observe real arguments/results; do not approximate the detector or modify its state."""

    def process_observed(self, frame, selected=()):
        self.selected = set(selected)
        self.components = {}
        self.inputs = []
        self.notes = {}
        self.fresh_checks = {}
        self.before = {}
        self.input_stage = None
        self.ranges = None
        self.corridor = None
        self.active = bool(selected)
        result = super().process(frame)
        records = []
        if not self.active:
            return result, records
        for t in self.tracker.tracks:
            if t.id not in self.selected or t.last is None:
                continue
            record = {"frame_id": frame.frame_id, "stamp": frame.stamp,
                      "id": t.id, "model": jsonable(asdict(result.track)), "mount": result.mount,
                      "rotation": self.mount_rotation.tolist(), "effective_ranges": self.ranges,
                      "before": self.before.get(t.id), "after": track_state(t),
                      "hit": self.notes.get(t.id), "fresh_gate_calls": self.fresh_checks.get(t.id, []),
                      "alarm": any(d.id == t.id for d in result.detections),
                      "cluster": dict(cluster_record(t.last), weak=t.last.weak),
                      "support": None, "component": None}
            if t.misses == 0:
                idx = np.asarray(t.last.points_idx)
                if np.any((idx < 0) | (idx >= frame.n)):
                    raise ValueError("invalid current-frame point identity")
                capture = self.components.get(id(t.last))
                if capture is None:
                    raise ValueError(f"unobserved descriptor source for selected fresh track {t.id}")
                component = capture[1]
                frame_idx = np.asarray(component["frame_idx"])
                mask = np.isin(frame_idx, idx) & (frame_idx >= 0)
                if set(frame_idx[mask]) != set(idx) or int(mask.sum()) != len(idx):
                    raise ValueError("descriptor/current support membership mismatch")
                record["component"] = component
                record["support"] = {name: np.asarray(component[name])[mask].tolist()
                                     for name in ("xyz", "frame_idx", "dy", "h", "strict", "rail_strict",
                                                  "dy_rail", "voxel_ids", "ring", "intensity")}
                record["support"]["configured_xyz"] = frame.xyz[frame_idx[mask]].tolist()
                record["support"]["mask_meaning"] = component["mask_meaning"]
                record["support"]["corridor_member"] = np.isin(frame_idx[mask], self.corridor[0]).tolist()
                record["support"]["corridor_strict"] = np.isin(frame_idx[mask], self.corridor[1]).tolist()
                record["component"]["output_member"] = mask.tolist()
                n_vox = len(np.unique(np.asarray(component["voxel_ids"])[mask]))
                strict = np.asarray(component["strict"], bool)
                n_strict = len(np.unique(np.asarray(component["voxel_ids"])[mask & strict]))
                if not component["historical_points"] and (n_vox != t.last.n or n_strict != t.last.n_gauge):
                    raise ValueError(f"exact voxel support mismatch {t.id}: {n_vox}/{n_strict}")
            records.append(record)
        return result, records

    def _corridor(self, xyz, intensity):
        out = super()._corridor(xyz, intensity)
        if self.active:
            cand = out[0]
            self.corridor = (cand.idx.copy(), cand.idx[cand.in_gauge].copy())
            self.ranges = list(map(float, out[4]))
        return out

    def _cluster(self, *args):
        if not self.active:
            return super()._cluster(*args)
        stage_function = detector_module._clusters_of

        def stage(c, cfg, **kw):
            previous = self.input_stage
            self.input_stage = (c, cfg, kw)
            try:
                return stage_function(c, cfg, **kw)
            finally:
                self.input_stage = previous

        def observer(fn):
            signature = inspect.signature(fn)

            def run(*a, **kw):
                bound = signature.bind(*a, **kw)
                bound.apply_defaults()
                p = bound.arguments
                output = fn(*a, **kw)
                if output is not None:
                    c, cfg, stage_kw = self.input_stage
                    b = p["b"]
                    ids = b.idx
                    inv = p.get("inv")
                    if inv is None:
                        _, inv = clustering.voxelize(c.xyz, cfg)
                    params = {k: v for k, v in p.items() if k in (
                        "factor", "factor_range", "axis_valid", "height_valid", "keep_thin", "weak_from")}
                    params.update({k: stage_kw[k] for k in ("axis_valid", "height_valid") if k in stage_kw})
                    record = {"function": fn.__name__, "cfg": asdict(cfg), "parameters": params,
                              "gauge": None if p.get("gauge") is None else asdict(p["gauge"]),
                              "low_cfg": None if p.get("low_cfg") is None else asdict(p["low_cfg"]),
                              "mask_meaning": "low_stage_eligibility" if p.get("low_cfg") else "effective_corridor",
                              "xyz": b.pts.copy(), "frame_idx": c.idx[ids].copy(),
                              "dy": c.dy[ids].copy(), "h": c.h[ids].copy(),
                              "strict": c.in_gauge[ids].copy(), "rail_strict": c.rail()[ids].copy(),
                              "dy_rail": c.lateral_rail()[ids].copy(), "voxel_ids": inv[ids].copy(),
                              "intensity": c.intensity[ids].copy(),
                              "ring": np.full(len(ids), -1) if c.ring is None else c.ring[ids].copy(),
                              "dy_alt": None if p.get("dy_alt") is None else p["dy_alt"][ids].copy(),
                              "historical_points": int((c.idx[ids] < 0).sum())}
                    # Hold the output object to prevent ID reuse. Outer component context wins
                    # after a recursive strict split; output membership is stored separately.
                    self.components[id(output)] = (output, jsonable(record))
                return output
            return run

        with ExitStack() as stack:
            stack.enter_context(patch.object(detector_module, "_clusters_of", stage))
            for name in ("_corridor_cluster", "_low_cluster"):
                stack.enter_context(patch.object(clustering, name, observer(getattr(clustering, name))))
            return super()._cluster(*args)

    def _confirm(self, *args):
        if not self.active:
            return super()._confirm(*args)
        self.before = {t.id: track_state(t) for t in self.tracker.tracks if t.id in self.selected}
        original_note = self.tracker._note
        original_check = self.tracker._fresh_stop_ok

        def note(t, cl, far_thin, zw, source="ordinary"):
            prior = list(t.evidence_hist)
            answer = original_note(t, cl, far_thin, zw, source)
            if t.id in self.selected:
                self.notes[t.id] = {"input_source": source, "far_thin_argument": bool(far_thin),
                                    "evidence_before": prior, "evidence_after": list(t.evidence_hist)}
            return answer

        def check(t):
            answer = original_check(t)
            if t.id in self.selected:
                self.fresh_checks.setdefault(t.id, []).append(bool(answer))
            return answer

        with patch.object(self.tracker, "_note", note), patch.object(self.tracker, "_fresh_stop_ok", check):
            return super()._confirm(*args)


def replay_piece(job):
    measurement, cache, out, piece, requests, expected = job
    capture = measurement / "fresh_stop_v1" / (piece + ".jsonl")
    rows = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines()]
    validate_piece(piece, rows, expected)
    cfg = DetectorConfig.from_yaml(str(measurement / "fresh_stop_v1/config.yaml"))
    if not cfg.tracking.fresh_stop_evidence:
        raise ValueError("fresh STOP configuration required")
    stop = max(v[1] for v in requests.values())
    plain, traced = Detector(cfg), SupportTraceDetector(DetectorConfig.from_dict(cfg.to_dict()))
    timelines = {i: [] for i in requests}
    provenance = []
    for k, row in enumerate(rows[:stop + 1]):
        path = cache / expected[k]["name"]
        digest = sha(path)
        if digest != expected[k]["sha256"]:
            raise ValueError(f"audited cache hash mismatch: {path}")
        frame = frame_from_compact(np.load(path), cfg.sensor, stamp=row["stamp"], frame_id=row["frame_id"])
        if not np.isfinite(frame.xyz).all():
            raise ValueError("nonfinite frame would require a separate source-index mapping")
        selected = [i for i, (start, end) in requests.items() if start <= k <= end]
        result, records = traced.process_observed(frame, selected)
        reference = plain.process(frame).to_dict()
        actual = result.to_dict()
        for output in (actual, reference):
            output.update(frame=k, frame_id=row["frame_id"])
        if semantic(actual) != semantic(reference):
            raise ValueError(f"instrumentation semantic mismatch: {row['frame_id']}")
        if semantic(reference) != semantic(row):
            raise ValueError(f"saved fresh semantic mismatch: {row['frame_id']}")
        for record in records:
            record["piece_frame"] = k
            timelines[record["id"]].append(record)
        provenance.append({"name": path.name, "sha256": digest})
        if k % 250 == 0:
            print(f"{piece}: {k + 1}/{stop + 1} paired frames", flush=True)
    events = []
    for key, timeline in timelines.items():
        matched = [r for r in timeline if r["support"] is not None]
        wanted = [r["frame_id"] for r in rows if any(d["id"] == key for d in r["detections"])]
        got = [r["frame_id"] for r in timeline if r["alarm"]]
        if wanted != got:
            raise ValueError(f"selected event coverage mismatch: {piece}:{key}")
        events.append({"key": f"{piece}.jsonl:{key}", "timeline": timeline,
                       "transitions": [common_reference(a, b) for a, b in zip(matched, matched[1:])]})
    report = {"piece": piece, "paired_frames": stop + 1, "capture_sha256": sha(capture),
              "cache_hashes": provenance, "config": cfg.to_dict(), "events": events,
              "instrumentation_semantic_mismatches": 0, "saved_fresh_semantic_mismatches": 0}
    path = out / f"{piece}.json"
    path.write_text(json.dumps(report, allow_nan=False) + "\n", encoding="utf-8")
    return {"piece": piece, "path": str(path), "sha256": sha(path), "paired_frames": stop + 1,
            "events": len(events), "observations": sum(len(e["timeline"]) for e in events),
            "stop_track_frames": sum(r["alarm"] for e in events for r in e["timeline"])}


def completed_piece(path, piece, requests, expected):
    """Reuse only a fully written, already paired prefix from an interrupted long run."""
    record = json.loads(path.read_text(encoding="utf-8"))
    stop = max(v[1] for v in requests.values())
    keys = {f"{piece}.jsonl:{key}" for key in requests}
    if (record["piece"] != piece or record["paired_frames"] != stop + 1
            or record["instrumentation_semantic_mismatches"]
            or record["saved_fresh_semantic_mismatches"]
            or len(record["cache_hashes"]) != stop + 1
            or {e["key"] for e in record["events"]} != keys
            or any(got["name"] != wanted["name"] or got["sha256"] != wanted["sha256"]
                   for got, wanted in zip(record["cache_hashes"], expected, strict=False))):
        raise ValueError(f"existing prefix cannot be resumed: {path}")
    events = record["events"]
    return {"piece": piece, "path": str(path), "sha256": sha(path), "paired_frames": stop + 1,
            "events": len(events), "observations": sum(len(e["timeline"]) for e in events),
            "stop_track_frames": sum(r["alarm"] for e in events for r in e["timeline"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--events", default=DEFAULT_EVENTS)
    parser.add_argument("--all-retained", action="store_true",
                        help="select all 27 identities in the audited fresh residual inventory")
    parser.add_argument("--resume", action="store_true", help="validate and reuse completed piece files")
    parser.add_argument("--jobs", type=int, default=3)
    args = parser.parse_args()
    if not args.out.parent.is_dir():
        parser.error("output parent must exist")
    args.out.mkdir(exist_ok=True)
    source_path = args.measurement / "false_target_trace/trace.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    lookup = {e["key"]: e for e in source["events"]}
    pieces, audited = expected_pieces(args.measurement)
    requests = {}
    if args.all_retained:
        inventory_path = ROOT / "docs/evidence/results/residual_events_2026-09-28.json"
        keys = json.loads(inventory_path.read_text(encoding="utf-8"))["events"]
        if len(keys) != 27:
            raise ValueError("unexpected retained event inventory size")
        event_texts = [event["key"].removeprefix("new_data_").replace(".jsonl", "") for event in keys]
    else:
        event_texts = args.events.split(",")
    for text in event_texts:
        piece_number, track = map(int, text.split(":"))
        piece = f"new_data_{piece_number}"
        rows = lookup[f"{piece}.jsonl:{track}"]["timeline"]
        # Source trace is used ONLY to schedule capture, never to attribute fresh support.
        requests.setdefault(piece, {})[track] = (max(0, min(r["piece_frame"] for r in rows) - 2),
                                                  min(len(pieces[piece]) - 1,
                                                      max(r["piece_frame"] for r in rows) + 2))
    jobs = [(args.measurement, args.cache, args.out, piece, req, pieces[piece])
            for piece, req in requests.items()]
    results, pending = {}, []
    for job in jobs:
        _, _, out, piece, req, expected = job
        path = out / f"{piece}.json"
        if args.resume and path.is_file():
            results[piece] = completed_piece(path, piece, req, expected)
        else:
            pending.append(job)
    if pending:
        with ProcessPoolExecutor(max_workers=args.jobs) as executor:
            for result in executor.map(replay_piece, pending):
                results[result["piece"]] = result
    results = [results[part] for part in requests]
    paths = [Path(__file__), ROOT / "resense/detector.py", ROOT / "resense/tracking.py",
             ROOT / "resense/clustering.py", ROOT / "resense/config.py", ROOT / "resense/gauge.py",
             args.measurement / "fresh_stop_v1/config.yaml", source_path]
    if args.all_retained:
        paths.append(ROOT / "docs/evidence/results/residual_events_2026-09-28.json")
    report = {"schema": "direct-fresh-support-v1", "pieces": results, "audited": audited,
              "source_sha256": {str(p): sha(p) for p in paths},
              "paired_frames": sum(r["paired_frames"] for r in results),
              "scope": "selected piece prefixes, warmed from original reset; not full ride",
              "coordinates": "current mount + rail reference; no ego translation or physical identity",
              "provenance": "direct tracker calls and descriptor inputs; no defaults-to-fresh mapping"}
    (args.out / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
