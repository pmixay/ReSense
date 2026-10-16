#!/usr/bin/env python3
"""Copy measured compact evidence into the parent's own new H3 evidence folder.

Raw frame JSONL remains external, indexed by hashes. Never commits or modifies source.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

COMMIT = "f8c088dc4f3243fbd15a3aae9be0459e8a0aa941"
CONTROL = "baseline-707ea9cda051-20261016T060147Z-68fb3429"
CANDIDATE = "candidate-f8c088dc4f32-20261016T073403Z-4b64ec55"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def index(destination):
    manifest = []
    for p in sorted(destination.rglob("*")):
        if p.is_file() and p.name != "HASHES.json":
            manifest.append(dict(path=p.relative_to(destination).as_posix(), bytes=p.stat().st_size, sha256=sha(p)))
    write(destination / "HASHES.json", dict(measured_commit=COMMIT, files=manifest))
    total = sum(p.stat().st_size for p in destination.rglob("*") if p.is_file())
    print(json.dumps(dict(folder=str(destination), files=len(manifest) + 1, bytes=total, index_sha256=sha(destination / "HASHES.json")), indent=2))
    if total > 3_000_000:
        raise ValueError("compact evidence exceeds the registered 3 MB budget")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--index-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    destination = args.parent / "docs/evidence/integration_2026-10-16/h3"
    assert destination.parent.is_dir()
    merge_head = subprocess.check_output(["git", "rev-parse", "--git-path", "MERGE_HEAD"], cwd=args.parent, text=True).strip()
    merge_path = Path(merge_head)
    if not merge_path.is_absolute():
        merge_path = args.parent / merge_path
    if merge_path.exists():
        raise RuntimeError("parent Git merge is active; retain external evidence and retry copy after it finishes")
    if args.index_only:
        if json.loads((destination / "RUN.json").read_text())["measured_commit"] != COMMIT:
            raise ValueError("not the owned H3 evidence folder")
        index(destination)
        return
    status = json.loads((root / (CANDIDATE + ".finalization.json")).read_text())
    if status["stage"] not in ("ready", "gate_failed") or not status["verified"]:
        raise ValueError("candidate measurement/coverage/comparison is incomplete")
    run, base = root / CANDIDATE, root / CONTROL
    diff, analysis = root / ("framediff-" + CANDIDATE), root / ("analysis-" + CANDIDATE)
    explanation = json.loads((analysis / "explained_frames.json").read_text())
    if explanation["controls"]["candidate_commit"] != COMMIT:
        raise ValueError("wrong measured candidate")
    destination.mkdir(exist_ok=False)
    package_map = []

    def copy(origin, target):
        target = target.with_suffix(".txt") if target.suffix == ".log" else target
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, target)
        package_map.append(dict(external_path=origin.relative_to(root).as_posix(),
                                package_path=target.relative_to(destination).as_posix(), mode="byte-identical copy"))

    selected = ("gate.json", "gate_comparison_rows.json", "completion.json", "verification.json", "source_before.json", "source_after.json",
        "provenance.json", "evaluation_source.json", "cache_identity.json", "observer.json", "commands.json", "native_build.log", "compiler.log", "artifact_inventory.json",
        "gate_work/config.yaml", "gate_work/config.yaml.json")
    for name, origin in (("candidate", run), ("baseline", base)):
        for relative in selected:
            target = destination / name / relative
            copy(origin / relative, target)
        for suffix in (".launch.json", ".container-final.json", ".resource_telemetry.jsonl", ".infrastructure_tests.log", ".finalization.json"):
            if suffix.endswith(".jsonl"):
                target = destination / name / "runtime.resource_telemetry.json"
                write(target, [json.loads(line) for line in (root / (origin.name + suffix)).read_text().splitlines() if line.strip()])
                package_map.append(dict(external_path=origin.name + suffix,
                    package_path=target.relative_to(destination).as_posix(), mode="lossless JSONL records as JSON array"))
            else:
                copy(root / (origin.name + suffix), destination / name / ("runtime" + suffix))
    for name in ("seal_verify_before.log", "seal_verify_after.log"):
        copy(base / name, destination / "baseline" / name)
    for name in ("summary.json", "SUMMARY.md", "setF_report_changes.json"):
        target = destination / "frame_diff" / name
        target.parent.mkdir(exist_ok=True)
        copy(diff / name, target)
    for p in analysis.iterdir():
        if p.is_file() and p.suffix in (".json", ".txt", ".md"):
            target = destination / "analysis" / p.name
            target.parent.mkdir(exist_ok=True)
            if p.name == "explained_frames.json" and p.stat().st_size > 500_000:
                compact = json.loads(p.read_text())
                all_changes = compact["other_or_unexplained_changes"]
                compact["other_or_unexplained_changes"] = all_changes[:30]
                compact["other_change_details_compacted"] = dict(total=len(all_changes), retained_examples=min(30, len(all_changes)),
                    complete_external_path=str(p), complete_sha256=sha(p))
                write(target, compact)
            else:
                copy(p, target)
    for relative in ("run_linux_gate.py", "launch_gate.py", "hooks/sitecustomize.py", "verify_run.py", "frame_diff.py", "gate_control.py", "test_frame_diff.py", "analyze_h3.py", "metrics_h3.py", "package_h3.py", "start_job.py", "trace_h3_candidate.py", "finish_h3_analysis.py", "interpret_h3_trace.py"):
        target = destination / "helpers" / relative
        target.parent.mkdir(exist_ok=True, parents=True)
        copy(root / "helpers" / relative, target)
    source_diff = subprocess.check_output(["git", "diff", "--no-ext-diff", "--no-color", "707ea9cda051369326fb9407c42488c1033dad76", COMMIT, "--",
        "resense", "native", "configs", "ros2_ws/src/resense_ros/config", "scripts/build_native.sh", "setup.py", "pyproject.toml"], cwd=args.parent)
    (destination / "measured_detector_changes.patch").write_bytes(source_diff)
    external = []
    for directory in (base, run, diff, analysis):
        for p in sorted(directory.rglob("*")):
            if p.is_file():
                external.append(dict(path=p.relative_to(root).as_posix(), bytes=p.stat().st_size, sha256=sha(p)))
    for name in (CONTROL, CANDIDATE):
        for p in sorted(root.glob(name + ".*")):
            if p.is_file():
                external.append(dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)))
    write(destination / "EXTERNAL_ARTIFACTS.json", dict(external_root=str(root), files=external))
    write(destination / "PACKAGE_MAP.json", package_map)
    write(destination / "RUN.json", dict(measured_commit=COMMIT, sealed_control_commit="707ea9cda051369326fb9407c42488c1033dad76",
        candidate_run=CANDIDATE, baseline_run=CONTROL, gate_exit=status["gate_exit"],
        candidate_source_sha256=json.loads((run / "source_after.json").read_text())["source_sha256"],
        external_root=str(root), raw_frames_external=True,
        compact_package_budget_bytes=3_000_000, parent_head_at_copy=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.parent, text=True).strip()))
    index(destination)


if __name__ == "__main__":
    main()
