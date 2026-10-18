"""Independent read-only check of archived startup-remount safety records."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.records / "summary.json").read_text())
    records = {}
    for case in summary["cases"]:
        path = args.records / (case["name"] + ".jsonl")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == case["output_sha256"]
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert len(rows) == 201
        assert [row["i"] for row in rows] == list(range(201))
        records[case["name"]] = rows
    baseline = records["baseline"]
    checks = []
    for case in summary["cases"]:
        rows = records[case["name"]]
        first = case["first_correct_orientation"]
        mismatches = {
            field: [row["i"] for row, reference in zip(rows, baseline)
                    if row["i"] >= first and row[field] != reference[field]]
            for field in ("decision", "dets", "warns", "nearest", "clear", "monitored")
        }
        assert not any(mismatches.values())
        stops = [row["i"] for row in rows if row["decision"] == "STOP"]
        assert stops == list(range(8, 201))
        pending = [row for row in rows if not row["orientation_confirmed"]]
        assert all(row["decision"] in ("CAUTION", "FAULT")
                   and row["clear"] == row["monitored"] == 0 for row in pending)
        events = []
        for row in rows:
            event = row["mount_detail"].get("orientation_replay")
            if event:
                assert event["status"] == "replayed" and event["frames"] == 2
                assert event["bytes"] <= 32 * 1024 * 1024
                # judge.record serializes sensor stamps rounded to four decimals.
                assert round(event["published_stamp"], 4) == row["stamp"]
                events.append(row["i"])
        checks.append({
            "case": case["name"], "frames": len(rows),
            "sha256": case["output_sha256"],
            "post_adoption_payload_mismatches": mismatches,
            "stop_count": len(stops), "first_stop": stops[0],
            "pending_rows": len(pending), "replay_event_rows": events,
        })
    result = {
        "reviewer": "c2_implementation; independent of N2 implementation author",
        "method": "Read all archived JSONL independently; verify summary SHA, frame indices, "
                  "exact safety fields after adoption, every STOP row and current published stamp. "
                  "This is an artifact check, not a detector rerun.",
        "checks": checks,
        "limitations": "Track coefficient floats are excluded from the exact safety-field comparison; "
                       "their <=3.71e-8 differences remain documented. Shared-host timing is not benchmarked.",
    }
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"cases": len(checks), "rows": sum(c["frames"] for c in checks),
                      "all_first_stop": 8, "all_stop_count": 193, "mismatches": 0}))


if __name__ == "__main__":
    main()
