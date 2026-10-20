#!/usr/bin/env python3
"""Run one author check, preserving exact dirty source bytes and an exit receipt."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(repo):
    files = [p for folder in ("resense", "native", "configs", "ros2_ws/src/resense_ros/config", "scripts")
             for p in (repo / folder).rglob("*") if p.is_file()
             and p.suffix in (".py", ".cpp", ".h", ".so", ".yaml") and "__pycache__" not in p.parts]
    files += [repo / p for p in ("setup.py", "pyproject.toml")]
    return {str(p.relative_to(repo)): sha(p) for p in sorted(files)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    repo = a.repo.resolve()
    prefix = Path("/tmp/opencode") / f"f1a-b1-{a.name}"
    command = a.command[1:] if a.command[0] == "--" else a.command
    before = sources(repo)
    receipt = {"command": command, "repo": str(repo), "source_sha256": before,
               "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
               "diff": subprocess.check_output(["git", "diff", "HEAD", "--", "resense", "configs",
                    "ros2_ws/src/resense_ros/config"], cwd=repo, text=True),
               "started": datetime.now(timezone.utc).isoformat()}
    with tarfile.open(str(prefix) + "-source.tar.gz", "x:gz") as archive:
        for name in before:
            archive.add(repo / name, arcname=name)
    env = dict(os.environ, RESENSE_REPO=str(repo), PYTHONPATH=str(repo), OPENBLAS_CORETYPE="Haswell",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
               LD_LIBRARY_PATH="/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu",
               RESENSE_REQUIRE_SYNTHETIC="1")
    with open(str(prefix) + ".log", "x") as log:
        result = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(returncode=result.returncode, finished=datetime.now(timezone.utc).isoformat(),
                   source_unchanged=before == sources(repo), log_sha256=sha(Path(str(prefix) + ".log")))
    Path(str(prefix) + "-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(a.name, result.returncode, receipt["source_unchanged"], flush=True)
    return result.returncode if receipt["source_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
