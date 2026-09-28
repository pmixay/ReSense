"""Compare direct fresh histories and label-blind local parts using exact descriptor inputs."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

import numpy as np

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from resense.clustering import _Blob, _corridor_cluster
from resense.config import ClusterConfig, GaugeConfig
from scripts.analyze_local_body_support import RuntimeSupport, MODES, geometry, local_parts
from scripts.trace_fresh_support import common_reference, jsonable, sha


def runtime_support(component):
    if component["mask_meaning"] != "effective_corridor":
        raise ValueError("low-stage eligibility is not an effective corridor mask")
    xyz = np.asarray(component["xyz"], np.float32)
    return RuntimeSupport(xyz, np.asarray(component["dy"]), np.asarray(component["h"]),
                          np.asarray(component["strict"], bool), np.ones(len(xyz), bool),
                          np.asarray(component["frame_idx"]), np.asarray(component["voxel_ids"]),
                          "direct_actual_effective_corridor", component["parameters"]["axis_valid"],
                          component["parameters"]["height_valid"])


def exact_descriptor(component, ids):
    """Keep all real descriptor inputs, including intensity/rails/reference/weak provenance."""
    s = runtime_support(component)
    if not len(ids):
        return None
    b = _Blob.of(s.xyz, np.asarray(ids, int), len(np.unique(s.inv[ids])))

    def array(key, dtype=None):
        value = component.get(key)
        return None if value is None else np.asarray(value, dtype=dtype)

    c = _corridor_cluster(
        b, s.dy, s.h, s.strict, array("intensity", np.float32), s.inv, s.frame_idx,
        ClusterConfig(**component["cfg"]), **component["parameters"],
        gauge=None if component["gauge"] is None else GaugeConfig(**component["gauge"]),
        dy_alt=array("dy_alt"), in_rail=array("rail_strict", bool),
        dy_report=array("dy_rail"), ring=array("ring", np.int64),
    )
    if c is None:
        return None
    return {"zone": c.zone, "reason": c.reason, "voxels": c.n, "gauge_voxels": c.n_gauge,
            "thin": c.thin, "weak": c.weak, "ring_count": c.ring_count,
            "distance": float(c.distance), "lateral": float(c.lateral),
            "height": [float(c.height_min), float(c.height_max)], "size": c.size.tolist(),
            "frame_idx": c.points_idx.tolist()}


def ordinary(record):
    return bool(record and record["zone"] == "gauge" and not record["thin"] and not record["weak"])


def episode_count(frames):
    ordered = sorted(frames)
    return sum(i == 0 or k != ordered[i - 1] + 1 for i, k in enumerate(ordered))


def decomposition(component):
    s = runtime_support(component)
    cfg = ClusterConfig(**component["cfg"])
    # Finalize all runtime parts before any target-membership scoring.
    return {mode: [{"indices": ids.tolist(), "geometry": geometry(s, ids),
                    "descriptor": exact_descriptor(component, ids)} for ids in local_parts(s, cfg, mode)]
            for mode in MODES}


def validate_descriptor(actual, saved):
    if saved is None:
        if actual is not None:
            raise ValueError("saved rejected descriptor no longer rejects")
        return
    if actual is None:
        raise ValueError("saved accepted descriptor no longer accepts")
    aliases = {"zone": "zone", "reason": "reason", "thin": "thin", "voxels": "voxels",
               "gauge_voxels": "gauge_voxels"}
    for key, name in aliases.items():
        if actual[key] != saved[name]:
            raise ValueError(f"descriptor replay mismatch: {key}")
    for key in ("distance", "lateral", "height", "size"):
        if not np.allclose(actual[key], saved[key], atol=1e-6, rtol=0.):
            raise ValueError(f"descriptor replay mismatch: {key}")


def negative_report(directory):
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    events, stats, stop_frames = [], Counter(), {}
    for piece in summary["pieces"]:
        path = directory / Path(piece["path"]).name
        if sha(path) != piece["sha256"]:
            raise ValueError("direct fresh piece hash mismatch")
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["instrumentation_semantic_mismatches"] or report["saved_fresh_semantic_mismatches"]:
            raise ValueError("direct fresh parity missing")
        for event in report["events"]:
            timeline = event["timeline"]
            stop_frames.setdefault(report["piece"], set()).update(
                row["piece_frame"] for row in timeline if row["alarm"])
            matched = [r for r in timeline if r["support"] is not None]
            transitions = [common_reference(a, b) for a, b in zip(matched, matched[1:])]
            stats["observations"] += len(timeline)
            stats["matched_observations"] += len(matched)
            stats["transitions"] += len(transitions)
            stats["stop_track_frames"] += sum(r["alarm"] for r in timeline)
            sources = Counter(r["hit"]["input_source"] for r in matched)
            onset = next(r for r in timeline if r["alarm"])
            stats["events"] += 1
            stats["first_stop_gate_true"] += onset["fresh_gate_calls"] == [True]
            stats["first_stop_low"] += onset["cluster"]["kind"] == "low"
            stats["first_stop_ordinary"] += onset["cluster"]["kind"] != "low"
            onset_parts = None
            full_replays = 0
            for row in matched:
                component, cluster = row["component"], row["cluster"]
                if component["mask_meaning"] != "effective_corridor":
                    continue
                saved = {"zone": cluster["zone"], "reason": cluster["reason"], "thin": cluster["thin"],
                         "voxels": cluster["n_voxels"], "gauge_voxels": cluster["n_gauge"],
                         "distance": cluster["distance"], "lateral": cluster["lateral"],
                         "height": [cluster["height_min"], cluster["height_max"]], "size": cluster["size"]}
                actual = exact_descriptor(component, np.arange(len(component["xyz"])))
                validate_descriptor(actual, saved)
                full_replays += 1
                if row is onset:
                    onset_parts = decomposition(component)
                    member = np.asarray(component["output_member"], bool)
                    for parts in onset_parts.values():
                        for p in parts:
                            ids = np.asarray(p["indices"])
                            p["false_track_points"] = int(member[ids].sum())
            stats["validated_corridor_descriptors"] += full_replays
            interesting = []
            for i, t in enumerate(transitions):
                a, b = matched[i:i + 2]
                values = t["whole"]
                if (a["cluster"]["kind"] != b["cluster"]["kind"]
                        or max(values["own_rail_dy_gap_m"], values["own_rail_h_gap_m"]) > .25):
                    interesting.append(dict(t, kinds=[a["cluster"]["kind"], b["cluster"]["kind"]],
                                            evidence=b["after"]["evidence_hist"], alarm=b["alarm"]))
            events.append({"key": event["key"], "onset": onset["frame_id"], "sources": dict(sources),
                           "onset_kind": onset["cluster"]["kind"],
                           "onset_cluster": onset["cluster"],
                           "onset_effective_ranges": onset["effective_ranges"],
                           "onset_evidence": onset["after"]["evidence_hist"],
                           "onset_gate_calls": onset["fresh_gate_calls"],
                           "onset_local_parts": onset_parts, "interesting_transitions": interesting})
    stats["stop_frames"] = sum(map(len, stop_frames.values()))
    stats["episodes"] = sum(episode_count(frames) for frames in stop_frames.values())
    if stats["events"] == 27 and (stats["stop_track_frames"] != 133 or stats["stop_frames"] != 117
                                  or stats["episodes"] != 26 or stats["first_stop_gate_true"] != 27):
        raise ValueError("complete direct-fresh event inventory disagrees with fresh STOP output")
    return {"paired_frames": summary["paired_frames"], "counts": dict(stats), "events": events}


def positive_report(path):
    report = json.loads(path.read_text(encoding="utf-8"))
    if (not report["config"]["tracking"]["fresh_stop_evidence"]
            or report["instrumentation_semantic_mismatches"]):
        raise ValueError("direct positive fresh parity required")
    sequences = []
    for seq in report["sequences"]:
        if not seq["prior_parity"] or not seq["paired_parity"]:
            raise ValueError("saved positive output parity missing")
        counts, recovered, subset_frames = Counter(), [], {m: set() for m in MODES}
        target_observations = []
        for row, trace in zip(seq["rows"], seq["traces"], strict=True):
            if row["frame"] != trace["frame"]:
                raise ValueError("positive frame join mismatch")
            target_points = {}
            for blob in trace["blobs"]:
                component = blob["support"].get("descriptor_inputs")
                if component is None:
                    continue
                actual = exact_descriptor(component, np.arange(len(component["xyz"])))
                validate_descriptor(actual, blob["output"])
                counts["validated_corridor_descriptors"] += 1
                parts = decomposition(component)
                target = np.asarray(blob["support"]["target_mask"], bool)
                for j in np.flatnonzero(target):
                    fi = component["frame_idx"][j]
                    if fi >= 0:
                        target_points[fi] = (component["xyz"][j], component["strict"][j])
                oracle = blob.get("oracle_target_only")
                eligible = not row["hit"] and blob["output"] is None and oracle and oracle["zone"] == "gauge"
                for mode, local in parts.items():
                    good = []
                    for p in local:
                        ids = np.asarray(p["indices"])
                        nt = int(target[ids].sum())
                        p["target_points"] = nt
                        p["other_points"] = len(ids) - nt
                        if ordinary(p["descriptor"]) and nt:
                            subset_frames[mode].add(row["frame"])
                            if eligible and nt == int(target.sum()):
                                good.append(p)
                    if eligible:
                        counts[f"{mode}_oracle_cases"] += 1
                        counts[f"{mode}_complete_recoveries"] += bool(good)
                        recovered.append({"frame": row["frame"], "distance": row["d"], "mode": mode,
                                          "complete_parts": good})
            if target_points:
                values = list(target_points.values())
                target_observations.append({"frame_id": row["frame"], "stamp": None,
                                            "model": trace["model_exact"], "rotation": trace["rotation"],
                                            "support": {"xyz": [v[0] for v in values],
                                                        "strict": [v[1] for v in values]}})
        target_transitions = [common_reference(a, b) for a, b in zip(target_observations, target_observations[1:])]
        target_breaks = [t for t in target_transitions
                         if max(t["whole"]["common_rail_dy_gap_m"], t["whole"]["common_rail_h_gap_m"]) > .25]
        sequences.append({"kind": seq["kind"], "file0": seq["file0"], "frames": len(seq["rows"]),
                          "first": seq["first"], "sustained": seq["sustained"], "counts": dict(counts),
                          "local_ordinary_target_overlap_frames": {m: len(s) for m, s in subset_frames.items()},
                          "oracle_visible_support_transitions": len(target_transitions),
                          "oracle_common_reference_gap_over_025": target_breaks,
                          "oracle_cases": recovered})
    return {"path": str(path), "sha256": sha(path), "sequences": sequences}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fresh-trace", type=Path, required=True)
    parser.add_argument("--positive", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--summary-only", action="store_true", help="omit per-event console diagnostics")
    args = parser.parse_args()
    if not args.out.parent.is_dir():
        parser.error("output parent must exist")
    negatives = negative_report(args.fresh_trace)
    positives = [positive_report(p) for p in args.positive]
    report = {"schema": "fresh-local-support-comparison-v1", "negative": negatives, "positive": positives,
              "sha256": {str(p): sha(p) for p in (Path(__file__),
                           Path(__file__).with_name("analyze_local_body_support.py"),
                           Path(__file__).with_name("trace_fresh_support.py"),
                           Path(__file__).resolve().parents[1] / "resense/clustering.py",
                           Path(__file__).resolve().parents[1] / "resense/gauge.py",
                           args.fresh_trace / "summary.json")},
              "status": "diagnostic_only_no_detector_candidate",
              "limits": ["Selected negative events; no full-ride selector A/B.",
                         "Positive subset selection is label-blind; target identity is evaluation only.",
                         "Local parts are evaluated within actual components; no full-frame rescue pipeline.",
                         "Common reference is not ego pose registration or proof of object identity."]}
    args.out.write_text(json.dumps(jsonable(report), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"negative_counts": negatives["counts"], "paired_negative_frames": negatives["paired_frames"],
                      "positive_frames": sum(s["frames"] for p in positives for s in p["sequences"])}, indent=2))
    for e in negatives["events"]:
        if not args.summary_only:
            parts = e["onset_local_parts"]
            print(e["key"], e["onset"], e["onset_evidence"], "gate", e["onset_gate_calls"],
                  "local ordinary overlapping false track", None if parts is None else
                  {m: sum(ordinary(p["descriptor"]) and p["false_track_points"] > 0 for p in ps) for m, ps in parts.items()})
            for t in e["interesting_transitions"]:
                print(" transition", t["previous_frame"], t["frame"], t["kinds"], t["whole"], t["evidence"])
    for p in positives:
        for s in p["sequences"]:
            print(Path(p["path"]).name, s["kind"], s["file0"], s["counts"], s["local_ordinary_target_overlap_frames"],
                  "known-positive common-ref gaps >.25", len(s["oracle_common_reference_gap_over_025"]))


if __name__ == "__main__":
    main()
