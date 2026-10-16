"""Owned H4 runner. /review is the owned evidence folder; /work is a fresh volume."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

TARGET = "7cc640fb39698b1fe45bc6ab069eab68ad4ac6ae"
CONTROL = "707ea9cda051369326fb9407c42488c1033dad76"
OUT = Path("/review/run-001")
TARGET_ROOT = Path("/work/target")
CONTROL_ROOT = Path("/work/control")
TESTS = [
    "test_core.py", "test_algorithm.py", "test_modules.py", "test_native.py",
    "test_wall_drift.py", "test_history_robustness.py", "test_clear_cap.py",
    "test_clear_cap_persist.py", "test_column_free_top.py", "test_structure_cut.py",
    "test_stop_keep.py", "test_near_escalation.py", "test_explained_run.py",
    "test_far_thin.py", "test_reseed_safety.py", "test_detector_timing.py",
    "test_envelope_reference.py", "test_edge_margin_quadratic.py",
    "test_node.py", "test_fastcloud.py", "test_decision_policy.py",
    "test_rescore_decisions.py",
]


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def run(name, argv, cwd=None, env=None):
    started = time.time()
    proc = subprocess.run(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT)
    (OUT / f"{name}.txt").write_bytes(proc.stdout)
    row = {"name": name, "argv": list(map(str, argv)), "cwd": str(cwd),
           "exit": proc.returncode, "elapsed_informational_s": time.time() - started}
    with (OUT / "commands.jsonl.txt").open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(json.dumps(row), flush=True)
    return proc.returncode


def inventory(root, name):
    inv = json.loads((TARGET_ROOT / "docs/evidence/integration_2026-10-16/h3" /
                      name / "source_before.json").read_text())
    rows = {}
    for rel, expected in inv["files"].items():
        data = (root / rel).read_bytes()
        git_data = subprocess.check_output(["git", "show", f"HEAD:{rel}"], cwd=root)
        actual = hashlib.sha256(data).hexdigest()
        rows[rel] = {"sha256": actual, "matches_h3": actual == expected,
                     "matches_git": data == git_data, "crlf": b"\r\n" in data}
    answer = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                              text=True).strip(), "files": rows,
              "tracked_status": subprocess.check_output(
                  ["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, text=True),
              "windows_pyd": [str(p) for p in root.rglob("*.pyd")]}
    assert all(r["matches_h3"] and r["matches_git"] and not r["crlf"] for r in rows.values())
    assert not answer["tracked_status"] and not answer["windows_pyd"]
    return answer


def setup_units():
    OUT.mkdir(exist_ok=False)
    for name, sha in (("target", TARGET), ("control", CONTROL)):
        root = Path("/work") / name
        assert run(f"clone_{name}", ["git", "-c", "safe.directory=/source.git", "clone",
                   "--shared", "--no-checkout", "/source.git", str(root)]) == 0
        assert run(f"checkout_{name}", ["git", "-c", "core.autocrlf=false", "checkout",
                   "--detach", sha], root) == 0
        assert run(f"native_{name}", ["bash", "scripts/build_native.sh"], root) == 0
    write("source_before.json", {"target": inventory(TARGET_ROOT, "candidate"),
                                "control": inventory(CONTROL_ROOT, "baseline")})
    env = dict(os.environ, PYTHONPATH=str(TARGET_ROOT), RESENSE_REPO=str(TARGET_ROOT),
               RESENSE_REQUIRE_SYNTHETIC="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    assert run("imports", [sys.executable, "/review/provenance.py"], TARGET_ROOT, env) == 0
    status = run("unit_suites", [sys.executable, "-m", "pytest", "-q", "-rs",
                 "-o", "cache_dir=/work/pytest-cache", "--junitxml=" + str(OUT / "units.xml"),
                 *[str(TARGET_ROOT / "tests" / f) for f in TESTS]], TARGET_ROOT, env)
    write("source_after_units.json", {"target": inventory(TARGET_ROOT, "candidate"),
                                     "control": inventory(CONTROL_ROOT, "baseline")})
    write("unit_completion.json", {"exit": status, "target": TARGET, "control": CONTROL,
                                   "test_files": TESTS})
    return status


if __name__ == "__main__":
    raise SystemExit(setup_units())
