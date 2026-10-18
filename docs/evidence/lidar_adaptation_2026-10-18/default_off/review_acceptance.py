"""Joint strict review of fresh opt-in-only gate, X3 and actual Falcon evidence.

This never invokes a detector and never substitutes the rejected replay4 captures.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402
from scripts.decision_policy_import import load_policy  # noqa: E402

COMMIT = "cecab1b696b8c2e101207601acd8faed96c8bfb8"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def intervals(rows, index_key):
    output, active = [], False
    for row in rows:
        if row["obstacle"]:
            if active:
                output[-1][1] = row[index_key]
            else:
                output.append([row[index_key], row[index_key]])
        active = row["obstacle"]
    return output


def bound_input(review, path):
    recorded = review["input_sha256"]
    value = recorded.get(str(path), recorded.get(str(path.resolve())))
    assert value == sha(path), str(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-work", type=Path, required=True)
    parser.add_argument("--reference-work", type=Path, required=True)
    parser.add_argument("--x3-reference", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--gate-only", action="store_true",
                        help="Review completed gate only; explicitly leave joint reseal pending")
    args = parser.parse_args()
    identity = read(HERE / "runtime_identity.json")
    source = Path(identity["source_root"])
    files = freeze.source_hashes(source)
    assert identity["source_commit"] == COMMIT and len(files) == 38
    assert files == identity["files"] == freeze.source_hashes(ROOT)
    assert freeze.source_digest(files) == identity["source_sha256"]
    for name, digest in files.items():
        blob = subprocess.check_output(["git", "show", f"{COMMIT}:{name}"], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest
    for name, digest in identity["native_files"].items():
        assert sha(source / "resense" / name) == digest
    cfg = gate.eval_real.load_cfg(str(source / freeze.CONFIG), [])
    assert cfg.calibration.orientation_replay_frames == 0
    assert cfg.track.rails_axis_extension is False
    assert files[freeze.CONFIG] == files[freeze.ROS_CONFIG]

    execution = read(HERE / "gate_execution_status.json")
    assert execution["status"] == "finished" and execution["returncode"] == 0
    assert execution["source_commit"] == COMMIT
    assert execution["command"] == [
        "/home/resense/.venv/bin/python", str(source / "scripts/regression_gate.py"),
        "--cache", "/home/resense/data/gate_cache", "--jobs", "1", "--baseline",
        str(source / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"),
        "--out", str(HERE / "gate.json"), "--work", str(args.candidate_work.resolve())]
    wrapper = gzip.decompress((HERE / "run_default_off_gate.py.gz").read_bytes())
    assert hashlib.sha256(wrapper).hexdigest() == execution["wrapper_sha256"]
    execution_manifest = read(HERE / "gate_execution_manifest.json")
    assert execution_manifest["status"] == "COMPLETED_REVALIDATED_AND_ARCHIVED"
    for name, digest in execution_manifest["files"].items():
        assert sha(HERE / name) == digest
    archive_manifest = read(HERE / "raw/gate_manifest.json")
    assert sha(HERE / "raw/gate.tar.gz") == archive_manifest["archive_sha256"]
    expected = {row["member"]: row for row in archive_manifest["members"]}
    assert len(expected) == archive_manifest["member_count"] == 27
    seen = set()
    with tarfile.open(HERE / "raw/gate.tar.gz", "r:gz") as archive:
        for info in archive:
            assert info.isfile() and info.name in expected and info.name not in seen
            member = expected[info.name]
            with archive.extractfile(info) as stream:
                assert hashlib.sha256(stream.read()).hexdigest() == member["sha256"]
            assert info.size == member["bytes"] and sha(Path(member["source"])) == member["sha256"]
            seen.add(info.name)
    assert seen == set(expected)

    candidate = read(HERE / "gate.json")
    reference_path = HERE.parent / "control_9b_native/gate.json"
    reference = read(reference_path)
    control_receipt_path = HERE.parent / "control_9b_native/receipt.json"
    control_receipt = read(control_receipt_path)
    assert control_receipt["status"] == "FINISHED" and control_receipt["source_unchanged"]
    assert control_receipt["native_library_hashes"] == identity["native_files"]
    audit = read(HERE / "gate_independent_review.json")
    historical = read(source / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json")
    freeze.check_gate(historical, candidate, files[freeze.CONFIG])
    assert candidate["code"]["commit"] == COMMIT
    assert candidate["config"]["sha256"] == gate.config_info(None, [], cfg)["sha256"]
    assert cfg.to_dict() == gate.eval_real.load_cfg(str(args.candidate_work / "config.yaml"), []).to_dict()
    assert candidate["gate"] == gate.gate_summary(gate.compare(historical, candidate, []), historical,
                                                  candidate["gate"]["baseline"], [])
    bound_input(audit, HERE / "gate.json")
    bound_input(audit, reference_path)
    comparisons = gate.compare(reference, candidate, [])
    assert comparisons == audit["gate_metrics"] and not any(row["fails"] for row in comparisons)
    assert all(row["verdict"] == "same" or row["metric"].startswith("latency_ms.") for row in comparisons)
    policy = load_policy(source)
    ordinary = {}
    for name, digest in audit["candidate_raw_hashes"].items():
        a_path, b_path = args.reference_work / name, args.candidate_work / name
        assert sha(a_path) == audit["reference_raw_hashes"][name] and sha(b_path) == digest
        a, b = ([json.loads(line) for line in path.read_text().splitlines()] for path in (a_path, b_path))
        assert len(a) == len(b)
        for left, right in zip(a, b):
            assert all(left[k] == right[k] for k in ("frame", "frame_id", "stamp", "detections", "warnings",
                                                    "clear_distance", "obstacle", "warning"))
            assert policy.decision(left) == policy.decision(right)
            assert right["obstacle"] == bool(right["detections"])
            assert left["health"]["monitored_range"] == right["health"]["monitored_range"]
        assert intervals(a, "frame") == intervals(b, "frame")
        ordinary[name] = {"rows": len(b), "stop_frames": sum(row["obstacle"] for row in b),
                          "stop_intervals": intervals(b, "frame"), "exact_boundaries": True}
    assert sum(case["rows"] for case in ordinary.values()) == audit["ordinary_rows"] == 15269
    for case in audit["ordinary"].values():
        assert set(case["changed_fields"]) <= {"added:health.orientation_confirmed", "added:mount.orientation_confirmed"}
        for key in ("lost_stop_frames", "added_stop_frames", "frames_with_changed_or_missing_old_detection_payload",
                    "unconfirmed_orientation_guard_violations"):
            assert case[key] == []
    af, bf = (read(folder / "setF_straight.json") for folder in (args.reference_work, args.candidate_work))
    assert af["sequences"] == bf["sequences"]
    assert sum(len(case["rows"]) for case in bf["sequences"]) == audit["set_F_rows"] == 3060

    gate_inputs = [Path(__file__), HERE / "runtime_identity.json", HERE / "gate.json",
                   HERE / "gate_independent_review.json", reference_path, control_receipt_path,
                   HERE / "gate_execution_status.json", HERE / "gate_execution_manifest.json",
                   HERE / "raw/gate_manifest.json", HERE / "raw/gate.tar.gz"]
    if args.gate_only:
        output = {"status": "DEFAULT0_GATE_PASS_JOINT_RESEAL_PENDING",
                  "checked_utc": datetime.now(timezone.utc).isoformat(), "source_commit": COMMIT,
                  "source_sha256": identity["source_sha256"], "source_files": 38,
                  "default_replay_frames": 0, "rail_axis_extension": False,
                  "gate_no_waivers_or_overrides": True, "ordinary_rows": 15269, "set_F_rows": 3060,
                  "ordinary_boundaries": ordinary, "set_F_sequences_exact": True,
                  "lost_added_delayed_shortened_stop_frames": 0,
                  "fresh_gate_metric_verdicts": dict(Counter(row["verdict"] for row in comparisons)),
                  "verified_archive_members": len(seen),
                  "input_sha256": {str(path): sha(path) for path in gate_inputs},
                  "limits": ["Gate alone cannot authorize reseal; final-source X3 and actual Falcon are separately required.",
                             "Exact serialized STOP intervals and stored Set F rows; not surveyed truth or full-precision equivalence.",
                             "Latency excluded from acceptance; N3/N6 remain unaccepted and replay4 remains opt-in."]}
        args.out.write_text(json.dumps(output, indent=2) + "\n")
        print(json.dumps({key: output[key] for key in ("status", "source_commit", "ordinary_rows", "set_F_rows")}))
        return

    x3, xr, xa = read(HERE / "x3.json"), read(args.x3_reference), read(HERE / "x3_independent_review.json")
    bound_input(xa, HERE / "x3.json")
    bound_input(xa, args.x3_reference)
    assert x3["status"] == xa["candidate_gate_status"] == "PASS"
    assert xa["all_non_timing_fields_identical"] and xa["all_metrics_identical"] and xa["source_protocol_labels_identical"]
    assert x3["comparison"] == xa["comparison_recomputed"]
    checks = [row for case in x3["comparison"]["cases"].values() for row in case]
    assert len(checks) == 260 and all(row["passed"] for row in checks)
    assert x3["evaluation"]["commit"] == x3["harness_commit"] == COMMIT
    assert Path(x3["evaluation"]["repo"]).resolve() == source.resolve()
    assert Path(x3["evaluation"]["import"]).resolve() == (source / "resense/__init__.py").resolve()
    assert x3["evaluation"]["config_sha256"] == files[freeze.CONFIG]
    tree_paths = ["resense", "native", "configs", "setup.py", "pyproject.toml", "ros2_ws/src/resense_ros/config"]
    tree = subprocess.check_output(["git", "ls-tree", "-r", COMMIT, "--", *tree_paths], cwd=ROOT, text=True).strip()
    assert x3["evaluation"]["source_tree"] == tree
    assert x3["evaluation"]["native_binaries"] == {
        str(source / "resense" / name): digest for name, digest in identity["native_files"].items()}
    x3_helper = module(HERE.parent / "review_x3_boundaries.py", "previous_x3_helpers")
    cases = {}
    for key in x3["entries"]:
        entries = xr["entries"][key], x3["entries"][key]
        rows = []
        for entry, report in zip(entries, (xr, x3)):
            path = Path(entry["raw_path"])
            assert sha(path) == entry["raw_sha256"]
            assert read(path.with_suffix(".complete.json"))["identity"] == report["evaluation"]
            rows.append([json.loads(line) for line in path.read_text().splitlines()])
        a, b = rows
        assert len(a) == len(b) == entries[0]["metrics"]["frames"] == entries[1]["metrics"]["frames"]
        for left, right in zip(a, b):
            assert x3_helper.decision(left) == left["decision"] == x3_helper.decision(right) == right["decision"]
            assert x3_helper.normalized(left) == x3_helper.normalized(right)
        assert intervals(a, "i") == intervals(b, "i")
        cases[key] = {"rows": len(b), "stop_frames": sum(row["obstacle"] for row in b),
                      "stop_intervals": intervals(b, "i"), "exact_boundaries": True}
    assert len(cases) == 40 and sum(case["rows"] for case in cases.values()) == 29765

    falcon_path = ROOT / "docs/evidence/n2_falcon_2026-10-18/falcon_default_off/independent_review.json"
    falcon = read(falcon_path)
    assert falcon["status"] == "PASS" and all(falcon["checks"].values())
    assert falcon["source_commit"] == COMMIT and falcon["source_sha256"] == identity["source_sha256"]
    assert falcon["frames"] == 4443 and not falcon["lost_stop_frames"] and not falcon["added_stop_frames"]
    for name, digest in falcon["input_sha256"].items():
        assert sha(Path(name)) == digest
    inputs = gate_inputs + [HERE / "x3.json", HERE / "x3_independent_review.json", args.x3_reference,
                           falcon_path, HERE.parent / "review_x3_boundaries.py"]
    output = {"status": "DEFAULT0_RESEAL_RECOMMENDED_PENDING_MANIFEST_REVIEW",
              "checked_utc": datetime.now(timezone.utc).isoformat(), "source_commit": COMMIT,
              "source_sha256": identity["source_sha256"], "source_files": 38,
              "default_replay_frames": 0, "rail_axis_extension": False,
              "gate_no_waivers_or_overrides": True, "ordinary_rows": 15269, "set_F_rows": 3060,
              "ordinary_boundaries": ordinary, "x3_rows": 29765, "x3_cases": cases,
              "x3_checks_passed": 260, "falcon_rows": 4443, "falcon_checks": falcon["checks"],
              "lost_added_delayed_shortened_stop_frames": 0,
              "fresh_gate_metric_verdicts": dict(Counter(row["verdict"] for row in comparisons)),
              "input_sha256": {str(path): sha(path) for path in inputs},
              "limits": ["Original serialized and actual Falcon auto-baseline preservation; not full-precision or surveyed obstacle truth.",
                         "Set F scoring rows omit full detections; stored associations cannot be independently reassigned.",
                         "Replay4 remains explicit opt-in with its known13 lost Falcon STOP rows; its gains are not claimed for default0.",
                         "N3 dust suppression and N6 extension remain unaccepted. No release/deployment approval or timing claim.",
                         "The actual new manifest still requires independent review and successful verification."]}
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({key: output[key] for key in ("status", "source_commit", "ordinary_rows", "set_F_rows", "x3_rows", "falcon_rows")}))


if __name__ == "__main__":
    main()
