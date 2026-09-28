#!/usr/bin/env python3
"""Read-only residual STOP inventory; no detector replay or app/config mutation.

Counts come from fresh_stop_v1 captures. Source-default trace history is explicitly
labelled as such, and is mapped only after archive parity and same-output checks.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml


# Reviewed hypotheses, not physical labels or a proposed detector decision rule.
# Each row retains a concrete positive-obstacle counterexample to its tempting veto.
INVESTIGATIONS = {
    "0:3": ("Ordinary four-ring onset beyond the height reference; prior axis/height demotions.",
            "Inspect height-reference crossings, not ring count.",
            "A tall distant person beyond the fitted floor can have this support; a hard height-reference cap loses range."),
    "0:383": ("Compact vertical onset after column/axis/height history; two separated STOP runs.",
              "Measure localized protrusion against upper context.",
              "Whole-context verticality or column history can hide a person beside a column."),
    "1:74": ("Long full target, but the earlier snapshot study found only 0.19 m strict along-X extent.",
             "Distinguish the intruding strict subset from attached outside support.",
             "Rejecting full-cluster length erases a compact obstacle attached to an outside structure."),
    "1:286": ("Low-to-ordinary-to-low history; six hits in ten frames; only 6/10 matched at onset.",
              "Inspect local height reference and the change of supported footprint.",
              "A partly occluded low object can alternate low and ordinary support; forbidding that transition loses it."),
    "1:292": ("Five-hit low onset after one ordinary hit and one miss; shallow top below same-band reference.",
              "Check independent rail-band height residual at the actual footprint.",
              "A small obstacle against a raised rail can lie below neighboring returns; a same-band-height veto hides it."),
    "1:298": ("6.80 m full target but 0.09 m strict along-X extent in source snapshot study.",
              "Separate localized transverse strict support from its outside connection.",
              "Full-component aspect rejection hides a transverse plank or other localized intrusion."),
    "1:293": ("Distance increases 33.12 to 43.23 m before onset while low/ordinary support switches.",
              "Inspect physical support correspondence; report the receding source fit to tracking owner.",
              "A moving obstacle or newly visible farther part of an occluded object need not fit static approach."),
    "1:310": ("Four left-side low hits precede a broad ordinary fifth hit with 21 strict voxels.",
              "Inspect whether local rail-height bias joins two distinct surface patches.",
              "A lying person or plank spanning a rail can legitimately grow from low support into a broad ordinary cluster."),
    "1:306": ("Five low hits with gaps; 3.8-5.2 cm onset height, below same-band reference.",
              "Compare left/right local reference residuals with nearby right-side events.",
              "A low rail obstruction can have only three voxels; a height or density floor would suppress it."),
    "1:377": ("Ordinary four-ring onset with a clean approaching fit after an axis-range interruption.",
              "Inspect strict footprint and model range history.",
              "More approach consistency cannot separate this event from a real approaching obstacle; a range cap loses recall."),
    "2:81": ("Nearly sensor-stationary elevated target; earlier floating demotions, ordinary onset.",
             "Inspect localized upper-envelope intrusion separately from surrounding vertical context.",
             "A hanging obstacle seen from a stopped train is also stationary; mandatory approach hides it."),
    "2:570": ("Warning edge, low, edge-demoted, low, low matched sequence; exactly 3/5 gauge votes.",
              "Compare low template excess with ordinary edge support at the same footprint.",
              "Forbidding cross-stage confirmation loses a real small obstacle whose sampled top flickers across the gauge floor."),
    "3:266": ("Five-ring compact vertical onset; earlier column/height demotions; coherent approach.",
              "Inspect localized protrusion, retaining the strict body.",
              "Whole-context column rejection hides an attached person or debris, and approach does not distinguish infrastructure."),
    "4:36": ("Seven-ring strict onset while mount remains pending; later zero-strict continuation.",
             "Separate onset geometry from subsequent off-gauge continuation.",
             "Blocking pending calibration suppresses an obstacle immediately after startup; removing holds loses occluded positives."),
    "4:56": ("Low-warning-warning-low-low sequence, exactly 3/5 gauge votes; receding fitted distance.",
             "Inspect footprint migration and local rail-band geometry.",
             "A real low object can present warning side faces between low top hits; same-stage or approach veto delays it."),
    "4:58": ("Approaching low onset: five voxels, 3 cm along-X span, zero raw vertical extent.",
             "Check local reference and single-scan-line surface support without a ring veto.",
             "A real thin low object's sampled top can be flat; demanding volume or multiple rings removes range."),
    "4:209": ("Low onset with rail_slabs=0 and rail_lock=0; five coherent approaching hits within the 40 m cap.",
              "Inspect held low-template reference under absent near rail evidence.",
              "A rail-lock prerequisite hides a close low obstacle where an obstacle itself or a station obscures rails."),
    "4:513": ("Large outside-left cluster; 7/59 strict voxels; four matches with two intervening misses.",
              "Measure local strict edge protrusion, not total component size.",
              "A person or debris at the envelope edge can have a small strict fraction and interrupted visibility."),
    "5:113": ("Three-ring ordinary edge onset; source five-hit approach residual is 0.77 m.",
              "Inspect intruding support despite nearest-point distance jitter.",
              "Nearest points switch on real extended objects; a low-residual requirement shortens detection range."),
    "5:330": ("Four matches with two misses; 10/62 strict voxels; strict subset is long and low.",
              "Inspect local protrusion along the strict low strip.",
              "A plank touching a longer edge must survive; whole-component rejection already has positive counterexamples."),
    "5:358": ("Candidate onset is 7944, one frame later than source; six strict rings, coherent approach.",
              "Use 7944 trace record; never substitute the 7943 onset snapshot.",
              "A stronger onset delay reduces range for a real late-appearing obstacle with flickering strict support."),
    "6:331": ("20/20 strict voxels, nine rings, 1.95 m vertical body; candidate retains only the first run.",
              "Keep this as a localized-body counterexample for geometry rejection.",
              "The connected-context study joins ground returns to this person-like body; long-context rejection hides it."),
    "6:336": ("Compact transverse three-ring face; onset follows axis/height demotions and fits approach.",
              "Inspect model/reference transitions while retaining the compact strict face.",
              "A compact distant obstacle can be intermittently beyond model trust; stricter trust history loses range."),
    "6:518": ("Four-voxel two-ring elevated face; two STOP runs with prior floating and reference demotions.",
              "Inspect small free-body support rather than restoring broad floating rejection.",
              "A small hanging cube is deliberately retained by the compact-body exception; broad floating veto hides it."),
    "7:204": ("Six consecutive low hits; fifth span is 0.499922 s, sixth crosses confirmation time.",
              "Inspect changing local height/axis reference and support footprint.",
              "Extra persistence or stable-model requirements delay a real approaching low object on a curve."),
    "7:215": ("Six hits in ten frames; one prior ordinary hit; coherent approach despite gaps.",
              "Inspect the localized rail-edge support; retain a sparse approaching low positive counterexample.",
              "A same-stage, uninterrupted-hit or wider-shape requirement hides a sparse low obstruction on the rail."),
    "7:264": ("Ordinary single-strict-ring onset; raw channels include outside support; long low cluster.",
              "Inspect strict low protrusion, not a far-thin-path ring gate.",
              "A distant plank or cable may occupy one strict ring; applying a multi-ring veto to ordinary support loses range."),
}


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def provenance(path):
    return {"path": path.resolve().as_posix(), "sha256": digest(path)}


def read_rows(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def runs(numbers):
    """Inclusive runs, including gaps and singleton runs; never span piece resets."""
    result = []
    for n in sorted(set(numbers)):
        if result and n == result[-1][1] + 1:
            result[-1][1] = n
        else:
            result.append([n, n])
    return result


def frame_number(row):
    return int(row["frame_id"].rsplit("_", 1)[1])


def inventory(pieces):
    events, episodes = {}, []
    for piece, rows in pieces.items():
        stop = []
        for index, row in enumerate(rows):
            if row["frame"] != index or row["obstacle"] != bool(row["detections"]):
                raise ValueError(f"{piece}: invalid frame index or STOP flag")
            if index and frame_number(row) != frame_number(rows[index - 1]) + 1:
                raise ValueError(f"{piece}: nonconsecutive global frame IDs")
            ids = [d["id"] for d in row["detections"]]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{piece}: duplicate detection ID")
            if ids:
                stop.append(frame_number(row))
            for detection in row["detections"]:
                events.setdefault(f"{piece}:{detection['id']}", []).append((row, detection))
        episodes.extend({"piece": piece, "global_frame_range": r} for r in runs(stop))
    return events, {"frames": sum(map(len, pieces.values())), "events": len(events),
                    "stop_frames": sum(r["global_frame_range"][1] - r["global_frame_range"][0] + 1
                                       for r in episodes),
                    "track_stop_frames": sum(map(len, events.values())),
                    "episodes": len(episodes), "episode_ranges": episodes}


def support_class(record):
    """Exclusive descriptive classes, not tracker input provenance or physical labels."""
    if record["misses"]:
        return "missed"
    cluster = record["cluster"]
    if cluster["kind"] == "low":
        return "low"
    return "ordinary" if cluster["n_gauge"] > 0 else "off_gauge"


def same_cluster(detection, record):
    """Fresh exact rounded output fingerprint; ID alone cannot establish this join."""
    if record["misses"]:
        return False
    c = record["cluster"]
    projected = {"distance": round(c["distance"], 2), "lateral": round(c["lateral"], 2),
                 "center": [round(v, 2) for v in c["centroid"]],
                 "size": [round(v, 2) for v in c["size"]], "n_points": c["n_voxels"],
                 "height_min": round(c["height_min"], 2), "kind": c["kind"]}
    return all(detection[k] == v for k, v in projected.items())


def capture_semantics(row):
    """Ignore runtime latency only, retaining model, warnings and decision health."""
    out = {k: v for k, v in row.items() if k not in ("timing_ms", "health")}
    health = row["health"]
    out["health"] = {k: v for k, v in health.items()
                     if k not in ("level", "latency_p95_ms", "messages")}
    out["health"]["fault"] = health["level"] == "error"
    out["health"]["messages"] = [m for m in health.get("messages", [])
                                  if not m.startswith("latency p95 ")]
    return out


def config_diff(default, candidate, prefix=""):
    differences = {}
    for key in sorted(default.keys() | candidate.keys()):
        name = f"{prefix}.{key}" if prefix else key
        old, new = default.get(key), candidate.get(key)
        if isinstance(old, dict) and isinstance(new, dict):
            differences.update(config_diff(old, new, name))
        elif old != new:
            differences[name] = {"default": old, "candidate": new}
    return differences


def validate_join(row, detection, base_row, record):
    """IDs are necessary but insufficient: never silently substitute source onset."""
    matches = [d for d in base_row["detections"] if d["id"] == detection["id"]]
    if (len(matches) != 1 or detection != matches[0] or not record["alarm"]
            or record["frame_id"] != row["frame_id"]
            or record["piece_frame"] != row["frame"]
            or record["track"] != row["track"] or record["stamp"] != row["stamp"]):
        raise ValueError(f"unsupported source/candidate join at {row['frame_id']}")
    if record["misses"] == 0 and not same_cluster(detection, record):
        raise ValueError(f"fresh cluster fingerprint mismatch at {row['frame_id']}")


def approach(history, cfg):
    """Diagnostic fit to last matched SOURCE rows, not unrecorded candidate tracker state."""
    fresh = [r for r in history if r["misses"] == 0][-max(2, cfg["approach_hits"]):]
    result = {"source_frames": [r["frame_id"] for r in fresh], "speed_m_s": None,
              "rms_m": None, "passes_numeric_rule": False}
    if len(fresh) < max(2, cfg["approach_hits"]):
        return result
    t = np.array([r["stamp"] for r in fresh], dtype=np.float64)
    d = np.array([r["cluster"]["distance"] for r in fresh], dtype=np.float64)
    t -= t.mean()
    d -= d.mean()
    if float(t @ t) <= 0:
        return result
    slope = float(t @ d / (t @ t))
    rms = float(np.sqrt(np.mean((d - slope * t) ** 2)))
    result.update(speed_m_s=-slope, rms_m=rms,
                  passes_numeric_rule=(-cfg["ego_speed_max"] - 1e-9 <= slope
                                       <= -cfg["approach_min_speed"]
                                       and rms <= cfg["approach_max_residual"]))
    return result


def model_evidence(row, cfg):
    m = row["track"]
    floor = max(m["floor_range"][1] + cfg["track"]["floor_valid_margin"], m["floor_verified"])
    axis = min(m["axis_valid"], cfg["gauge"]["range_max"])
    corridor = axis if cfg["cluster"]["far_min_height"] > 0 else min(axis, floor)
    if cfg["gauge"]["no_rail_range"] > 0 and m["rail_slabs"] == 0:
        corridor = min(corridor, cfg["gauge"]["no_rail_range"])
    return {"model": m, "height_reference_range_m": floor, "axis_range_m": axis,
             "corridor_range_m": corridor, "rail_lock": row["health"]["rail_lock"],
             "monitored_range_m": row["health"]["monitored_range"],
             "health": row["health"],
             "mount": row["mount"]}


def snapshot(path, record):
    """Only current exact target mask; do not recluster context or infer strict membership."""
    if record["misses"]:
        raise ValueError("stale source indices cannot map a snapshot")
    with np.load(path, allow_pickle=False) as data:
        target = data["target"].astype(bool)
        xyz = data["xyz"][target]
        if len(xyz) != record["cluster"]["n_points_idx"]:
            raise ValueError(f"{path}: snapshot target count mismatch")
        unique = np.unique(xyz, axis=0)
        dy, height = data["dy"][target], data["h"][target]
        return {**provenance(path), "frame_id": record["frame_id"],
                "mapping": "fresh source target mask; same rounded candidate cluster and model",
                "raw_target_points": len(xyz), "distinct_xyz": len(unique),
                "xyz_min": xyz.min(axis=0).tolist(), "xyz_max": xyz.max(axis=0).tolist(),
                "xyz_extent": np.ptp(xyz, axis=0).tolist(),
                "rail_relative_dy_range_m": [float(dy.min()), float(dy.max())],
                "rail_relative_height_range_m": [float(height.min()), float(height.max())],
                "strict_mask_recomputed": False}


def onset_history(before):
    """Last ten source frames, including misses; fixed-X model movement is descriptive."""
    x = before[-1]["cluster"]["centroid"][0]
    result = []
    for r in before[-10:]:
        m, c = r["track"], r["cluster"]
        xc = np.clip(x, *m["floor_range"])
        a2, a1, a0 = m["floor_coef"]
        rail_z = (a2 * xc + a1) * xc + a0 + (2 * a2 * xc + a1) * (x - xc) + m["rail_offset"]
        axis_y = m["center"] + np.tan(m["yaw"]) * x + 0.5 * m["curvature"] * x * x
        result.append({"frame_id": r["frame_id"], "hits": r["hits"], "misses": r["misses"],
                       "source_alarm": r["alarm"], "kind": c["kind"], "zone": c["zone"],
                       "reason": c["reason"], "distance_m": c["distance"], "lateral_m": c["lateral"],
                       "height_range_m": [c["height_min"], c["height_max"]],
                       "gauge_voxels": c["n_gauge"], "zone_hist": r["zone_hist"],
                       "hit_hist": r["hit_hist"], "span_s": r["span_s"],
                       "column_hist": r["column_hist"], "column_held": r["column_held"],
                       "near_escalated": r["near_escalated"],
                       "model_at_fixed_onset_x_m": {"x": x, "rail_z": float(rail_z), "axis_y": float(axis_y)}})
    return result


def analyze(root):
    inputs = []

    def load_json(path):
        inputs.append(provenance(path))
        return json.loads(path.read_text(encoding="utf-8"))

    trace = load_json(root / "false_target_trace/trace.json")
    manifest = load_json(root / "new_data_cache_manifest.json")
    audit = load_json(root / "audit.json")
    if digest(root / "new_data_cache_manifest.json") != audit["new_data"]["cache_manifest_sha256"]:
        raise ValueError("cache manifest is not the audited manifest")
    config_path = root / "fresh_stop_v1/config.yaml"
    inputs.append(provenance(config_path))
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg = cfg.get("resense", cfg)
    config_differences = {}
    for directory in ("base", "candidate_defaults_v2"):
        path = root / directory / "config.yaml"
        inputs.append(provenance(path))
        default = yaml.safe_load(path.read_text(encoding="utf-8"))
        default = default.get("resense", default)
        config_differences[directory] = config_diff(default, cfg)
        if default["tracking"].get("fresh_stop_evidence", False):
            raise ValueError(f"{directory}: expected default-off fresh evidence")
    repo = Path(__file__).resolve().parents[1]
    inputs.append(provenance(Path(__file__)))
    for name in ("EXPERIMENT_FRESH_STOP_EVIDENCE.md", "EXPERIMENT_LOW_LOCAL_SUPPORT.md",
                 "EXPERIMENT_FAR_STRUCTURE.md"):
        inputs.append(provenance(repo / "docs" / name))
    if not cfg["tracking"]["fresh_stop_evidence"]:
        raise ValueError("candidate configuration has fresh evidence disabled")
    if cfg["cluster"]["far_axis_both_sides"] != 0:
        raise ValueError("diagnostic model range formula requires far_axis_both_sides=0")
    base, candidate, defaults = {}, {}, {}
    offset = 0
    for k in range(8):
        piece = f"new_data_{k}.jsonl"
        paths = [root / "base" / piece, root / "fresh_stop_v1" / piece,
                 root / "trace_archives" / (piece + ".gz"),
                 root / "candidate_defaults_v2" / piece]
        b, c, archived, d = [read_rows(p) for p in paths]
        inputs.extend(provenance(p) for p in paths)
        if not len(b) == len(c) == len(archived) == len(d):
            raise ValueError(f"{piece}: alignment failure")
        for i, (br, cr, ar, dr) in enumerate(zip(b, c, archived, d)):
            expected = manifest[offset + i]
            for row in (br, cr, ar, dr):
                if (row["frame"] != i or row["frame_id"] + ".npy" != expected["name"]
                        or row["stamp"] != expected["stamp"]):
                    raise ValueError(f"{piece}: audited frame/stamp mismatch")
            if br["detections"] != ar["detections"] or br["track"] != ar["track"]:
                raise ValueError(f"{piece}: source archive/default base parity failure")
            if br["track"] != cr["track"]:
                raise ValueError(f"{piece}: candidate model differs from source")
            if capture_semantics(br) != capture_semantics(dr):
                raise ValueError(f"{piece}: captured defaults/base semantic difference")
        base[piece], candidate[piece], defaults[piece] = b, c, d
        offset += len(b)
    if offset != len(manifest) or trace["frames"] != offset or trace["detection_mismatch_frames"]:
        raise ValueError("trace parity/frame count failure")
    for event in trace["events"]:
        piece, _ = event["key"].split(":")
        if event["archive_sha256"] != digest(root / "trace_archives" / (piece + ".gz")):
            raise ValueError("trace archive hash mismatch")
    be, bs = inventory(base)
    ce, cs = inventory(candidate)
    _, ds = inventory(defaults)
    te = {e["key"]: e for e in trace["events"]}
    if len(te) != len(trace["events"]) or set(te) != set(be) or not set(ce) <= set(be):
        raise ValueError("trace and baseline event identities differ")
    base_support = Counter()
    for key, hits in be.items():
        source = te[key]
        if source["alarm_frame_indices"] != [r["frame"] for r, _ in hits]:
            raise ValueError(f"{key}: trace alarm membership differs from base")
        by_frame = {r["frame_id"]: r for r in source["timeline"]}
        for row, detection in hits:
            record = by_frame[row["frame_id"]]
            validate_join(row, detection, row, record)
            base_support[support_class(record)] += 1
    all_counts, events = Counter(), []
    for key, hits in ce.items():
        source = te[key]
        piece, tid = key.split(":")
        timeline = source["timeline"]
        by_frame = {r["frame_id"]: r for r in timeline}
        if len(by_frame) != len(timeline):
            raise ValueError(f"{key}: duplicate source timeline frame")
        records, snapshots = [], []
        for row, detection in hits:
            record = by_frame[row["frame_id"]]
            base_row = base[piece][row["frame"]]
            validate_join(row, detection, base_row, record)
            fresh = record["misses"] == 0
            kind = support_class(record)
            all_counts[kind] += 1
            entry = {"frame_id": row["frame_id"], "piece_frame": row["frame"],
                     "stamp": row["stamp"], "candidate_detection": detection,
                     "source_support_class": kind, "source_misses": record["misses"],
                     "same_fresh_cluster": fresh, "model_evidence": model_evidence(row, cfg),
                      "source_cluster": record["cluster"],
                      "source_support": record["support"] if fresh else None,
                      "source_observed_ring_ids": record["observed_ring_ids"] if fresh else None}
            if fresh and record.get("point_snapshot"):
                snap = snapshot(root / "false_target_trace/points" / record["point_snapshot"], record)
                snapshots.append(snap)
                entry["snapshot_path"] = snap["path"]
            records.append(entry)
        first = hits[0][0]
        before = [r for r in timeline if r["piece_frame"] <= first["frame"]]
        frames = [frame_number(r) for r, _ in hits]
        base_frames = [frame_number(r) for r, _ in be[key]]
        for r in timeline:
            br = base[piece][r["piece_frame"]]
            if (br["frame_id"] != r["frame_id"] or br["track"] != r["track"]
                    or br["stamp"] != r["stamp"]):
                raise ValueError(f"{key}: source history alignment failure")
        counts = Counter(r["source_support_class"] for r in records)
        cache_entry = manifest[frame_number(first)]
        cache_path = root.parent / "new_data" / cache_entry["name"]
        raw_onset = provenance(cache_path)
        if raw_onset["sha256"] != cache_entry["sha256"]:
            raise ValueError(f"{key}: onset raw cache hash differs from audit")
        event = {"key": key, "physical_surface_identity": "unknown; no surveyed per-surface label",
                 "candidate_stop_frames": len(hits), "candidate_global_frame_ranges": runs(frames),
                 "candidate_piece_frame_ranges": runs([r["frame"] for r, _ in hits]),
                 "first_onset_frame": first["frame_id"], "first_onset_stamp": first["stamp"],
                 "candidate_distance_range_m": [min(d["distance"] for _, d in hits),
                                                max(d["distance"] for _, d in hits)],
                 "base_stop_frames": len(be[key]), "base_global_frame_ranges": runs(base_frames),
                 "removed_global_frames": sorted(set(base_frames) - set(frames)),
                 "support_counts": {k: counts[k] for k in ("ordinary", "low", "missed", "off_gauge")},
                 "source_onset_approach_diagnostic": approach(before, cfg["tracking"]),
                 "raw_onset_cache": {**raw_onset, "rehash_matches_audit": True},
                 "source_last_ten_onset_frames": onset_history(before),
                 "source_pre_onset_reason_counts": dict(Counter(r["cluster"]["reason"] or "none"
                                                                  for r in before if not r["misses"])),
                 "source_pre_onset_demoted_frames": [r["frame_id"] for r in before
                                                      if not r["misses"] and r["cluster"]["demoted"]],
                 "source_pre_onset_history": [r["frame_id"] for r in before],
                  "candidate_stop_records": records, "mapped_fresh_snapshots": snapshots,
                  "source_default_history_reference": {"event_key": key, "rows": len(timeline),
                                                        "input": "false_target_trace/trace.json"}}
        note = INVESTIGATIONS.get(f"{piece.removeprefix('new_data_').removesuffix('.jsonl')}:{tid}")
        if note:
            event["interpretation"] = dict(zip(("observed_mechanism", "investigation_direction",
                                               "valid_obstacle_suppression_risk"), note))
        events.append(event)
    changed = []
    for piece in base:
        changed.extend(b["frame_id"] for b, c in zip(base[piece], candidate[piece])
                       if b["obstacle"] != c["obstacle"])
    return {"schema": "resense-residual-events-v2", "measurement_root": root.resolve().as_posix(),
            "candidate": cs, "base": bs, "captured_defaults": ds,
            "config_differences_from_candidate": config_differences,
            "source_support_counts_on_candidate_stop_frames": dict(all_counts),
            "source_support_counts_on_base_stop_frames": dict(base_support),
            "source_onset_support_counts": dict(Counter(e["candidate_stop_records"][0]["source_support_class"]
                                                        for e in events)),
            "source_onset_approach_counts": dict(Counter(
                "insufficient" if e["source_onset_approach_diagnostic"]["speed_m_s"] is None else
                "pass" if e["source_onset_approach_diagnostic"]["passes_numeric_rule"] else "fail"
                for e in events)),
            "mapped_fresh_snapshot_count": sum(len(e["mapped_fresh_snapshots"]) for e in events),
            "removed_base_event_keys": sorted(set(be) - set(ce)), "stop_decision_changed_frames": changed,
            "removed_base_events": [{"key": key, "track_stop_frames": len(be[key]),
                                     "global_frame_ranges": runs([frame_number(r) for r, _ in be[key]])}
                                    for key in sorted(set(be) - set(ce))],
            "validation": {"audited_frame_stamp_alignment": True,
                           "trace_archive_hashes_match": True,
                           "source_archive_base_detection_and_model_parity": True,
                            "candidate_source_model_parity": True,
                            "captured_defaults_base_semantic_parity": True,
                           "all_retained_candidate_detections_equal_base": True,
                           "all_fresh_mapped_cluster_fingerprints_match": True},
            "approach_thresholds": {k: cfg["tracking"][k] for k in
                                    ("approach_hits", "approach_min_speed", "approach_max_residual", "ego_speed_max")},
            "inputs": inputs, "events": events,
            "limitations": [
                "Counts, distances and STOP membership are candidate capture facts. The trace is source-default, not candidate replay.",
                "Defaults means saved candidate_defaults_v2 outputs, not the concurrently edited working-tree detector.",
                "Rounded output/model equality supports source mapping, not proof of identical hidden candidate tracker state or raw indices.",
                "Missed source rows have stale last clusters: no point snapshot or fresh channel evidence is assigned to them.",
                "Ordinary means fresh non-low with n_gauge>0; off_gauge means fresh non-low n_gauge=0. These are not tracker input-source flags.",
                "Source trace lacks approach/far_evidence/thin_hist, candidate evidence_hist, low bed-template state and opinion probabilities.",
                "Approach uses source last matched hits and receive stamps; it is a numeric diagnostic, not the recorded tracker decision.",
                "Snapshot dy/h are rail-model-relative; reference/union effective strict mask is not reconstructed. Low ring_count is a placeholder.",
                "Raw-channel IDs are not independent sensors, and can include points outside strict support.",
                "Organizer-empty ride establishes false STOPs; individual rails, fasteners, walls or other surfaces remain physically unlabelled.",
                "Raw onset cache bytes are rehashed against the audited manifest; other full-ride cache hashes are recorded audit provenance, not rehashed here."]}


def concise(event):
    first = event["candidate_stop_records"][0]
    c = first["source_cluster"]
    a = event["source_onset_approach_diagnostic"]
    return {"key": event["key"], "frames": event["candidate_global_frame_ranges"],
            "counts": event["support_counts"], "distance": event["candidate_distance_range_m"],
            "onset": {k: c[k] for k in ("kind", "zone", "reason", "n_voxels", "n_gauge", "size",
                                        "height_min", "height_max", "lateral", "ring_count", "rail_line")},
            "support": first["source_support"], "model": first["model_evidence"],
            "approach": a, "reasons": event["source_pre_onset_reason_counts"],
            "snapshots": [s["frame_id"] for s in event["mapped_fresh_snapshots"]]}


def markdown_table(report):
    lines = ["| Event suffix | Candidate STOP frames (inclusive) | N | Onset; min–max m | O/L/M/X | Onset strict/all vox; rings; height m | Onset A/H m; slabs/lock | Approach v/RMS | Onset/history detail |",
             "|---|---|---:|---|---|---|---|---|---|"]
    for e in report["events"]:
        intervals = ", ".join(str(a) if a == b else f"{a}–{b}" for a, b in e["candidate_global_frame_ranges"])
        lo, hi = e["candidate_distance_range_m"]
        counts = "/".join(str(e["support_counts"][k]) for k in ("ordinary", "low", "missed", "off_gauge"))
        first = e["candidate_stop_records"][0]
        c = first["source_cluster"]
        model = first["model_evidence"]
        a = e["source_onset_approach_diagnostic"]
        fit = (f"{a['speed_m_s']:.2f}/{a['rms_m']:.2f} " + ("P" if a["passes_numeric_rule"] else "F")
               if a["speed_m_s"] is not None else "<5 hits")
        trust = (f"{model['axis_range_m']:g}/{model['height_reference_range_m']:g}; "
                  f"{model['model']['rail_slabs']}/{model['rail_lock']:g}")
        rings = "n/a" if c["kind"] == "low" else str(c["ring_count"])
        geometry = (f"{c['n_gauge']}/{c['n_voxels']}; {rings}; "
                    f"{c['height_min']:.3f}–{c['height_max']:.3f}")
        lines.append(f"| `{e['key'].removeprefix('new_data_')}` | {intervals} | {e['candidate_stop_frames']} | "
                      f"{first['candidate_detection']['distance']:.2f}; {lo:.2f}–{hi:.2f} | "
                      f"{counts} | {geometry} | {trust} | {fit} | "
                     f"{e['interpretation']['observed_mechanism']} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--measurement", type=Path,
                        default=Path("D:/Datasets/ReSense/cross_ring_2026-09-28_measurement"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--markdown", type=Path, help="Update only the marked inventory table in an existing report")
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--near-history", action="store_true")
    parser.add_argument("--table", action="store_true")
    args = parser.parse_args(argv)
    report = analyze(args.measurement)
    if args.out:
        args.out.resolve().write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if args.markdown:
        text = args.markdown.read_text(encoding="utf-8")
        begin, end = "<!-- BEGIN GENERATED INVENTORY -->", "<!-- END GENERATED INVENTORY -->"
        if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) >= text.index(end):
            raise ValueError("markdown requires one ordered pair of inventory markers")
        before, rest = text.split(begin)
        _, after = rest.split(end)
        args.markdown.resolve().write_text(before + begin + "\n" + markdown_table(report) + "\n" + end + after,
                                           encoding="utf-8")
    print(json.dumps({k: {a: b for a, b in report[k].items() if a != "episode_ranges"}
                      for k in ("candidate", "base", "source_support_counts_on_candidate_stop_frames")}, indent=2))
    if args.inspect:
        for event in report["events"]:
            print(json.dumps(concise(event)))
    if args.near_history:
        for event in report["events"]:
            if event["candidate_distance_range_m"][1] < 60:
                print(event["key"])
                for r in event["source_last_ten_onset_frames"]:
                    print(json.dumps(r))
    if args.table:
        print(markdown_table(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
