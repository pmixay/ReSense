#!/usr/bin/env python3
"""Verify committed H5 bytes and, when present, the byte-exact generated seal."""
import argparse
import hashlib
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", required=True)
parser.add_argument("--commit", required=True)
parser.add_argument("--with-manifest", action="store_true")
args = parser.parse_args()
PREFIX = "docs/evidence/integration_2026-10-16/h5/"
MANIFEST = "docs/evidence/detector_freeze_2026-10-16_1.1.0.json"
MEASURED = "52115654417a660669b8dddfce447692c1d782cc"


def git(*argv):
    return subprocess.check_output(["git", *argv], cwd=args.parent)


def digest(data):
    return hashlib.sha256(data).hexdigest()


commit = git("rev-parse", "--verify", args.commit + "^{commit}").decode().strip()
paths = git("diff-tree", "--no-commit-id", "--name-only", "-r", commit).decode().splitlines()
assert paths and all(p.startswith(PREFIX) or (args.with_manifest and p == MANIFEST) for p in paths)
index_bytes = git("show", commit + ":" + PREFIX + "HASHES.json")
index = json.loads(index_bytes)
assert index["measured_commit"] == MEASURED
for entry in index["files"]:
    data = git("show", commit + ":" + PREFIX + entry["path"])
    assert len(data) == entry["bytes"] and digest(data) == entry["sha256"], entry["path"]
    assert b"\r\n" not in data, entry["path"]
gate_bytes = git("show", commit + ":" + PREFIX + "candidate/gate.json")
gate = json.loads(gate_bytes)
assert gate["code"]["commit"] == MEASURED and gate["code"]["version"] == "1.1.0"
assert gate["gate"]["passed"] and not gate["gate"]["allow"] and gate["code"]["uncommitted_detector_changes"] == []
assert not git("diff", "--name-only", MEASURED, commit, "--", "resense", "native", "configs", "setup.py", "pyproject.toml", "scripts/build_native.sh", "ros2_ws/src/resense_ros/config")
result = dict(passed=True, evidence_commit=commit, measured_commit=MEASURED, committed_hashes_and_LF_verified=True,
              gate_version="1.1.0", owned_paths_only=True, source_unchanged_from_measured=True,
              index_sha256=digest(index_bytes), indexed_files=len(index["files"]) + 1)
if args.with_manifest:
    data = git("show", commit + ":" + MANIFEST)
    assert data == git("show", commit + ":" + PREFIX + "seal_create/generated_manifest.json")
    manifest = json.loads(data)
    assert manifest["measured_commit"] == MEASURED and manifest["validation"]["path"] == PREFIX + "candidate/gate.json"
    assert manifest["validation"]["sha256"] == digest(gate_bytes)
    assert digest(json.dumps(manifest["files"], sort_keys=True, separators=(",", ":")).encode()) == manifest["source_sha256"]
    for path, value in manifest["files"].items():
        for source in (MEASURED, manifest["source_commit"], commit):
            blob = git("show", source + ":" + path)
            assert digest(blob) == value and b"\r\n" not in blob, path
    result.update(manifest_sha256=digest(data), manifest_source_commit=manifest["source_commit"],
                  manifest_measured_commit=manifest["measured_commit"], source_sha256=manifest["source_sha256"],
                  committed_manifest_byte_identical_to_linux=True)
print(json.dumps(result, indent=2))
