"""Paired H1 author runs with immutable logs, source snapshots and receipts."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path("/tmp/opencode/h1-core")
REF = Path("/tmp/opencode/h1-core-reference")
DATA = Path("/tmp/opencode/resense-b4-data")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(repo):
    paths = [p for folder in ["resense", "native", "configs", "ros2_ws/src/resense_ros"]
             for p in (repo / folder).rglob("*") if p.is_file() and "__pycache__" not in str(p)
             and p.suffix in [".py", ".so", ".cpp", ".yaml", ".xml"]]
    paths += [repo / "pyproject.toml", repo / "setup.py"]
    return {str(p.relative_to(repo)): sha(p) for p in sorted(paths)}


def run(name, repo, command):
    before = sources(repo)
    receipt = dict(name=name, repo=str(repo), command=list(map(str, command)), source_sha256=before,
                   commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
                   tracked_diff=subprocess.check_output(["git", "diff", "--binary"], cwd=repo, text=True),
                   started=datetime.now(timezone.utc).isoformat(), numpy=np.__version__)
    archive = WORK / f"{name}-source.tar.gz"
    with tarfile.open(archive, "x:gz") as t:
        for path in before:
            t.add(repo / path, arcname=path)
    with tarfile.open(archive) as t:
        assert all(hashlib.sha256(t.extractfile(p).read()).hexdigest() == s for p, s in before.items())
    env = dict(os.environ, RESENSE_REPO=str(repo), PYTHONPATH=str(repo), OPENBLAS_CORETYPE="Haswell",
               OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1",
               LD_LIBRARY_PATH="/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu")
    receipt["environment"] = {k: env[k] for k in ["RESENSE_REPO", "PYTHONPATH", "OPENBLAS_CORETYPE",
                                                 "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS"]}
    print("START", name, flush=True)
    with (WORK / f"{name}.log").open("x") as log:
        result = subprocess.run(list(map(str, command)), cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(returncode=result.returncode, finished=datetime.now(timezone.utc).isoformat(),
                   source_unchanged=before == sources(repo), source_archive_sha256=sha(archive),
                   log_sha256=sha(WORK / f"{name}.log"))
    (HERE / f"{name}-execution.json").write_text(json.dumps(receipt, indent=2) + "\n")
    assert receipt["source_unchanged"]
    print("END", name, result.returncode, flush=True)
    return result.returncode


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["gate", "x3"])
    p.add_argument("--revision", required=True)
    p.add_argument("--candidate-only", action="store_true")
    p.add_argument("--reference", type=Path)
    a = p.parse_args()
    assert np.__version__ == "1.26.4"
    WORK.mkdir(exist_ok=True)
    target = REF / "resense/_resense_native.so"
    if not target.exists():
        shutil.copy2(ROOT / "resense/_resense_native.so", target)
    assert sha(target) == sha(ROOT / "resense/_resense_native.so")
    pairs = [("reference", REF), ("candidate", ROOT)]
    if a.candidate_only:
        reference = json.loads((HERE / "gate-a-reference-execution.json").read_text())
        assert reference["source_sha256"] == sources(REF) and reference["source_unchanged"]
        pairs = [("candidate", ROOT)]
    if a.phase == "gate":
        def one(pair):
            side, repo = pair
            name = f"gate-{a.revision}-{side}"
            return run(name, repo, [sys.executable, repo / "scripts/regression_gate.py", "--cache", DATA / "cache",
                                   "--jobs", "4", "--baseline",
                                   repo / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json",
                                   "--out", HERE / f"{name}.json", "--work", WORK / f"{name}-work"])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(one, pairs))
    else:
        results = []
        for side, repo in pairs:
            name = f"x3-{a.revision}-{side}"
            command = [sys.executable, ROOT / "scripts/robustness_battery.py", "--repo", repo,
                       "--cache", DATA / "decoded", "--out", WORK / f"{name}.json", "-j", "2"]
            if side == "candidate":
                command += ["--reference", a.reference or WORK / f"x3-{a.revision}-reference.json"]
            results.append(run(name, repo, command))
            shutil.copy2(WORK / f"{name}.json", HERE / f"{name}.json")
    return int(any(results))


if __name__ == "__main__":
    sys.exit(main())
