"""Independently compare full original-auto and opt-in-only Falcon captures."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from detector_freeze import source_digest, source_hashes  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "falcon_default_off"
PENDING = "sensor orientation unconfirmed: waiting for a supported axis mapping"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized(row):
    result = deepcopy(row)
    for key in ("decode_ms", "detect_ms", "total_ms"):
        result.pop(key)
    messages = [value for value in result["msgs"] if not value.startswith("latency p95 ")]
    if messages != result["msgs"] and result["level"] == "warn":
        result["level"] = result["dlevel"]
    result["msgs"] = messages
    return result


def differences(left, right, prefix=""):
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(left.keys() | right.keys()):
            path = f"{prefix}.{key}" if prefix else key
            if key not in left:
                yield "added:" + path
            elif key not in right:
                yield "removed:" + path
            else:
                yield from differences(left[key], right[key], path)
    elif left != right:
        yield "changed:" + prefix


def intervals(rows):
    output = []
    previous = False
    for row in rows:
        if row["obstacle"]:
            if previous:
                output[-1][1] = row["i"]
            else:
                output.append([row["i"], row["i"]])
        previous = row["obstacle"]
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=HERE / "falcon_full",
                        help="Recorded baseline folder; matched control is falcon_default_off_control")
    args = parser.parse_args()
    receipt_path = OUT / "execution.json"
    receipt, summary = read(receipt_path), read(OUT / "summary.json")
    assert receipt["status"] == "COMPLETE" and receipt["returncode"] == 0
    assert receipt["source_unchanged"] and receipt["harness_unchanged"]
    assert receipt["default_replay_frames"] == 0 and receipt["config_overrides"] == []
    assert receipt["source_commit"] == "cecab1b696b8c2e101207601acd8faed96c8bfb8"
    source = Path(receipt["source"])
    hashes = source_hashes(source)
    assert hashes == receipt["source_files"] and source_digest(hashes) == receipt["source_sha256"]
    for name, expected in hashes.items():
        blob = subprocess.check_output(["git", "show", f"{receipt['source_commit']}:{name}"], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
    for name, expected in receipt["native_files"].items():
        assert sha(source / name) == expected
    assert sha(HERE / "replay_inputs.py") == receipt["harness_sha256"]
    assert sha(OUT / "summary.json") == receipt["summary_sha256"]
    assert Path(summary["source"]).resolve() == source.resolve()
    assert summary["cases"][0]["frames"] == 4443
    assert summary["cases"][0]["overrides"] == {}
    old_path, new_path = args.reference / "baseline.jsonl", OUT / "baseline.jsonl"
    old_summary = read(args.reference / "summary.json")
    extra_inputs = []
    if args.reference.resolve() != (HERE / "falcon_full").resolve():
        control_path = args.reference / "execution.json"
        control = read(control_path)
        assert control["status"] == "COMPLETE" and control["returncode"] == 0
        assert control["source_unchanged"] and control["harness_unchanged"]
        assert control["source_commit"] == "9b92df56e802d9d63f83f2fc5e5b07374db669c7"
        assert control["native_files"] == receipt["native_files"]
        assert control["harness_sha256"] == receipt["harness_sha256"]
        assert control["config_overrides"] == [] and control["expected_frames"] == 4443
        assert sha(old_path) == control["raw_sha256"]
        assert sha(args.reference / "summary.json") == control["summary_sha256"]
        assert source_hashes(Path(control["source"])) == control["source_files"]
        assert Path(old_summary["source"]).resolve() == Path(control["source"]).resolve()
        for name, expected in control["source_files"].items():
            blob = subprocess.check_output(["git", "show", f"{control['source_commit']}:{name}"], cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest() == expected
            if name in old_summary["source_hashes"]:
                assert old_summary["source_hashes"][name] == expected
        extra_inputs.append(control_path)
    old_case = next(row for row in old_summary["cases"] if row["name"] == "baseline")
    assert sha(old_path) == old_case["output_sha256"]
    assert sha(new_path) == summary["cases"][0]["output_sha256"] == receipt["raw_sha256"]
    assert summary["cache_meta_sha256"] == old_summary["cache_meta_sha256"] == receipt["input_meta_sha256"]
    metadata = read(Path(summary["cache"]) / "meta.json")
    assert len(metadata) == 4443
    before, after = ([json.loads(line) for line in path.read_text().splitlines()] for path in (old_path, new_path))
    assert len(before) == len(after) == 4443
    changed, unexpected = {}, []
    lost, added, decision_changes = [], [], []
    for index, (left, right, meta) in enumerate(zip(before, after, metadata)):
        assert left["i"] == right["i"] == index
        for key in ("stamp", "bag_t"):
            assert left[key] == right[key] == round(meta[key], 4)
        for key in ("topic", "frame_id"):
            assert left[key] == right[key] == meta[key]
        for row in (left, right):
            assert type(row["obstacle"]) is bool and row["obstacle"] == bool(row["dets"])
            assert row["obstacle"] == (row["decision"] == "STOP")
        if left["obstacle"] and not right["obstacle"]:
            lost.append(index)
        if right["obstacle"] and not left["obstacle"]:
            added.append(index)
        if left["decision"] != right["decision"]:
            decision_changes.append(index)
        a, b = normalized(left), normalized(right)
        for field in differences(a, b):
            changed.setdefault(field, []).append(index)
        # Report the new diagnostics above before removing only these explicitly
        # understood additions for unchanged operational-field equality.
        confirmed = b["mount_detail"].pop("orientation_confirmed")
        assert confirmed == b["orientation_confirmed"]
        if index == 0:
            assert not confirmed and b["decision"] == "FAULT" and b["clear"] == b["monitored"] == 0
            assert b["msgs"] == a["msgs"] + [PENDING]
            b["msgs"].remove(PENDING)
        else:
            assert confirmed
        if a != b:
            unexpected.append(index)
    checks = {"complete_original_stamps_and_frames": True,
              "no_stop_added_or_lost": not lost and not added,
              "no_decision_changes": not decision_changes,
              "all_stop_intervals_exact": intervals(before) == intervals(after),
              "all_other_non_timing_fields_exact": not unexpected}
    result = {"status": "PASS" if all(checks.values()) else "FAIL", "checked_utc": datetime.now(timezone.utc).isoformat(),
              "checks": checks, "source_commit": receipt["source_commit"], "source_sha256": receipt["source_sha256"],
              "frames": 4443, "reference_decisions": dict(Counter(row["decision"] for row in before)),
              "candidate_decisions": dict(Counter(row["decision"] for row in after)),
              "reference_stop_intervals": intervals(before), "candidate_stop_intervals": intervals(after),
              "lost_stop_frames": lost, "added_stop_frames": added, "decision_changed_frames": decision_changes,
              "all_non_timing_changed_fields": changed, "unexpected_changed_frames": unexpected,
              "expected_readiness_additions": "mount_detail.orientation_confirmed on every row; explicit unconfirmed message on initial already-FAULT/zero-range row only.",
              "reference_folder": str(args.reference),
              "input_sha256": {str(path): sha(path) for path in [Path(__file__), receipt_path,
                  OUT / "summary.json", args.reference / "summary.json", old_path, new_path, *extra_inputs]},
              "limits": ["Serialized full-recording equality, not surveyed object/gauge ground truth.",
                         "Timing excluded; shared host does not establish throughput.",
                         "Prior old-auto static-support/person detection limitations remain; default0 does not claim replay4 gains."]}
    (OUT / "independent_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "frames", "checks", "candidate_decisions")}))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
