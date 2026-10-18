"""Summarize complete paired decoded-bag input sensitivity captures without TP claims."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

BAGS = {"doubleT_obstacle": 201, "doubleT_platform": 345, "roundT_doubleT": 252,
        "roundT_pressureGate_roundT": 268, "roundT_squareT_pressureGate_squareT": 545,
        "squareT_platform_squareT_switch": 877, "cloud_with_fake_obj": 1510,
        "synthetic_platform": 386, "synthetic_switch": 736, "synthetic_tunnels": 545}
EMPTY = {"doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent / "proxy")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    reports = {}
    for name, count in BAGS.items():
        folder = args.root / name
        summary = json.loads((folder / "summary.json").read_text())
        if summary["suite"] != "proxy" or len(summary["cases"]) != 2:
            raise ValueError(f"wrong suite: {name}")
        captures = []
        for case, filename in zip(summary["cases"], ("baseline.jsonl", "falcon_proxy.jsonl")):
            path = folder / filename
            if sha(path) != case["output_sha256"]:
                raise ValueError(f"capture changed: {path}")
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            if len(rows) != count or [r["i"] for r in rows] != list(range(count)):
                raise ValueError(f"incomplete capture: {path}")
            if dict(Counter(r["decision"] for r in rows)) != case["decisions"]:
                raise ValueError(f"summary does not match capture: {path}")
            captures.append(rows)
        before, after = captures
        for left, right in zip(before, after):
            if any(left[k] != right[k] for k in ("i", "stamp", "frame_id", "topic")):
                raise ValueError(f"input identity changed: {name}")
        retained = [right["input_points"] / max(1, left["input_points"]) for left, right in zip(before, after)]
        reports[name] = {
            "frames": count, "source_hashes": summary["source_hashes"],
            "input_metadata_sha256": summary["cache_meta_sha256"],
            "baseline_raw_sha256": sha(folder / "baseline.jsonl"),
            "proxy_raw_sha256": sha(folder / "falcon_proxy.jsonl"),
            "baseline_decisions": dict(Counter(r["decision"] for r in before)),
            "proxy_decisions": dict(Counter(r["decision"] for r in after)),
            "lost_baseline_stop_frames": [left["i"] for left, right in zip(before, after)
                                          if left["decision"] == "STOP" and right["decision"] != "STOP"],
            "added_stop_frames": [left["i"] for left, right in zip(before, after)
                                  if left["decision"] != "STOP" and right["decision"] == "STOP"],
            "changed_decision_frames": [left["i"] for left, right in zip(before, after)
                                        if left["decision"] != right["decision"]],
            "input_points_before": sum(r["input_points"] for r in before),
            "input_points_after": sum(r["input_points"] for r in after),
            "retained_fraction_min_median_max": [min(retained), float(np.median(retained)), max(retained)],
            "known_obstacle_free_recording": name in EMPTY,
            "false_stop_frames_if_known_empty": {
                "baseline": sum(r["decision"] == "STOP" for r in before),
                "proxy": sum(r["decision"] == "STOP" for r in after),
            } if name in EMPTY else None,
            "first_stop": {
                label: next(({"frame": row["i"], "reported_nearest_m": row["nearest"]}
                             for row in rows if row["decision"] == "STOP"), None)
                for label, rows in (("baseline", before), ("proxy", after))
            },
        }
    output = {
        "status": "COMPLETE_INPUT_SENSITIVITY_EXPERIMENT", "bags": reports,
        "frames_per_arm": sum(BAGS.values()), "raw_captures": 2 * len(BAGS),
        "known_empty_stop_frames": {
            label: sum(reports[name]["false_stop_frames_if_known_empty"][label] for name in EMPTY)
            for label in ("baseline", "proxy")
        },
        "limitations": [
            "Pandar-point thinning and FOV crop are a stress proxy, not a faithful Falcon raster/noise/return simulation.",
            "These decoded NodeReplica captures preserve header stamps and radial crop; ordinary full-gate compact input/receive-stamp results are a separate protocol.",
            "Loss of baseline STOP is not an exact false-negative count: the transform can remove observable object points, and positive-recording STOP can include uncertain objects.",
            "Synthetic proxy mount estimates may differ from the identity-mount N5 label contract; these summaries do not silently rescore raw boxes as calibrated ground truth.",
            "Full Set F/ride gate results, input-hook coverage and their original visibility denominators are reported separately.",
            "Timing is informational under shared CPU load.",
        ],
        "script_sha256": sha(Path(__file__)),
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "bags"}))


if __name__ == "__main__":
    main()
