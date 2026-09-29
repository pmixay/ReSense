#!/usr/bin/env python3
"""Seal the validated detector, or verify its source and evidence without running the data set.

Verification uses only the standard library and works in a source archive without Git.
Creating a seal requires Git: every frozen file must match the commit named by the gate.
The seal is a reviewed change record, not a substitute for the full regression gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = "docs/evidence/detector_freeze_2026-09-27.json"
DEFAULT_BASELINE = "docs/evidence/results/regression_baseline_2026-09-26_ride_p3d.json"
SCHEMA = "resense-detector-freeze-v1"
DIRECTORIES = ("resense", "native", "configs", "ros2_ws/src/resense_ros/config")
BUILD_FILES = ("setup.py", "pyproject.toml", "scripts/build_native.sh")
GENERATED_SUFFIXES = (".pyc", ".pyo", ".so", ".o", ".a", ".dylib", ".dll")
CONFIG = "configs/default.yaml"
ROS_CONFIG = "ros2_ws/src/resense_ros/config/detector.yaml"
RECORDINGS = {
    "doubleT_obstacle", "doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
    "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scope(path: str) -> bool:
    p = PurePosixPath(path)
    if "__pycache__" in p.parts or p.suffix in GENERATED_SUFFIXES:
        return False
    return path in BUILD_FILES or any(path.startswith(d + "/") for d in DIRECTORIES)


def _relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"path must be inside the repository: {path}") from exc


def source_hashes(root: Path) -> dict[str, str]:
    """Use the filesystem inventory, so untracked additions cannot evade the seal."""
    paths = set(BUILD_FILES)
    for directory in DIRECTORIES:
        base = root / directory
        if not base.is_dir() or base.is_symlink():
            raise ValueError(f"missing or symlinked detector directory: {directory}")
        for path in base.rglob("*"):
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                raise ValueError(f"symlink in detector scope: {rel}")
            if path.is_file() and _scope(rel):
                paths.add(rel)
    out = {}
    for rel in sorted(paths):
        path = root / rel
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"missing or symlinked detector file: {rel}")
        out[rel] = sha256(path)
    return out


def source_digest(files: dict[str, str]) -> str:
    raw = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def check_gate(baseline: dict, evidence: dict, config_sha: str) -> None:
    """Require the full gate's acceptance record; never turn a partial run into a freeze."""
    gate = evidence.get("gate", {})
    if gate.get("passed") is not True:
        raise ValueError("validation evidence has no passing regression gate")
    for key in ("allow", "worse_gated", "missing_gated", "worse_allowed", "missing_allowed"):
        if key not in gate or gate[key]:
            raise ValueError(f"validation must have no waivers, missing rows or regressions: {key}")
    for name, data in (("baseline", baseline), ("validation", evidence)):
        if data.get("schema") != "resense-regression-gate-v1":
            raise ValueError(f"unsupported {name} schema")
        if set(data.get("recordings", {})) != RECORDINGS:
            raise ValueError(f"{name} must contain all six recordings")
        if not data.get("set_O", {}).get("objects"):
            raise ValueError(f"{name} must contain the organizer objects")
        for key in ("ride", "set_F_straight"):
            if data.get(key, {}).get("available") is not True:
                raise ValueError(f"{name} is missing {key}")
    config = evidence.get("config", {})
    if config.get("set") or config.get("file_sha256") != config_sha:
        raise ValueError("validation must use the current default config without overrides")
    if gate.get("baseline_config_sha256") != baseline.get("config", {}).get("sha256"):
        raise ValueError("gate and baseline effective config hashes disagree")
    if gate.get("baseline_commit") != baseline.get("code", {}).get("commit"):
        raise ValueError("gate and baseline commits disagree")
    code = evidence.get("code", {})
    if not code.get("commit") or code.get("uncommitted_detector_changes") != []:
        raise ValueError("validation must name a commit with no uncommitted detector changes")


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=30)
    if result.returncode:
        raise ValueError(f"Git could not verify validation source ({' '.join(args[:2])})")
    return result.stdout


