"""Run an immutable historical detector on the final gate's current inputs/runtime."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hashes(source):
    paths = subprocess.check_output(
        ["git", "ls-files", "resense", "configs", "native", "scripts", "labels", "setup.py"],
        cwd=source, text=True,
    ).splitlines()
    return {p: sha(source / p) for p in paths}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.source, args.candidate_source, args.cache, args.out = (
        p.resolve() for p in (args.source, args.candidate_source, args.cache, args.out)
    )
    if args.out.exists():
        raise ValueError("Choose a new output directory; existing evidence is never overwritten")
    source_hashes = hashes(args.source)
    harness_paths = ["scripts/" + name for name in (
        "regression_gate.py", "eval_real.py", "far_range_eval.py", "cache_io.py",
        "score_fake_objects.py")]
    if any(sha(args.candidate_source / p) != source_hashes[p] for p in harness_paths):
        raise ValueError("Historical and candidate harness scripts differ")
    native = {p.name: sha(p) for p in (args.source / "resense").glob("*.so")}
    candidate_native = {p.name: sha(p) for p in (args.candidate_source / "resense").glob("*.so")}
    if not native or native != candidate_native:
        raise ValueError("Control and candidate must have byte-identical native libraries")
    if sha(args.source / "native/resense_native.cpp") != sha(args.candidate_source / "native/resense_native.cpp"):
        raise ValueError("Native source differs")
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain", "--", "resense", "configs", "native", "scripts", "labels", "setup.py"],
        cwd=args.source, text=True,
    )
    if dirty:
        raise ValueError("Historical source worktree is dirty")
    args.out.mkdir(parents=True)
    baseline = args.source / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"
    command = [sys.executable, str(args.source / "scripts/regression_gate.py"),
               "--cache", str(args.cache), "--jobs", "1", "--chunks", "8",
               "--baseline", str(baseline), "--out", str(args.out / "gate.json"),
               "--work", str(args.out / "work")]
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1", "OPENBLAS_CORETYPE": "Haswell",
           "PYTHONPATH": str(args.source)}
    # No transformed-input experiment may leak into this ordinary control.
    for key in list(env):
        if key.startswith("RESENSE_N2_"):
            del env[key]
    receipt = {
        "status": "RUNNING", "command": command, "pid": os.getpid(), "pgid": os.getpgrp(),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=args.source, text=True).strip(),
        "source_hashes": source_hashes, "same_harness_as_candidate": True,
        "compared_harness_paths": harness_paths,
        "native_library_hashes": native, "same_native_as_candidate": True,
        "candidate_source": str(args.candidate_source), "python": platform.python_version(),
        "dependencies": {name: importlib.metadata.version(name) for name in ("numpy", "scipy", "open3d")},
        "nominal_stamps": False, "chunks": 8, "jobs": 1, "blas_coretype": "Haswell",
        "timings_informational_shared_cpu": True, "wrapper_sha256": sha(Path(__file__)),
        "baseline_sha256": sha(baseline),
        "cache_receipt_hashes": {str(p.relative_to(args.cache)): sha(p) for p in (
            args.cache / "originals_receipt.json", args.cache / "set_o_receipt.json",
            args.cache / "ride_receipt.json", args.cache / "new_data/intake_manifest.json")},
        "scope": "Serialized per-frame ordinary gate outputs and Set F scoring/placement rows; not a full-precision observer capture",
    }
    receipt_path = args.out / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    started = time.monotonic()
    with (args.out / "gate.log").open("w") as log:
        result = subprocess.run(command, cwd=args.source, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(status="FINISHED", returncode=result.returncode,
                   wall_s=time.monotonic() - started,
                   finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   source_unchanged=hashes(args.source) == source_hashes)
    if (args.out / "gate.json").exists():
        receipt["gate_sha256"] = sha(args.out / "gate.json")
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
