"""Independently bind the final manifest to source, lineage and supporting bytes."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def git_sha(commit, name):
    value = subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=ROOT)
    return hashlib.sha256(value).hexdigest()


def main():
    path = ROOT / "docs/evidence/detector_freeze_2026-10-18_lidar.json"
    manifest = read(path)
    assert freeze.DEFAULT_MANIFEST == str(path.relative_to(ROOT))
    assert freeze.verify_manifest(ROOT, manifest) == []
    measured = "cecab1b696b8c2e101207601acd8faed96c8bfb8"
    assert manifest["measured_commit"] == measured
    identity = read(HERE / "runtime_identity.json")
    assert manifest["files"] == identity["files"] == freeze.source_hashes(Path(identity["source_root"]))
    assert len(manifest["files"]) == 38
    assert manifest["source_sha256"] == identity["source_sha256"]
    evidence_commit = manifest["source_commit"]
    assert manifest["lineage"]["evidence_commit"] == evidence_commit
    assert manifest["lineage"]["selected_measured_commit"] == measured
    for name, digest in manifest["files"].items():
        assert git_sha(measured, name) == git_sha(evidence_commit, name) == digest
    references = manifest["reviewed_supporting_evidence"]
    assert len(references) == len({row["path"] for row in references}) == 15
    for row in references + [manifest["baseline"], manifest["validation"]]:
        ref = ROOT / row["path"]
        assert not ref.is_symlink() and ref.resolve().is_relative_to(ROOT)
        assert sha(ref) == git_sha(evidence_commit, row["path"]) == row["sha256"]
    previous_path = ROOT / manifest["lineage"]["previous_manifest"]
    previous = read(previous_path)
    assert sha(previous_path) == manifest["lineage"]["previous_manifest_sha256"]
    assert manifest["lineage"]["previous_authorization"] == previous["authorization"]
    assert all(manifest["decisions"][key] == value for key, value in previous["decisions"].items())
    assert all(limit in manifest["limits"] for limit in previous["limits"])
    cfg = gate.eval_real.load_cfg(str(ROOT / freeze.CONFIG), [])
    assert cfg.calibration.orientation_replay_frames == 0
    assert cfg.track.rails_axis_extension is False and cfg.cluster.column_free_max_top == 0
    acceptance = read(HERE / "independent_acceptance.json")
    assert acceptance["status"] == "DEFAULT0_RESEAL_RECOMMENDED_PENDING_MANIFEST_REVIEW"
    assert acceptance["source_commit"] == measured and acceptance["source_sha256"] == manifest["source_sha256"]
    for name in ("independent_acceptance.json", "independent_x3_archive.json"):
        for filename, digest in read(HERE / name)["input_sha256"].items():
            assert sha(Path(filename)) == digest
    result = {"status": "INDEPENDENT_MANIFEST_REVIEW_PASS",
              "checked_utc": datetime.now(timezone.utc).isoformat(), "manifest": str(path.relative_to(ROOT)),
              "manifest_sha256": sha(path), "measured_commit": measured,
              "evidence_commit": evidence_commit, "source_sha256": manifest["source_sha256"],
              "source_files": 38, "supporting_references_verified": 15,
              "builtin_verification_errors": [], "all_supporting_bytes_committed_at_evidence_commit": True,
              "lineage_and_inherited_decisions_retained": True,
              "default_replay_frames": 0, "rail_axis_extension": False, "column_free_max_top": 0,
              "manual_scope_review": "Current user opt-in choice, rejection of default4 without waiver, explicit C2 profile, N3/N6/H1 limitations, separate node/image checks and no release/deployment all retained.",
              "builtin_verifier_limit_acknowledged": "Additional15 hashes verified here; built-in verifier validates only source/baseline/gate and never replays data.",
              "input_sha256": {str(p): sha(p) for p in [Path(__file__), path, previous_path,
                  ROOT / "scripts/detector_freeze.py", HERE / "independent_acceptance.json",
                  HERE / "independent_x3_archive.json"]}}
    (HERE / "manifest_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "manifest_sha256", "source_files", "supporting_references_verified")}))


if __name__ == "__main__":
    main()