def create_manifest(root: Path, baseline_path: Path, evidence_path: Path) -> dict:
    files = source_hashes(root)
    if files[CONFIG] != files[ROS_CONFIG]:
        raise ValueError("the canonical and ROS detector configs differ")
    baseline = json.loads(baseline_path.read_text())
    evidence = json.loads(evidence_path.read_text())
    check_gate(baseline, evidence, files[CONFIG])
    commit = evidence["code"]["commit"]
    names = _git(root, "ls-tree", "-r", "--name-only", commit).decode().splitlines()
    if {p for p in names if _scope(p)} != set(files):
        raise ValueError("current detector file inventory differs from the measured commit")
    for rel, digest in files.items():
        if hashlib.sha256(_git(root, "show", f"{commit}:{rel}")).hexdigest() != digest:
            raise ValueError(f"detector file differs from the measured commit: {rel}")
    return {
        "schema": SCHEMA,
        "status": "frozen",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "authorization": "User delegated captain work and requested detector freeze on 2026-09-26.",
        "source_commit": _git(root, "rev-parse", "HEAD").decode().strip(),
        "measured_commit": commit,
        "source_sha256": source_digest(files),
        "files": files,
        "config_file_sha256": files[CONFIG],
        "effective_config_sha256": evidence["config"]["sha256"],
        "baseline": {"path": _relative(root, baseline_path), "sha256": sha256(baseline_path)},
        "validation": {"path": _relative(root, evidence_path), "sha256": sha256(evidence_path),
                       "measured_at": evidence.get("created"), "kind": "committed full regression gate"},
        "decisions": {"candidate_B": "not shipped: one extra STOP frame at 7.1 m; keep voxel bar 10",
                      "axis_union": "off: the organizers measure the envelope from the rail heads (answer of 29.09); "
                                    "gauge.reference 3 keeps the bounded union"},
        "change_policy": "Blocker fixes only; review the fix, repeat affected checks and the full gate, then replace this seal.",
        "limits": ["Verification checks source and evidence integrity; it does not replay recordings.",
                   "Node, launch, Docker and documentation have separate acceptance checks.",
                   "A detector freeze is not a release, deployment approval or proof of safety."],
    }


def verify_manifest(root: Path, manifest: dict) -> list[str]:
    errors = []
    if manifest.get("schema") != SCHEMA or manifest.get("status") != "frozen":
        return ["unsupported or unfrozen manifest"]
    try:
        actual = source_hashes(root)
        expected = manifest["files"]
        errors += [f"added detector file: {p}" for p in sorted(actual.keys() - expected.keys())]
        errors += [f"missing detector file: {p}" for p in sorted(expected.keys() - actual.keys())]
        errors += [f"changed detector file: {p}" for p in sorted(actual.keys() & expected.keys())
                   if actual[p] != expected[p]]
        if source_digest(expected) != manifest.get("source_sha256"):
            errors.append("manifest source digest disagrees with its inventory")
        if actual[CONFIG] != manifest.get("config_file_sha256") or actual[CONFIG] != actual[ROS_CONFIG]:
            errors.append("canonical / ROS config does not match the freeze")
        evidence = {}
        for key in ("baseline", "validation"):
            ref = manifest[key]
            path = root / ref["path"]
            if _relative(root, path) != ref["path"] or path.is_symlink():
                raise ValueError(f"invalid {key} path")
            if sha256(path) != ref["sha256"]:
                errors.append(f"changed {key} evidence: {ref['path']}")
            evidence[key] = json.loads(path.read_text())
        check_gate(evidence["baseline"], evidence["validation"], actual[CONFIG])
        if evidence["validation"]["config"]["sha256"] != manifest.get("effective_config_sha256"):
            errors.append("effective config hash disagrees with validation")
        if evidence["validation"]["code"]["commit"] != manifest.get("measured_commit"):
            errors.append("measured commit disagrees with validation")
    except (KeyError, TypeError, ValueError, OSError) as exc:
        errors.append(str(exc))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("create", "verify"))
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--evidence", help="full gate JSON; required for create")
    args = parser.parse_args(argv)
    path = ROOT / args.manifest
    try:
        if args.command == "create":
            if not args.evidence:
                parser.error("create requires --evidence")
            if _scope(_relative(ROOT, path)):
                raise ValueError("manifest must be outside the frozen source scope")
            result = create_manifest(ROOT, ROOT / args.baseline, ROOT / args.evidence)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, indent=2) + "\n")
            print(f"FROZEN: {len(result['files'])} files; source {result['source_sha256']}")
            print(f"Validation: {result['validation']['path']} (measured {result['validation']['measured_at']})")
        else:
            result = json.loads(path.read_text())
            errors = verify_manifest(ROOT, result)
            if errors:
                print("Detector freeze FAIL:\n" + "\n".join(f"- {e}" for e in errors), file=sys.stderr)
                return 1
            print(f"Detector freeze PASS: {len(result['files'])} files; source {result['source_sha256']}")
            print("Integrity check only; no recordings replayed.")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Detector freeze ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
