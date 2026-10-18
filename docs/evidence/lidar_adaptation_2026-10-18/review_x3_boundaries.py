"""Strict independent X3 source and alarm-boundary audit, without detector calls."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from scripts import detector_freeze as freeze  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decision(row):
    assert type(row["obstacle"]) is bool and type(row["warning"]) is bool
    assert row["obstacle"] == bool(row["dets"])
    assert row["level"] in ("ok", "warn", "error")
    assert row["dlevel"] in ("ok", "warn", "error")
    if row["obstacle"]:
        return "STOP"
    if "error" in (row["level"], row["dlevel"]):
        return "FAULT"
    if row["warning"] or row["dlevel"] == "warn":
        return "CAUTION"
    return "GO"


def spans(rows):
    """Inclusive source-frame endpoints in processed order (hz5 skips source rows)."""
    result = []
    active = False
    for row in rows:
        if row["decision"] == "STOP":
            if not active:
                result.append([row["i"], row["i"]])
            else:
                result[-1][1] = row["i"]
            active = True
        else:
            active = False
    return result


def normalized(row):
    clean = {key: value for key, value in row.items()
             if key not in ("decode_ms", "detect_ms", "total_ms")}
    messages = [message for message in row["msgs"] if not message.startswith("latency p95 ")]
    if messages != row["msgs"] and row["level"] == "warn":
        clean["level"] = row["dlevel"]
    clean["msgs"] = messages
    return clean


def falcon_no_loss_review():
    """Do not turn original-data parity into a waiver of known actual-input losses."""
    folder = ROOT / "docs/evidence/n2_falcon_2026-10-18"
    associations_path = folder / "falcon_full_associations.json"
    associations = read(associations_path)
    paths = [folder / name for name in ("falcon_full/baseline.jsonl",
                                        "falcon_replay_candidate/baseline.jsonl")]
    for path in paths:
        assert sha(path) == associations["source_hashes"][str(path.relative_to(folder))]
    before, after = ([json.loads(line) for line in path.read_text().splitlines()] for path in paths)
    assert len(before) == len(after) == 4443
    lost, added = [], []
    for left, right in zip(before, after):
        assert all(left[key] == right[key] for key in ("i", "stamp", "bag_t"))
        assert decision(left) == left["decision"] and decision(right) == right["decision"]
        if left["obstacle"] and not right["obstacle"]:
            lost.append(left["i"])
        if right["obstacle"] and not left["obstacle"]:
            added.append(left["i"])
    targets = associations["cases"]["baseline"]["associated_targets"]
    person = sorted(set(lost) & set(targets["main_approach"]["stop"]))
    assert len(lost) == 13 and len(added) == 28 and person == [2972, 2973, 2974, 2975]
    summary_path = folder / "falcon_replay_candidate/summary.json"
    return {"registered_no_loss_passed": False, "frames": 4443,
            "lost_stop_frames": lost, "added_stop_frames": added,
            "lost_main_person_associated_frames": person,
            "measured_full_replay_source": read(summary_path)["source"],
            "scope": "Full replay4 candidate predates the metadata accounting fix; no evidence shows that fix removes these losses. Corrected7b prefix/orientation compatibility checks do not replace the full recording.",
            "interpretation": "Raw STOP loss is exact; person association is not surveyed in-gauge truth. First-hit/net gains do not satisfy preserve-every-existing-STOP.",
            "input_sha256": {str(path): sha(path) for path in [*paths, associations_path, summary_path]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("reference", "candidate", "review", "source", "out"):
        parser.add_argument("--" + argument, type=Path, required=True)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    old, new, audit = (read(path) for path in (args.reference, args.candidate, args.review))
    identity = read(evidence / "runtime_identity_metadata_fixed.json")
    gate_review = read(evidence / "independent_gate_boundaries.json")
    gate_report = read(evidence / "gate.json")
    assert new["status"] == "PASS" and new["errors"] == []
    assert audit["candidate_gate_status"] == "PASS"
    assert audit["case_count"] == 40 and audit["rows_compared"] == 29765
    assert audit["all_metrics_identical"] and audit["all_non_timing_fields_identical"]
    assert audit["source_protocol_labels_identical"]
    for path in (args.reference, args.candidate):
        expected = audit["input_sha256"].get(str(path))
        if expected is None:
            expected = audit["input_sha256"].get(str(path.resolve()))
        assert expected == sha(path)
    assert new["comparison"] == audit["comparison_recomputed"]
    checks = [row for case in new["comparison"]["cases"].values() for row in case]
    assert len(checks) == 260 and all(row["passed"] for row in checks)
    assert new["protocol"] == old["protocol"]
    assert new["labels"] == old["labels"]
    assert new["reference"]["sha256"] == sha(args.reference)
    commit = identity["source_commit"]
    assert new["evaluation"]["commit"] == new["harness_commit"] == commit
    assert Path(new["evaluation"]["repo"]).resolve() == args.source.resolve()
    assert Path(new["evaluation"]["import"]).resolve() == (args.source / "resense/__init__.py").resolve()
    assert new["evaluation"]["config_sha256"] == gate_report["config"]["file_sha256"]
    assert new["runtime"]["jobs"] == new["runtime"]["threads"] == 1
    files = freeze.source_hashes(args.source)
    assert len(files) == 38 and files == identity["source_files"] == freeze.source_hashes(ROOT)
    assert freeze.source_digest(files) == gate_review["source_digest"] == identity["source_sha256"]
    for name, expected in files.items():
        blob = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
    paths = ["resense", "native", "configs", "setup.py", "pyproject.toml",
             "ros2_ws/src/resense_ros/config"]
    tree = subprocess.check_output(["git", "ls-tree", "-r", commit, "--", *paths], cwd=ROOT, text=True).strip()
    assert tree == new["evaluation"]["source_tree"]
    binaries = {str(args.source / name): value for name, value in identity["native_files"].items()}
    assert new["evaluation"]["native_binaries"] == binaries
    for name, expected in binaries.items():
        assert sha(Path(name)) == expected
    for name, source in new["sources"].items():
        assert {k: v for k, v in source.items() if k != "path"} == {
            k: v for k, v in old["sources"][name].items() if k != "path"}

    cases = {}
    for key in sorted(new["entries"]):
        before, after = old["entries"][key], new["entries"][key]
        paths = [Path(entry["raw_path"]) for entry in (before, after)]
        left, right = ([json.loads(line) for line in path.read_text().splitlines()] for path in paths)
        assert len(left) == len(right) == before["metrics"]["frames"] == after["metrics"]["frames"]
        assert before["metrics"] == after["metrics"]
        for entry, path, report in zip((before, after), paths, (old, new)):
            assert sha(path) == entry["raw_sha256"]
            assert read(path.with_suffix(".complete.json"))["identity"] == report["evaluation"]
        for a, b in zip(left, right):
            assert decision(a) == a["decision"] == decision(b) == b["decision"]
            assert normalized(a) == normalized(b)
        assert spans(left) == spans(right)
        intervals = spans(right)
        cases[key] = {"frames": len(right), "decisions": dict(Counter(row["decision"] for row in right)),
                      "stop_intervals_source_frames": intervals,
                      "first_stop_frame": intervals[0][0] if intervals else None,
                      "stop_frames": sum(row["obstacle"] for row in right),
                      "stop_episodes": len(intervals), "all_semantics_and_boundaries_exact": True,
                      "reference_raw_sha256": before["raw_sha256"],
                      "candidate_raw_sha256": after["raw_sha256"]}
    assert len(cases) == 40 and sum(case["frames"] for case in cases.values()) == 29765
    falcon = falcon_no_loss_review()
    output = {"status": "DEFAULT_GATE_X3_PASS_RESEAL_BLOCKED_BY_FALCON_NO_LOSS_CONTRACT",
              "checked_utc": datetime.now(timezone.utc).isoformat(), "source_commit": commit,
              "source_files": 38, "source_digest": freeze.source_digest(files),
              "source_matches_live_immutable_git_and_gate": True,
              "native_binaries": binaries, "configuration_matches_full_default_gate": True,
              "case_count": 40, "rows_compared": 29765, "directional_checks_passed": 260,
              "all_non_timing_serialized_fields_exact": True,
              "lost_added_delayed_shortened_stop_frames": 0, "cases": cases,
              "actual_falcon_no_loss_review": falcon,
              "ordinary_gate_rows": gate_review["ordinary_rows"], "set_F_rows": gate_review["set_F_rows"],
              "input_sha256": {str(path): sha(path) for path in (Path(__file__), args.reference,
                  args.candidate, args.review, evidence / "independent_gate_boundaries.json",
                  evidence / "runtime_identity_metadata_fixed.json", evidence / "gate.json")},
              "limits": ["Serialized equality, not full-precision internal observer equality.",
                         "Historical X3 reference uses Python3.10/native build; corrected run uses Python3.12/native build recorded here.",
                         "No performance claim from concurrent runs or wall time.",
                         "Unqualified preserve-every-existing-STOP also applies to actual Falcon; known13 losses block unconditional replay4 acceptance absent an explicit criterion decision or satisfying implementation.",
                         "N3 dust suppression and N6 extension remain unaccepted; no release or deployment approval.",
                         "New seal must separately name/review actual source and all validation evidence."]}
    args.out.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"status": output["status"], "cases": 40, "rows": 29765,
                      "stop_frames": sum(case["stop_frames"] for case in cases.values()),
                      "stop_episodes": sum(case["stop_episodes"] for case in cases.values())}))


if __name__ == "__main__":
    main()
