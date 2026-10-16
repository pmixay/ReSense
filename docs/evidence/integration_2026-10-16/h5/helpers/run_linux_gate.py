#!/usr/bin/env python3
"""Run a committed full gate in a fresh Linux Git checkout; no source modifications."""
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

SEALED = "707ea9cda051369326fb9407c42488c1033dad76"
BASELINE = "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--baseline-control", action="store_true")
    a = ap.parse_args()
    out = Path("/evidence") / a.run_id
    out.mkdir(exist_ok=False)
    repo = Path("/evalworkspace") / a.run_id
    commands = []

    def run(cmd, name, *, cwd=None, check=True):
        started = time.time()
        print("RUN", name, json.dumps(cmd), flush=True)
        with (out / (name + ".log")).open("w") as log:
            p = subprocess.run(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT)
        commands.append(dict(argv=cmd, cwd=str(cwd) if cwd else None,
                             log=name + ".log", exit=p.returncode,
                             started_unix=started, wall_s=time.time() - started))
        dump(out / "commands.json", commands)
        if check and p.returncode:
            raise RuntimeError(f"{name} exited {p.returncode}; see {out}/{name}.log")
        return p.returncode

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=repo).decode().strip()

    run(["git", "-c", "safe.directory=/source.git", "clone", "--shared", "--no-checkout",
         "-c", "core.autocrlf=false", "-c", "core.eol=lf", "/source.git", str(repo)], "clone")
    commit = git("rev-parse", "--verify", a.commit + "^{commit}")
    if a.baseline_control and commit != SEALED:
        raise ValueError("baseline control must be the exact sealed commit")
    run(["git", "-c", "core.autocrlf=false", "checkout", "--detach", commit], "checkout", cwd=repo)
    os.environ.update(PYTHONPATH=str(repo) + ":/helpers/hooks", RESENSE_REPO=str(repo),
                      OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      NUMEXPR_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1",
                      PYTHONHASHSEED="0", RESENSE_NATIVE="1")
    sys.path[:0] = [str(repo), str(repo / "scripts")]
    import detector_freeze as freeze
    files = freeze.source_hashes(repo)
    tracked = git("ls-tree", "-r", "--name-only", commit).splitlines()
    scope = {p for p in tracked if freeze._scope(p)}
    differences = [p for p in sorted(scope & files.keys()) if
                   hashlib.sha256(subprocess.check_output(["git", "show", f"{commit}:{p}"], cwd=repo)).hexdigest() != files[p]]
    crlf = [p for p in files if b"\r\n" in (repo / p).read_bytes()]
    pyd = [str(p.relative_to(repo)) for p in (repo / "resense").rglob("*.pyd")]
    source = dict(commit=commit, head=git("rev-parse", "HEAD"),
                  source_sha256=freeze.source_digest(files), files=files,
                  inventory_matches_commit=(scope == files.keys()),
                  files_differing_from_commit=differences, crlf_files=crlf, windows_pyd=pyd,
                  git_status=git("status", "--porcelain"),
                  shared_alternates=(repo / ".git/objects/info/alternates").read_text())
    dump(out / "source_before.json", source)
    if source["git_status"] or differences or crlf or pyd or scope != files.keys() or source["head"] != commit:
        raise ValueError("checkout failed clean LF/source inventory/commit checks")
    run(["bash", "scripts/build_native.sh"], "native_build", cwd=repo)
    import resense
    from resense import _native
    if Path(resense.__file__).resolve() != repo / "resense/__init__.py" or not _native.enabled():
        raise ValueError("wrong resense import or native backend disabled")
    native = repo / "resense/_resense_native.so"
    provenance = dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                      resense_file=resense.__file__, environment={k: os.environ[k] for k in (
                          "PYTHONPATH", "RESENSE_REPO", "RESENSE_NATIVE", "PYTHONHASHSEED",
                          "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")},
                      native_status=_native.status(), native_sha256=sha(native),
                      packages={p: importlib.metadata.version(p) for p in (
                          "numpy", "scipy", "scikit-learn", "open3d", "PyYAML", "zstandard", "rosbags")},
                      cpu=Path("/proc/cpuinfo").read_text(), meminfo=Path("/proc/meminfo").read_text(),
                      cgroup={p.name: p.read_text() for p in Path("/sys/fs/cgroup").glob("*")
                              if p.name in ("memory.max", "memory.swap.max", "cpu.max", "cpuset.cpus.effective")},
                      baseline_sha256=sha(repo / BASELINE),
                      config_file_sha256=sha(repo / "configs/default.yaml"),
                      ros_config_sha256=sha(repo / "ros2_ws/src/resense_ros/config/detector.yaml"))
    dump(out / "provenance.json", provenance)
    run(["g++", "--version"], "compiler", cwd=repo)
    if a.baseline_control:
        run([sys.executable, "scripts/detector_freeze.py", "verify"], "seal_verify_before", cwd=repo)
    # Byte-for-byte input manifest (compressed compact16 input is used directly).
    inventory = []
    for directory in sorted(Path("/data/cache").iterdir()):
        if directory.is_dir():
            for p in sorted(directory.iterdir()):
                if p.is_file():
                    inventory.append(dict(path=p.relative_to("/data/cache").as_posix(),
                                          bytes=p.stat().st_size, sha256=sha(p)))
    dump(out / "cache_inventory.json", inventory)
    dump(out / "cache_identity.json", dict(files=len(inventory), bytes=sum(p["bytes"] for p in inventory),
         sha256=hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()))
    os.environ["RESENSE_CAPTURE_DIR"] = str(out / "frames")
    (out / "frames").mkdir()
    gate_exit = run([sys.executable, "scripts/regression_gate.py", "--cache", "/data/cache", "--jobs", "2",
                    "--chunks", "8", "--baseline", BASELINE, "--work", str(out / "gate_work"),
                    "--out", str(out / "gate.json")], "gate", cwd=repo, check=False)
    gate = json.loads((out / "gate.json").read_text())
    import regression_gate
    base = json.loads((repo / BASELINE).read_text())
    rows = regression_gate.compare(base, gate)
    dump(out / "gate_comparison_rows.json", rows)
    if a.baseline_control:
        run([sys.executable, "scripts/detector_freeze.py", "verify"], "seal_verify_after", cwd=repo)
    after_files = freeze.source_hashes(repo)
    after = dict(head=git("rev-parse", "HEAD"), source_sha256=freeze.source_digest(after_files),
                 files=after_files, git_status=git("status", "--porcelain"),
                 native_ignored=git("check-ignore", "resense/_resense_native.so"))
    dump(out / "source_after.json", after)
    if after_files != files or after["git_status"] or after["head"] != commit:
        raise ValueError("source or commit changed during gate")
    if gate["code"]["commit"] != commit or gate["code"]["uncommitted_detector_changes"] != []:
        raise ValueError("gate has wrong commit or dirty detector")
    set_f = json.loads((out / "gate_work/setF_straight.json").read_text())
    frame_counts = {p.name: sum(1 for _ in p.open()) for p in sorted((out / "frames").glob("*.jsonl"))}
    set_f_rows = sum(len(s["rows"]) for s in set_f["sequences"])
    captured_set_f = sum(n for p, n in frame_counts.items() if p.startswith("setF_"))
    if captured_set_f != set_f_rows or set_f_rows != 3060:
        raise ValueError(f"incomplete Set F capture: {captured_set_f}/{set_f_rows}/3060")
    dump(out / "completion.json", dict(commit=commit, gate_exit=gate_exit, passed=gate["gate"]["passed"],
         comparison_rows=len(rows), gated_rows=sum(r["gated"] for r in rows),
         same_non_latency_rows=sum(r["verdict"] == "same" for r in rows if not r["metric"].startswith("latency_ms.")),
         non_latency_rows=sum(not r["metric"].startswith("latency_ms.") for r in rows),
         frame_counts=frame_counts, total_frames=sum(frame_counts.values()), set_f_rows=set_f_rows,
         clean_source=True, seal_verified=a.baseline_control))
    print((out / "completion.json").read_text(), flush=True)
    return gate_exit


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        import traceback
        traceback.print_exc()
        raise SystemExit(2)
