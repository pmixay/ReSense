#!/usr/bin/env python3
"""Review the actual versioned integrity manifest; never grant release approval."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402

MEASURED = "e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569"
OLD = "cecab1b696b8c2e101207601acd8faed96c8bfb8"
PREVIOUS_SHA = "f75231a9d52124620ec7f23ee7ecf0050bf4e668ee2e10fdb660c3dba06bbc3c"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def git_sha(commit, relative):
    return hashlib.sha256(
        subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=ROOT)
    ).hexdigest()


def checked_inputs(receipt, counter):
    for name, digest in receipt["input_sha256"].items():
        path = Path(name)
        assert path.is_absolute(), name
        assert sha(path) == digest, name
        counter[str(path)] = digest


def main():
    path = ROOT / "docs/evidence/detector_freeze_2026-10-18_1.2.0_candidate.json"
    manifest = read(path)
    assert manifest["status"] == "frozen"
    assert freeze.DEFAULT_MANIFEST == str(path.relative_to(ROOT))
    assert freeze.verify_manifest(ROOT, manifest) == []
    assert manifest["measured_commit"] == MEASURED
    assert len(manifest["files"]) == 38
    assert manifest["files"] == freeze.source_hashes(ROOT)
    assert manifest["source_sha256"] == freeze.source_digest(manifest["files"])
    evidence = manifest["source_commit"]
    assert manifest["lineage"]["evidence_commit"] == evidence
    assert manifest["lineage"]["selected_measured_commit"] == MEASURED
    for name, digest in manifest["files"].items():
        assert git_sha(MEASURED, name) == git_sha(evidence, name) == digest, name
    prefix = "docs/evidence/version_1.2.0_2026-10-18/"
    followup = "docs/evidence/p4_followup_2026-10-18/"
    oldprefix = "docs/evidence/lidar_adaptation_2026-10-18/default_off/"
    expected = {
        prefix + name
        for name in (
            "PLAN.md",
            "gate_execution.json",
            "gate_frame_review.json",
            "gate_acceptance.json",
            "raw/gate_manifest.json",
            "raw/gate.tar.gz",
            "junit-release.xml",
            "main_j1_target.json",
        )
    }
    expected |= {
        followup + name
        for name in (
            "source_continuity.json",
            "p4_intake_manifest.json",
            "version_gate_review.json",
            "check_source_continuity.py",
            "review_version_gate.py",
        )
    }
    expected |= {
        oldprefix + name
        for name in (
            "x3.json",
            "independent_x3_archive.json",
            "independent_acceptance.json",
            "INDEPENDENT_DDS_REVIEW.md",
        )
    }
    references = manifest["reviewed_supporting_evidence"]
    assert len(references) == len(expected) == 17
    assert {r["path"] for r in references} == expected
    for item in references + [manifest["baseline"], manifest["validation"]]:
        target = ROOT / item["path"]
        assert not target.is_symlink() and target.resolve().is_relative_to(ROOT)
        assert sha(target) == git_sha(evidence, item["path"]) == item["sha256"], item[
            "path"
        ]
    previous_path = ROOT / manifest["lineage"]["previous_manifest"]
    previous = read(previous_path)
    assert (
        sha(previous_path)
        == manifest["lineage"]["previous_manifest_sha256"]
        == PREVIOUS_SHA
    )
    assert git_sha(evidence, str(previous_path.relative_to(ROOT))) == PREVIOUS_SHA
    assert previous["measured_commit"] == OLD
    assert manifest["lineage"]["previous_authorization"] == previous["authorization"]
    assert all(manifest["decisions"][k] == v for k, v in previous["decisions"].items())
    assert all(limit in manifest["limits"] for limit in previous["limits"])
    for item in previous["reviewed_supporting_evidence"] + [
        previous["baseline"],
        previous["validation"],
    ]:
        assert (
            sha(ROOT / item["path"])
            == git_sha(previous["source_commit"], item["path"])
            == item["sha256"]
        )
    review = read(HERE / "version_gate_review.json")
    acceptance = read(ROOT / prefix / "gate_acceptance.json")
    assert review["status"] == "INDEPENDENT_VERSION_GATE_REVIEW_PASS"
    assert acceptance["status"] == "COMPLETE_GATE_AND_VERSION_ONLY_PARITY_PASS"
    assert review["source_commit"] == MEASURED
    assert (
        review["source_sha256"]
        == acceptance["source_sha256"]
        == manifest["source_sha256"]
    )
    assert (
        review["ordinary_rows"],
        review["ordinary_stop_frames"],
        review["ordinary_stop_intervals"],
        review["set_F_rows"],
    ) == (15269, 805, 51, 3060)
    transitives = {}
    for receipt in (review, acceptance):
        checked_inputs(receipt, transitives)
    for name in ("independent_acceptance.json", "independent_x3_archive.json"):
        historical = read(ROOT / oldprefix / name)
        assert historical["source_commit"] == OLD
        checked_inputs(historical, transitives)
    release = manifest["release_review"]
    assert release["kind"] == "candidate_integrity_only"
    assert (
        release["P4_final_acceptance"]
        == release["P3_coordination_acknowledgement"]
        == "PENDING"
    )
    assert release["release_authorized"] is False
    assert (
        "3b7d7aa7cbbf238c21f84330497697da131b7cb9"
        in manifest["decisions"]["next_J1_target"]
    )
    cfg = gate.eval_real.load_cfg(str(ROOT / freeze.CONFIG), [])
    assert cfg.calibration.orientation_replay_frames == 0
    assert cfg.track.rails_axis_extension is False
    assert cfg.cluster.column_free_max_top == 0
    result = {
        "status": "INDEPENDENT_CANDIDATE_INTEGRITY_MANIFEST_PASS",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "manifest": str(path.relative_to(ROOT)),
        "manifest_sha256": sha(path),
        "measured_commit": MEASURED,
        "evidence_commit": evidence,
        "source_sha256": manifest["source_sha256"],
        "source_files": 38,
        "supporting_references_verified": 17,
        "previous_manifest_sha256": PREVIOUS_SHA,
        "transitive_input_files_rehashed": len(transitives),
        "builtin_verification_errors": [],
        "P4_final_acceptance": "PENDING",
        "P3_coordination_acknowledgement": "PENDING",
        "release_authorized": False,
        "next_J1_target": "sealed main 1.1.0 at 3b7d7aa",
        "historical_supporting_run_commit": OLD,
        "scope": "Actual manifest bytes and committed evidence integrity verified. Not final P4 review, new-version X3/Falcon/DDS execution, J1 completion or release approval.",
        "input_sha256": {
            str(p): sha(p)
            for p in (
                Path(__file__),
                path,
                previous_path,
                ROOT / "scripts/detector_freeze.py",
                ROOT / prefix / "prepare_manifest.py",
                HERE / "version_gate_review.json",
            )
        },
        "transitive_input_sha256": transitives,
    }
    (HERE / "candidate_manifest_review.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "manifest_sha256",
                    "source_files",
                    "supporting_references_verified",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
