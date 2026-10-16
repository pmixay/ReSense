#!/usr/bin/env python3
"""Verify compact/external evidence hashes, LF bytes and ordinary Git addability."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", type=Path, required=True)
parser.add_argument("--folder", choices=("h3", "h3_withdrawn", "h3_selected", "h5"), default="h3")
parser.add_argument("--commit", default="f8c088dc4f3243fbd15a3aae9be0459e8a0aa941")
args = parser.parse_args()
destination = args.parent / "docs/evidence/integration_2026-10-16" / args.folder
manifest = json.loads((destination / "HASHES.json").read_text())
assert manifest["measured_commit"] == args.commit
paths = []
for entry in manifest["files"]:
    p = destination / entry["path"]
    assert p.stat().st_size == entry["bytes"] and sha(p) == entry["sha256"], entry["path"]
    assert b"\r\n" not in p.read_bytes(), "CRLF: " + entry["path"]
    paths.append(p.relative_to(args.parent).as_posix())
actual = {p.relative_to(destination).as_posix() for p in destination.rglob("*") if p.is_file() and p.name != "HASHES.json"}
assert actual == {entry["path"] for entry in manifest["files"]}
ignore = subprocess.run(["git", "check-ignore", "--stdin"], cwd=args.parent, input="\n".join(paths) + "\n", capture_output=True, text=True)
assert ignore.returncode == 1 and not ignore.stdout, ignore.stdout + ignore.stderr
external = json.loads((destination / "EXTERNAL_ARTIFACTS.json").read_text())
for entry in external["files"]:
    p = Path(external["external_root"]) / entry["path"]
    assert p.stat().st_size == entry["bytes"] and sha(p) == entry["sha256"], entry["path"]
evaluation = json.loads((destination / "analysis/evaluation_and_config.json").read_text())
assert evaluation["all_active_evaluator_and_labels_identical"]
for name in ("same_runtime", "shell_off_2026_09_29"):
    summary = json.loads((destination / ("analysis/metrics_vs_" + name + ".json")).read_text())["summary"]
    assert summary["passed"] and summary["identical_non_latency_rows"] == summary["non_latency_rows"] == 208
    assert summary["gated_rows"] == 146 and not summary["allow"] and not summary["changed_non_latency_rows"]
total = sum(p.stat().st_size for p in destination.rglob("*") if p.is_file())
assert total < 3_000_000
print(json.dumps(dict(passed=True, compact_files=len(paths) + 1, compact_bytes=total, compact_clean_LF=True,
    ignored_compact_files=[], external_artifacts_verified=len(external["files"]),
    measured_commit=manifest["measured_commit"], index_sha256=sha(destination / "HASHES.json")), indent=2))
