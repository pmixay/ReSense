#!/usr/bin/env python3
"""Strict paired acceptance for all 33 clear-recording history stress cases.

A new STOP frame fails its own history even if another frame or history improves. Events
are distinct reported track IDs; IDs may change across algorithms, so event correspondence
requires an overlapping input frame and nearby detection positions, with one-to-one matching.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

EMPTY = ("roundT_doubleT", "doubleT_platform", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
HISTORIES = ("every", "drop20", "drop40", "catchup", "offset", "dither5")
CAPTURES = ("failed_clear", "old_stock", "old_pass")
EXPECTED = ({("cache", bag, name, 0) for bag in EMPTY for name in HISTORIES}
            | {("capture", "roundT_doubleT", name, 0) for name in CAPTURES})


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def verify_identity(report, expected, role):
    for field, contents in (("source_sha256", "source_files"), ("config_sha256", "config")):
        actual = digest_json(report[contents])
        if actual != report[field]:
            raise ValueError(f"{role} {field} does not match its report contents")
        if actual != expected[field]:
            raise ValueError(f"{role} {field} differs from the expected frozen identity")
    if report["source_files"] != expected["source_files"]:
        raise ValueError(f"{role} production file inventory differs from the expected freeze")


def key(row):
    return row["source"], row["bag"], row["history"], row["seed"]


def inventory(report):
    if report.get("schema") != "resense-history-stress-v2":
        raise ValueError("per-frame history evidence requires schema v2")
    out = {}
    for row in report["rows"]:
        identity = key(row)
        if identity in out:
            raise ValueError(f"duplicated history: {identity}")
        out[identity] = row
    if set(out) != EXPECTED:
        raise ValueError(f"expected all 33 histories: missing={sorted(EXPECTED-set(out))}; "
                         f"unexpected={sorted(set(out)-EXPECTED)}")
    if report["totals"]["histories"] != 33:
        raise ValueError("declared history total differs from required 33")
    return out


def frame_key(row):
    return row["frame"], row["frame_id"], row["stamp"]


def event_map(rows):
    events = {}
    for row in rows:
        for detection in row["detections"]:
            events.setdefault(int(detection["id"]), {})[frame_key(row)] = detection
    return events


def load_capture(report_path, report, row):
    directory = report_path.parent / report["capture_directory"]
    path = directory / row["capture"]["file"]
    if path.resolve().parent != directory.resolve():
        raise ValueError("capture filename must stay in its declared directory")
    if sha(path) != row["capture"]["sha256"]:
        raise ValueError(f"capture hash mismatch: {path}")
    with gzip.open(path, "rt") as stream:
        frames = [json.loads(line) for line in stream if line.strip()]
    if not frames or len(frames) != row["frames"]:
        raise ValueError(f"capture frame count differs: {path}")
    identities = [frame_key(frame) for frame in frames]
    if len(set(identities)) != len(identities):
        raise ValueError(f"duplicate input frame: {path}")
    if any(b[0] <= a[0] or b[2] <= a[2] for a, b in zip(identities, identities[1:])):
        raise ValueError(f"unordered frame identity or timestamp: {path}")
    if any(bool(frame["detections"]) != bool(frame["obstacle"]) for frame in frames):
        raise ValueError(f"STOP flag and detection list differ: {path}")
    stops = [frame["frame"] for frame in frames if frame["obstacle"]]
    if stops != row["stop_frame_ids"] or len(stops) != row["stop_frames"]:
        raise ValueError(f"STOP frame summary differs: {path}")
    if len(event_map(frames)) != row["stop_events"]:
        raise ValueError(f"STOP event summary differs: {path}")
    return frames


def event_pairs(previous, current):
    # A physical event must share at least one input frame and agree in location there.
    edges = {}
    for candidate_id, candidate in current.items():
        compatible = []
        for baseline_id, baseline in previous.items():
            overlap = set(candidate) & set(baseline)
            if any(abs(candidate[f]["distance"] - baseline[f]["distance"]) <= 0.5
                   and abs(candidate[f]["lateral"] - baseline[f]["lateral"]) <= 0.25
                   and candidate[f].get("kind", "") == baseline[f].get("kind", "") for f in overlap):
                compatible.append(baseline_id)
        edges[candidate_id] = sorted(compatible, key=lambda baseline_id: (baseline_id != candidate_id, baseline_id))
    owners = {}

    def augment(candidate_id, seen):
        for baseline_id in edges[candidate_id]:
            if baseline_id in seen:
                continue
            seen.add(baseline_id)
            if baseline_id not in owners or augment(owners[baseline_id], seen):
                owners[baseline_id] = candidate_id
                return True
        return False

    for candidate_id in sorted(current):
        augment(candidate_id, set())
    return sorted([{"baseline_id": baseline_id, "candidate_id": candidate_id}
                   for baseline_id, candidate_id in owners.items()], key=lambda row: row["candidate_id"])


def compare_rows(baseline, candidate):
    if [frame_key(r) for r in baseline] != [frame_key(r) for r in candidate]:
        raise ValueError("paired history input identity, order, or timestamps differ")
    new_stops = [b["frame"] for a, b in zip(baseline, candidate) if b["obstacle"] and not a["obstacle"]]
    removed_stops = [a["frame"] for a, b in zip(baseline, candidate) if a["obstacle"] and not b["obstacle"]]
    previous, current = event_map(baseline), event_map(candidate)
    pairs = event_pairs(previous, current)
    used = {p["candidate_id"] for p in pairs}
    new_events = [{"id": ident, "frames": [f[0] for f in event],
                   "detections": [{"frame": f[0], **detection} for f, detection in event.items()]}
                  for ident, event in current.items() if ident not in used]
    counts = {"baseline_stop_frames": sum(r["obstacle"] for r in baseline),
              "candidate_stop_frames": sum(r["obstacle"] for r in candidate),
              "baseline_stop_events": len(previous), "candidate_stop_events": len(current)}
    payload_changes = [{"frame": a["frame"], "baseline": a["detections"], "candidate": b["detections"]}
                       for a, b in zip(baseline, candidate) if a["detections"] != b["detections"]]
    return {**counts, "frames": len(baseline), "new_stop_frames": new_stops,
            "removed_stop_frames": removed_stops, "matched_events": pairs, "new_stop_events": new_events,
            "detection_payload_changes": payload_changes,
            "passed": not new_stops and not new_events and len(current) <= len(previous)}


def compare(baseline_path, candidate_path, expected_path):
    baseline_path, candidate_path = Path(baseline_path), Path(candidate_path)
    baseline, candidate = json.loads(baseline_path.read_text()), json.loads(candidate_path.read_text())
    expected = json.loads(Path(expected_path).read_text())["variants"]
    verify_identity(baseline, expected["baseline"], "baseline")
    verify_identity(candidate, expected["candidate"], "candidate")
    old, new = inventory(baseline), inventory(candidate)
    if baseline["inputs"] != candidate["inputs"]:
        raise ValueError("source recording, capture, cache or timestamp hashes differ")
    if baseline["runner_sha256"] != candidate["runner_sha256"]:
        raise ValueError("paired histories require the same runner")
    rows = []
    for identity in sorted(EXPECTED):
        before = load_capture(baseline_path, baseline, old[identity])
        after = load_capture(candidate_path, candidate, new[identity])
        rows.append({"source": identity[0], "bag": identity[1], "history": identity[2], "seed": identity[3],
                     **compare_rows(before, after)})
    return {"schema": "resense-history-stress-acceptance-v1", "passed": all(r["passed"] for r in rows),
            "histories": len(rows), "failed_histories": [key(r) for r in rows if not r["passed"]],
            "expected_identities": {"file": Path(expected_path).name, "sha256": sha(expected_path)},
            "baseline": {"file": baseline_path.name, "sha256": sha(baseline_path),
                         "source_sha256": baseline["source_sha256"], "config_sha256": baseline["config_sha256"]},
            "candidate": {"file": candidate_path.name, "sha256": sha(candidate_path),
                          "source_sha256": candidate["source_sha256"], "config_sha256": candidate["config_sha256"]},
            "rule": "Every history must have zero new false STOP frames and zero unmatched false STOP events; no aggregate cancellation.",
            "event_correspondence": "One-to-one matching requires an overlapping input frame with distance within 0.5 m, lateral within 0.25 m, and the same kind.",
            "rows": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expect-identities", type=Path, required=True,
                        help="JSON protocol with frozen source/config hashes and production file maps in variants")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = compare(args.baseline, args.candidate, args.expect_identities)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "histories": result["histories"],
                      "failed_histories": result["failed_histories"]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
