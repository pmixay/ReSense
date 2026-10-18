"""Compare actual Falcon DDS frames with the independently captured offline prefix."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--offline", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    received = [json.loads(line) for line in args.status.read_text().splitlines()]
    actual = [row for row in received if row.get("sensor_profile") == "falcon_ros"
              and row.get("snapshot_kind") == "frame"]
    expected = [json.loads(line) for line in args.offline.read_text().splitlines()][:100]
    if len(actual) != 100 or len(expected) != 100:
        raise ValueError("expected exactly 100 actual frame snapshots and offline prefix rows")
    fields = {"d": "distance", "lat": "lateral", "c": "center", "size": "size",
              "n": "n_points", "zone": "zone", "kind": "kind", "reason": "reason",
              "conf": "confidence", "age": "age", "hmin": "height_min"}
    mismatches = []
    for index, (node, old) in enumerate(zip(actual, expected)):
        for name in ("detections", "warnings"):
            normalized = [{key: item[value] for key, value in fields.items()} for item in node[name]]
            if normalized != old["dets" if name == "detections" else "warns"]:
                mismatches.append({"frame": index, "field": name})
        for name in ("n_points", "obstacle", "warning"):
            if node[name] != old[name]:
                mismatches.append({"frame": index, "field": name})
        if round(node["stamp"], 4) != old["stamp"]:
            mismatches.append({"frame": index, "field": "stamp"})
        if node["stop_held"]:
            mismatches.append({"frame": index, "field": "unexpected held STOP"})
        if index and node["decision"] != old["decision"]:
            mismatches.append({"frame": index, "field": "decision"})
    first_guard = (actual[0]["decision"] == "FAULT" and actual[0]["clear_distance"] == 0
                   and actual[0]["freshness"]["reason"] == "epoch_unconfirmed")
    report = {"status": "PASS" if not mismatches and first_guard else "FAIL",
              "frames": 100, "mismatches": mismatches, "first_epoch_guard": first_guard,
              "actual_stop_frames": [i for i, row in enumerate(actual) if row["obstacle"]],
              "offline_stop_frames": [row["i"] for row in expected if row["obstacle"]],
              "scope": "Exact shared detection/warning geometry, counts, confidence, ages, reasons and zones; point counts, rounded original stamps, flags and post-initial decisions",
              "intentional_differences": ["First input remains FAULT until the new recording epoch is confirmed",
                                           "Runtime selected conservative Falcon policy reports unavailable small-target range as null and clear range zero; archived prefix uses legacy range policy"],
              "limitations": "Offline capture omits persistent IDs and intensity, so neither is compared; this is not physical obstacle/gauge ground truth",
              "input_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in (args.status, args.offline, Path(__file__))}}
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
