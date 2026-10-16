#!/usr/bin/env python3
"""Create/verify the final seal only from a clean LF Git checkout and committed H5 evidence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

MEASURED = "52115654417a660669b8dddfce447692c1d782cc"
GATE_RUN = "candidate-52115654417a-20261016T110150Z-d9084fe4"
MANIFEST = "docs/evidence/detector_freeze_2026-10-16_1.1.0.json"
BASELINE = "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"
EVIDENCE = "docs/evidence/integration_2026-10-16/h5/candidate/gate.json"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--use-default", action="store_true")
    args = parser.parse_args()
    if args.use_default and not args.verify_only:
        parser.error("creation always uses the explicit new manifest path")
    out = Path("/evidence") / args.run_id
    out.mkdir(exist_ok=False)
    repo = Path("/evalworkspace") / args.run_id
    commands = []

    def run(argv, name, cwd=None):
        started = time.time()
        print("RUN", name, json.dumps(argv), flush=True)
        with (out / (name + ".log")).open("w") as log:
            result = subprocess.run(argv, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        commands.append(dict(argv=argv, cwd=str(cwd) if cwd else None, exit=result.returncode, log=name + ".log", wall_s=time.time() - started))
        dump(out / "commands.json", commands)
        if result.returncode:
            raise RuntimeError(f"{name} failed: {result.returncode}")

    def git(*argv):
        return subprocess.check_output(["git", *argv], cwd=repo)

    run(["git", "-c", "safe.directory=/source.git", "clone", "--shared", "--no-checkout", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "/source.git", str(repo)], "clone")
    run(["git", "-c", "core.autocrlf=false", "checkout", "--detach", args.source_commit], "checkout", cwd=repo)
    head = git("rev-parse", "HEAD").decode().strip()
    assert head == args.source_commit and not git("status", "--porcelain").strip()
    os.environ.update(PYTHONPATH=str(repo), RESENSE_REPO=str(repo), RESENSE_NATIVE="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONHASHSEED="0")
    sys.path[:0] = [str(repo), str(repo / "scripts")]
    import detector_freeze as freeze
    assert freeze.ROOT == repo and not list((repo / "resense").rglob("*.pyd"))
    files = freeze.source_hashes(repo)
    assert all(b"\r\n" not in (repo / p).read_bytes() for p in files)
    measured_paths = {p for p in git("ls-tree", "-r", "--name-only", MEASURED).decode().splitlines() if freeze._scope(p)}
    assert measured_paths == files.keys()
    for path, digest in files.items():
        assert hashlib.sha256(git("show", f"{MEASURED}:{path}")).hexdigest() == digest, path
        assert hashlib.sha256(git("show", f"{head}:{path}")).hexdigest() == digest, path
    expected_files = json.loads((Path("/evidence") / GATE_RUN / "source_after.json").read_text())["files"]
    assert files == expected_files and files[freeze.CONFIG] == files[freeze.ROS_CONFIG]
    gate_path, baseline_path = repo / EVIDENCE, repo / BASELINE
    git("ls-files", "--error-unmatch", EVIDENCE)
    assert hashlib.sha256(git("show", f"{head}:{EVIDENCE}")).hexdigest() == sha(gate_path)
    assert sha(gate_path) == sha(Path("/evidence") / GATE_RUN / "gate.json")
    assert sha(baseline_path) == "8d86d6d19ef00f0ece4fd0c924935887ba6f8b39dbfd7074c2f1577099029b30"
    gate = json.loads(gate_path.read_text())
    baseline = json.loads(baseline_path.read_text())
    assert gate["code"]["commit"] == MEASURED and gate["code"]["version"] == "1.1.0"
    assert gate["code"]["uncommitted_detector_changes"] == [] and gate["native"]["path"] == "native"
    complete = json.loads((Path("/evidence") / GATE_RUN / "completion.json").read_text())
    assert complete["gate_exit"] == 0 and complete["total_frames"] == 18329 and complete["set_f_rows"] == 3060
    freeze.check_gate(baseline, gate, files[freeze.CONFIG])
    release_files = {}
    for path in ("resense/__init__.py", "pyproject.toml", "ros2_ws/src/resense_ros/setup.py", "ros2_ws/src/resense_ros/package.xml"):
        digest = sha(repo / path)
        assert hashlib.sha256(git("show", f"{MEASURED}:{path}")).hexdigest() == digest
        assert hashlib.sha256(git("show", f"{head}:{path}")).hexdigest() == digest
        release_files[path] = digest
    manifest_args = [] if args.use_default else ["--manifest", MANIFEST]
    if args.use_default:
        assert freeze.DEFAULT_MANIFEST == MANIFEST
    preflight = dict(checkout_commit=head, measured_commit=MEASURED, source_sha256=freeze.source_digest(files), files=files,
        source_clean=True, clean_LF=True, config_sync=True, evidence_tracked=True,
        evidence_blob=git("rev-parse", f"{head}:{EVIDENCE}").decode().strip(), evidence_sha256=sha(gate_path),
        baseline_sha256=sha(baseline_path), manifest_path=MANIFEST, default_manifest=freeze.DEFAULT_MANIFEST,
        release_files=release_files,
        freeze_script_sha256=sha(repo / "scripts/detector_freeze.py"), verify_only=args.verify_only, use_default=args.use_default)
    dump(out / "preflight.json", preflight)
    if args.verify_only:
        git("ls-files", "--error-unmatch", MANIFEST)
        run([sys.executable, "scripts/detector_freeze.py", "verify", *manifest_args], "verify_before_native", cwd=repo)
    else:
        assert not (repo / MANIFEST).exists(), "new manifest already exists at source commit"
    run(["bash", "scripts/build_native.sh"], "native_build", cwd=repo)
    import resense
    from resense import _native
    assert resense.__version__ == "1.1.0" and Path(resense.__file__).resolve() == repo / "resense/__init__.py"
    assert _native.enabled() and sha(repo / "resense/_resense_native.so") == "b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534"
    assert git("check-ignore", "resense/_resense_native.so").strip()
    assert freeze.source_hashes(repo) == files and not git("status", "--porcelain").strip()
    if not args.verify_only:
        run([sys.executable, "scripts/detector_freeze.py", "create", "--manifest", MANIFEST, "--baseline", BASELINE, "--evidence", EVIDENCE], "create", cwd=repo)
    run([sys.executable, "scripts/detector_freeze.py", "verify", *manifest_args], "verify_after_native_or_create", cwd=repo)
    manifest_path = repo / MANIFEST
    manifest = json.loads(manifest_path.read_text())
    assert manifest["measured_commit"] == MEASURED and manifest["files"] == files
    assert manifest["source_sha256"] == freeze.source_digest(files) and manifest["validation"]["sha256"] == sha(gate_path)
    assert manifest["baseline"]["path"] == BASELINE and manifest["validation"]["path"] == EVIDENCE
    if not args.verify_only:
        assert manifest["source_commit"] == head
        expected_status = "?? " + MANIFEST
        assert git("status", "--porcelain").decode().strip() == expected_status
    else:
        assert not git("status", "--porcelain").strip()
    assert freeze.source_hashes(repo) == files and git("rev-parse", "HEAD").decode().strip() == head
    (out / "generated_manifest.json").write_bytes(manifest_path.read_bytes())
    dump(out / "source_after.json", dict(head=head, files=files, source_sha256=freeze.source_digest(files),
        git_status=git("status", "--porcelain").decode().strip(), frozen_source_unchanged=True,
        native_ignored=True, native_sha256=sha(repo / "resense/_resense_native.so"), native_status=_native.status(),
        resense_file=resense.__file__, resense_version=resense.__version__))
    completion = dict(passed=True, checkout_commit=head, manifest_source_commit=manifest["source_commit"],
        manifest_measured_commit=manifest["measured_commit"], source_sha256=manifest["source_sha256"],
        manifest_sha256=sha(manifest_path), manifest_bytes=manifest_path.stat().st_size,
        validation_sha256=manifest["validation"]["sha256"], baseline_sha256=manifest["baseline"]["sha256"],
        source_files=len(files), clean_LF=True, config_sync=True, frozen_source_unchanged=True,
        version="1.1.0", verify_only=args.verify_only, use_default=args.use_default,
        manifest_path=MANIFEST, evidence_path=EVIDENCE, repo_path=str(repo))
    dump(out / "completion.json", completion)
    print(json.dumps(completion, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(2)
