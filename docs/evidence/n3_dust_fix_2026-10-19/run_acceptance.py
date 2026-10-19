#!/usr/bin/env python3
"""Serial / sharded N3 acceptance stages; records commands, identities, exit codes, log hashes.

    run_acceptance.py --stage <name> --source <candidate checkout> --reference <aec88d2 checkout>
        [--on-source <candidate checkout whose YAML has dust.enabled: true>]

Raw outputs go to --work (outside Git); the receipt <stage>_execution.json and logs go here.
Refuses to overwrite an existing receipt. Environment: Haswell BLAS, one thread per process.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path(__file__).resolve().parent
EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
SHARDS = [["squareT_platform_squareT_switch"], ["doubleT_obstacle", "doubleT_platform", "roundT_doubleT"],
          ["roundT_squareT_pressureGate_squareT"], ["roundT_pressureGate_roundT", "cloud_with_fake_obj"]]
FALCON = "https://disk.yandex.ru/d/SfBeRHbs8bNJAQ"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def identity(repo):
    sys.path.insert(0, str(repo / "scripts"))
    from detector_freeze import source_hashes, source_digest
    sys.path.pop(0)
    files = source_hashes(repo)
    git = lambda *w: subprocess.check_output(["git", *w], cwd=repo, text=True).strip()
    return {"path": str(repo), "commit": git("rev-parse", "HEAD"), "dirty": git("status", "--porcelain", "--", ".", ":!docs/evidence/n3_dust_fix_2026-10-19"),
            "frozen_set_sha256": source_digest(files),
            "detector_files": {str(p.relative_to(repo)): sha(p) for p in sorted((repo / "resense").glob("*.py"))},
            "config_sha256": sha(repo / "configs/default.yaml"),
            "native": {p.name: sha(p) for p in (repo / "resense").glob("*.so")}}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--source", type=Path, required=True)
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--on-source", type=Path)
    ap.add_argument("--work", type=Path, default=Path("/data/acceptance"))
    ap.add_argument("--cache", type=Path, default=Path("/data/decoded"))
    ap.add_argument("--gate-cache", type=Path, default=Path("/data/gate_cache"))
    a = ap.parse_args()
    source, reference = a.source.resolve(), a.reference.resolve()
    receipt_path = OUT / f"{a.stage}_execution.json"
    assert not receipt_path.exists(), "refuse to overwrite evidence"
    work = a.work / a.stage
    work.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, OPENBLAS_CORETYPE="Haswell", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    repos = {"source": source, "reference": reference}
    if a.on_source:
        repos["on_source"] = a.on_source.resolve()
    receipt = {"stage": a.stage, "runner_sha256": sha(Path(__file__)), "python": sys.version,
               "identities": {k: identity(v) for k, v in repos.items()},
               "environment": {k: env[k] for k in ("OPENBLAS_CORETYPE", "OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")},
               "work": str(work), "runs": [], "status": "running"}

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")

    def launch(name, command, repo):
        command = [str(c) for c in command]
        log = OUT / "logs" / f"{a.stage}__{name}.log"
        log.parent.mkdir(exist_ok=True)
        entry = {"name": name, "command": command, "cwd": str(repo),
                 "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        receipt["runs"].append(entry)
        stream = log.open("x")
        proc = subprocess.Popen(command, cwd=repo, stdout=stream, stderr=subprocess.STDOUT,
                                env=dict(env, RESENSE_REPO=str(repo),
                                         PYTHONPATH=f"{repo}:{repo}/ros2_ws/src/resense_ros"))
        return proc, entry, log, stream, time.monotonic()

    def run_parallel(jobs):
        started = [launch(*j) for j in jobs]
        save()
        ok = True
        for proc, entry, log, stream, t0 in started:
            rc = proc.wait()
            stream.close()
            entry.update(exit=rc, wall_s=round(time.monotonic() - t0, 1), log_sha256=sha(log),
                         finished_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            ok &= rc == 0
            save()
        return ok

    py = sys.executable
    s = a.stage
    jobs = []
    if s.startswith("battery-"):          # battery-on | battery-off | battery-ref | dim-*
        kind = s.split("-", 1)[1]
        repo = reference if kind == "ref" else source
        extra = ["--set", "dust.enabled=true"] if kind == "on" else []
        for k, bags in enumerate(SHARDS):
            jobs.append((f"shard{k}", [py, repo / "scripts/dust_battery.py", "--cache", a.cache, "--out", work / f"shard{k}",
                                       "--detector-root", repo, "--bags", ",".join(bags), "--seed", "20261018", *extra], repo))
    elif s.startswith("dim-"):             # dim-on | dim-off | dim-ref
        kind = s.split("-", 1)[1]
        repo = reference if kind == "ref" else source
        extra = ["--set", "dust.enabled=true"] if kind == "on" else []
        jobs.append(("dim", [py, repo / "scripts/dust_battery.py", "--cache", a.cache, "--out", work / "dim",
                             "--detector-root", repo, "--bags", "doubleT_obstacle", "--seed", "20261018",
                             "--dim-labels", "1", *extra], repo))
    elif s.startswith("gate-"):            # gate-on | gate-off | gate-ref
        kind = s.split("-", 1)[1]
        repo = reference if kind == "ref" else source
        extra = ["--set", "dust.enabled=true"] if kind == "on" else []
        jobs.append(("gate", [py, repo / "scripts/regression_gate.py", "--cache", a.gate_cache, "--jobs", "4",
                              "--baseline", repo / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json",
                              "--out", work / "gate.json", "--work", work / "rows", *extra], repo))
    elif s.startswith("x3-"):              # x3-ref | x3-on | x3-off  (on uses --on-source's YAML)
        kind = s.split("-", 1)[1]
        repo = {"ref": reference, "off": source, "on": repos.get("on_source")}[kind]
        assert repo is not None, "x3-on needs --on-source"
        ref_json = [] if kind == "ref" else ["--reference", a.work / "x3-ref" / "x3.json"]
        jobs.append(("x3", [py, source / "scripts/robustness_battery.py", "--repo", repo, "--cache", a.cache,
                            *ref_json, "--out", work / "x3.json", "-j", "4"], repo))
    elif s == "falcon-full":
        jobs.append(("falcon_full", [py, OUT / "falcon_dust_stream.py", FALCON, "--mode", "full", "--out", work / "full"], source))
    elif s.startswith("falcon-"):          # falcon-empty-on | falcon-empty-off | falcon-person-on | falcon-person-off
        _, window, kind = s.split("-")
        rng = {"empty": ("0", "1700"), "person": ("2700", "4400")}[window]
        jobs.append((f"falcon_{window}_{kind}", [py, OUT / "falcon_dust_stream.py", FALCON, "--mode", "window",
                                                 "--start", rng[0], "--end", rng[1], "--guard", kind,
                                                 "--out", work / "window"], source))
    else:
        raise SystemExit(f"unknown stage {s}")
    ok = run_parallel(jobs)
    receipt["identities_end"] = {k: identity(v) for k, v in repos.items()}
    receipt["identity_unchanged"] = receipt["identities_end"] == receipt["identities"]
    receipt["status"] = "complete" if ok and receipt["identity_unchanged"] else "failed"
    save()
    print(a.stage, receipt["status"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
