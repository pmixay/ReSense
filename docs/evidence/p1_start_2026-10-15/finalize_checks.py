"""Validate the final handoff against preserved receipts; never rerun/tune a detector."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TESTED = "7d3d5a05c258fc26a16c711e092822ff60d59d56"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ruff", required=True)
    parser.add_argument("--p4-repo", type=Path, required=True)
    args = parser.parse_args()
    path = "tests/test_node.py"
    previous = git("show", f"{TESTED}:{path}")
    current = (ROOT / path).read_text(encoding="utf-8")
    assert ast.dump(ast.parse(previous), include_attributes=False) == ast.dump(
        ast.parse(current), include_attributes=False), "test logic changed after the full suite"
    sealed = ["resense", "native", "configs", "pyproject.toml", "setup.py",
              "ros2_ws/src/resense_ros/config", "ros2_ws/src/resense_ros/setup.py",
              "ros2_ws/src/resense_ros/package.xml"]
    assert not git("diff", "--name-only", "origin/final/silent-misses", "--", *sealed).strip()
    product = ["resense", "native", "configs", "ros2_ws", "scripts", "docker", "webapp"]
    assert not git("diff", "--name-only", TESTED, "--", *product).strip(), "product differs from tested source"
    receipt = load(HERE / "integrated_linux_checks/final-04/suite_receipt.json")
    assert receipt["pytest_exit"] == 0 and not receipt["failed"] and not receipt["skipped"]
    assert receipt["only_missing_realdata_deselected"] and len(receipt["deselected"]) == 10
    passed = sum(receipt["passed_by_file"].values())
    assert passed == 1601
    matrix = load(ROOT / "docs/evidence/node_startup_2026-10-15/docker/linux_volume_2026-10-16/summary.json")
    assert matrix["passed"] is False and matrix["complete"] is False
    rescore = load(ROOT / "docs/evidence/caution_policy_2026-10-15/scratch_baseline_rescore.json")
    assert rescore["groups"]["empty"]["selected_caution_fraction"] > 0.25
    assert rescore["groups"]["objects"]["in_gauge_object_frames"]["lost_v1_alerts"] == 19
    comparison = load(args.p4_repo / "docs/evidence/p4_start_2026-10-15/gate_strict_comparison.json")
    assert comparison["measured_commit"]["commit"].startswith("707ea9c")
    assert len(comparison["rows"]) == 208
    assert all(row["verdict"] == "same" and not row["allowed"] and not row["fails"]
               for row in comparison["rows"])
    excluded = "docs/evidence/cycle_2026-09-28/complete_timing/default/run_gate.py"
    lint = subprocess.run([args.ruff, "check", "--exclude", excluded, "."], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", check=True)
    version = subprocess.check_output([args.ruff, "--version"], text=True).strip()
    report = {
        "verification": "PASS", "tested_source": TESTED,
        "product_matches_tested_source": True, "test_node_delta_ast_equivalent": True,
        "sealed_delta_from_candidate_base": [],
        "linux_suite": {"passed": passed, "skipped": 0, "failed": 0, "data_local_deselected": 10},
        "ruff": {"version": version, "exit": lint.returncode, "scope": "CI whole-tree command",
                 "archived_runner_excluded_as_in_ci": excluded, "output": lint.stdout.strip()},
        "h0_nonlatency_rows_identical": 208,
        "s1_linux_volume": {"accepted": False, "complete": False, "measured_source": "62d055f"},
        "c1_v2": {"accepted": False, "lost_labelled_alert_frames": 19},
        "o1": "prepared; dispatch and organizer reply pending",
        "g3": "specification only; no heldout detector run",
    }
    (HERE / "FINALIZATION.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
