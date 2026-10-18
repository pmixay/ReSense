"""Compare the strict 140-frame same-node run, retaining all safety/reset fields."""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path


# Independent observed timings/resource counters vary between real executions.
# No decision, validity, range, model, input generation, drop count or hold field
# is excluded. In particular, timing-induced changes to safety outputs still fail.
EXCLUDED = (
    ("_received_mono",), ("timing_ms",),
    ("health", "latency_p95_ms"),
    *(("node", key) for key in (
        "latency_ms", "fps", "decode_ms", "detect_ms", "cpu_cores", "rss_peak_mb")),
    *(("freshness", key) for key in (
        "evaluated_at_utc_s", "source_age_s", "acquisition_age_s", "publication_age_s",
        "residence_age_s", "queue_lag_s")),
    *(("mount", "orientation_replay", key) for key in (
        "physical_call_ms", "physical_cpu_ms", "replay_ms")),
)


def read(path):
    raw = path.read_bytes()
    decoded = gzip.decompress(raw) if path.suffix == ".gz" else raw
    return [json.loads(line) for line in decoded.splitlines()], hashlib.sha256(decoded).hexdigest()


def normalized(row):
    row = deepcopy(row)
    for path in EXCLUDED:
        current = row
        for key in path[:-1]:
            current = current.get(key, {})
        current.pop(path[-1], None)
    return row


def differences(left, right, path=""):
    if isinstance(left, dict) and isinstance(right, dict):
        out = []
        for key in sorted(left.keys() | right.keys()):
            name = f"{path}.{key}" if path else key
            if key not in left or key not in right:
                out.append({"path": name, "before": left.get(key), "after": right.get(key)})
            else:
                out.extend(differences(left[key], right[key], name))
        return out
    if left != right:
        if isinstance(left, list) or isinstance(right, list):
            return [{"path": path,
                     "before_sha256": hashlib.sha256(json.dumps(left).encode()).hexdigest(),
                     "after_sha256": hashlib.sha256(json.dumps(right).encode()).hexdigest(),
                     "before_length": len(left) if isinstance(left, list) else None,
                     "after_length": len(right) if isinstance(right, list) else None}]
        return [{"path": path, "before": left, "after": right}]
    return []


def transition_signature(rows):
    """Remove repeated watchdog publications, retain every semantic transition."""
    transitions = []
    for row in rows:
        if row.get("snapshot_kind") == "frame":
            continue
        sig = {
            "snapshot_kind": row.get("snapshot_kind"),
            "recording": row.get("node", {}).get("recording"),
            "input_generation": row.get("node", {}).get("input_generation"),
            "sensor_profile": row.get("sensor_profile"),
            "decision": row.get("decision"), "stop_held": row.get("stop_held"),
            "freshness_valid": row.get("freshness", {}).get("valid"),
            "freshness_reason": row.get("freshness", {}).get("reason"),
            "clear_distance": row.get("clear_distance"),
            "monitored_range": row.get("health", {}).get("monitored_range"),
            "monitored_small": row.get("monitored_small"),
            "gauge_valid": row.get("gauge", {}).get("valid"),
            "solid_range_m": row.get("gauge", {}).get("solid_range_m"),
        }
        if not transitions or transitions[-1] != sig:
            transitions.append(sig)
    return transitions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--before-report", type=Path, required=True)
    parser.add_argument("--after-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    old, old_hash = read(args.before)
    new, new_hash = read(args.after)
    frames = [[r for r in rows if r.get("snapshot_kind") == "frame"] for rows in (old, new)]
    expected = {"pandar128": 40, "falcon_ros": 100}
    assert all(dict(Counter(r["sensor_profile"] for r in rows)) == expected for rows in frames)
    keys = [[(r["sensor_profile"], r["stamp"]) for r in rows] for rows in frames]
    assert keys[0] == keys[1] and len(set(keys[0])) == 140
    changes = []
    for index, (a, b) in enumerate(zip(*frames)):
        diffs = differences(normalized(a), normalized(b))
        if diffs:
            changes.append({"index": index, "profile": a["sensor_profile"], "stamp": a["stamp"],
                            "differences": diffs})
    reports = [json.loads(path.read_text()) for path in (args.before_report, args.after_report)]
    assert all(r["passed"] and r["detector_restarts"] == 0 for r in reports)
    control_diffs = differences(reports[0]["controls"], reports[1]["controls"])
    transitions = [transition_signature(rows) for rows in (old, new)]
    result = {
        "passed": not changes and not control_diffs and transitions[0] == transitions[1],
        "expected_frames": expected, "compared_frames": 140,
        "uncompressed_input_sha256": {"before": old_hash, "after": new_hash},
        "exclusions": [".".join(path) for path in EXCLUDED],
        "exclusion_scope": "Only measured time/rate/resource values. All decisions, health severity/messages, "
                           "freshness validity/reason, range claims, gauge state, detector payloads, input "
                           "identity/reset generations and dropped/catch-up counts remain exact.",
        "frame_mismatch_count": len(changes), "frame_mismatches": changes,
        "control_mismatches": control_diffs,
        "nonframe_transition_equal": transitions[0] == transitions[1],
        "nonframe_transitions": {"before": transitions[0], "after": transitions[1]},
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": result["passed"], "compared_frames": 140,
                      "frame_mismatches": len(changes), "control_mismatches": len(control_diffs),
                      "nonframe_transition_equal": result["nonframe_transition_equal"]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
