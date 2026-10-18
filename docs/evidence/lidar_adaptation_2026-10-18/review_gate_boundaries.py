"""Independent source/default/STOP-boundary audit; reads captures, never detectors."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402
from scripts.decision_policy_import import load_policy  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spans(flags):
    """Inclusive row-index intervals; called separately across every reset boundary."""
    result = []
    for index, active in enumerate(flags):
        if active:
            if not result or result[-1][1] != index - 1:
                result.append([index, index])
            else:
                result[-1][1] = index
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--reference-source", type=Path, required=True)
    parser.add_argument("--candidate-work", type=Path, required=True)
    parser.add_argument("--reference-work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence
    candidate = read(evidence / "gate.json")
    reference = read(evidence / "control_9b_native/gate.json")
    review = read(evidence / "gate_independent_review.json")
    identity = read(evidence / "runtime_identity_metadata_fixed.json")
    historical_path = args.candidate_source / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"
    historical = read(historical_path)

    files = freeze.source_hashes(args.candidate_source)
    assert len(files) == 38
    assert files == identity["source_files"] == freeze.source_hashes(ROOT)
    assert freeze.source_digest(files) == identity["source_sha256"]
    commit = candidate["code"]["commit"]
    assert commit == identity["source_commit"]
    for relative, expected in files.items():
        blob = subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected, relative
    assert files[freeze.CONFIG] == files[freeze.ROS_CONFIG]
    freeze.check_gate(historical, candidate, files[freeze.CONFIG])
    rebuilt = gate.gate_summary(gate.compare(historical, candidate, []), historical,
                                candidate["gate"]["baseline"], [])
    assert rebuilt == candidate["gate"]
    fresh_metrics = gate.compare(reference, candidate, [])
    assert fresh_metrics == review["gate_metrics"]
    assert not any(row["fails"] or row["allowed"] for row in fresh_metrics)
    assert all(row["verdict"] == "same" or row["metric"].startswith("latency_ms.")
               for row in fresh_metrics)
    cfg = gate.eval_real.load_cfg(str(args.candidate_work / "config.yaml"), [])
    canonical = gate.eval_real.load_cfg(str(args.candidate_source / freeze.CONFIG), [])
    assert cfg.to_dict() == canonical.to_dict()
    assert gate.config_info(None, [], cfg)["sha256"] == candidate["config"]["sha256"]
    assert cfg.calibration.orientation_replay_frames == 4
    assert cfg.track.rails_axis_extension is False
    for relative, expected in identity["native_files"].items():
        assert sha(args.candidate_source / relative) == sha(args.reference_source / relative) == expected
    harness = ["regression_gate.py", "eval_real.py", "far_range_eval.py", "cache_io.py",
               "score_fake_objects.py", "robustness_battery.py"]
    for name in harness:
        assert sha(ROOT / "scripts" / name) == sha(args.candidate_source / "scripts" / name)
        assert sha(args.candidate_source / "scripts" / name) == sha(args.reference_source / "scripts" / name)

    policy = load_policy(args.candidate_source)
    pieces = []
    total = 0
    for name in sorted(review["candidate_raw_hashes"]):
        left_path, right_path = args.reference_work / name, args.candidate_work / name
        assert sha(left_path) == review["reference_raw_hashes"][name]
        assert sha(right_path) == review["candidate_raw_hashes"][name]
        left = [json.loads(line) for line in left_path.read_text().splitlines()]
        right = [json.loads(line) for line in right_path.read_text().splitlines()]
        assert len(left) == len(right)
        old_decisions, new_decisions = [], []
        readiness = Counter()
        for a, b in zip(left, right):
            assert all(a[key] == b[key] for key in ("stamp", "frame", "frame_id"))
            for row in (a, b):
                assert type(row["obstacle"]) is bool
                assert row["obstacle"] == bool(row["detections"])
                assert row["warning"] == bool(row["warnings"])
                assert row["health"]["level"] in ("ok", "warn", "error")
                assert row["health"]["decision_level"] in ("ok", "warn", "error")
            assert a["detections"] == b["detections"]
            assert a["warnings"] == b["warnings"]
            assert a["clear_distance"] == b["clear_distance"]
            assert a["health"]["monitored_range"] == b["health"]["monitored_range"]
            old_decisions.append(policy.decision(a))
            new_decisions.append(policy.decision(b))
            assert b["health"]["orientation_confirmed"] == b["mount"]["orientation_confirmed"]
            readiness[str(b["health"]["orientation_confirmed"])] += 1
        assert old_decisions == new_decisions
        stop = [value == "STOP" for value in new_decisions]
        intervals = spans(stop)
        pieces.append({"capture": name, "rows": len(right), "decisions": dict(Counter(new_decisions)),
                       "orientation_confirmed": dict(readiness), "stop_intervals": intervals,
                       "first_stop_frame_id": right[intervals[0][0]]["frame_id"] if intervals else None,
                       "first_stop_row": intervals[0][0] if intervals else None,
                       "last_stop_row": intervals[-1][1] if intervals else None,
                       "stop_frames": sum(stop), "stop_episodes": len(intervals),
                       "all_decisions_and_stop_boundaries_identical": True})
        total += len(right)
    assert total == 15269
    sets = [read(path / "setF_straight.json") for path in (args.reference_work, args.candidate_work)]
    assert sets[0]["sequences"] == sets[1]["sequences"]
    summaries = [{key: value for key, value in item["summary"].items() if key != "wall_s"}
                 for item in sets]
    assert summaries[0] == summaries[1]
    assert len(sets[1]["sequences"]) == 30
    set_f = []
    for sequence in sets[1]["sequences"]:
        hits = [row["hit"] for row in sequence["rows"]]
        set_f.append({"kind": sequence["kind"], "file0": sequence["file0"], "rows": len(hits),
                      "first_hit_row": next((i for i, hit in enumerate(hits) if hit), None),
                      "hit_rows": sum(hits), "hit_intervals": spans(hits)})
    assert sum(row["rows"] for row in set_f) == 3060
    for case in review["ordinary"].values():
        assert set(case["changed_fields"]) <= {"added:health.orientation_confirmed",
                                              "added:mount.orientation_confirmed"}
        assert not any(case[key] for key in ("lost_stop_frames", "added_stop_frames",
                       "frames_with_changed_or_missing_old_detection_payload",
                       "unconfirmed_orientation_guard_violations"))

    manifest_path = evidence / "raw/gate_control_and_7b_manifest.json"
    manifest = read(manifest_path)
    archive_path = evidence / "raw" / manifest["archive"]
    assert sha(archive_path) == manifest["archive_sha256"]
    with tarfile.open(archive_path, "r:gz") as archive:
        assert len(archive.getmembers()) == manifest["member_count"] == 39
        assert set(archive.getnames()) == {entry["member"] for entry in manifest["members"]}
        for entry in manifest["members"]:
            payload = archive.extractfile(entry["member"]).read()
            assert len(payload) == entry["bytes"]
            assert hashlib.sha256(payload).hexdigest() == entry["sha256"]
    output = {
        "status": "FULL_DEFAULT_GATE_PASS_X3_STILL_REQUIRED",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Independent raw STOP/decision/range boundaries, source/defaults and durable archive; no detector execution.",
        "source_commit": commit, "source_files": len(files), "source_digest": freeze.source_digest(files),
        "source_matches_live_immutable_git_and_receipt": True,
        "native_files": identity["native_files"], "no_waivers_or_overrides": True,
        "default_orientation_replay_frames": 4, "default_rails_axis_extension": False,
        "historical_gate": rebuilt,
        "fresh_metric_verdicts": dict(Counter(row["verdict"] for row in fresh_metrics)),
        "fresh_metric_count": len(fresh_metrics), "all_non_latency_metrics_exact": True,
        "ordinary_rows": total, "pieces": pieces, "set_F_rows": 3060, "set_F_sequences": set_f,
        "lost_added_delayed_shortened_stop_frames": 0,
        "all_stored_set_F_sequences_and_non_timing_summary_exact": True,
        "archive_sha256": manifest["archive_sha256"], "archive_members_verified": 39,
        "input_sha256": {str(path): sha(path) for path in [Path(__file__), historical_path,
                           evidence / "gate.json", evidence / "control_9b_native/gate.json",
                           evidence / "gate_independent_review.json", manifest_path,
                           evidence / "runtime_identity_metadata_fixed.json",
                           args.candidate_source / "ros2_ws/src/resense_ros/resense_ros/decision_policy.py"]},
        "limits": ["Serialized outputs, not full-precision internal observer state.",
                   "Set F stores hit/fp assignments but omits full detections; reassociation is not independently possible.",
                   "Timing excluded; concurrent runs and pauses prohibit performance conclusions.",
                   "Old f5 X3 is not corrected-core evidence; final 7b X3 and reviewed seal remain required.",
                   "This gate does not accept dust filtering, N6 extension, release or deployment."],
    }
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "ordinary": total, "set_F": 3060,
                      "stop_frames": sum(piece["stop_frames"] for piece in pieces)}))


if __name__ == "__main__":
    main()
