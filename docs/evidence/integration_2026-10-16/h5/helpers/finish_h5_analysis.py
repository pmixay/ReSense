#!/usr/bin/env python3
"""Finalize H5 metrics/frame explanations and version-only identity proof."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

from launch_gate import IMAGE, DEFAULT_GIT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", required=True)
args = parser.parse_args()
ROOT = Path(__file__).resolve().parent.parent
RUN = "candidate-52115654417a-20261016T110150Z-d9084fe4"
COMMIT = "52115654417a660669b8dddfce447692c1d782cc"
CONTROL = "baseline-707ea9cda051-20261016T060147Z-68fb3429"
ANALYSIS = ROOT / ("analysis-" + RUN)
status = json.loads((ROOT / (RUN + ".finalization.json")).read_text())
assert status["stage"] in ("ready", "gate_failed") and status["verified"]
commands = []
explain = [sys.executable, str(ROOT / "helpers/analyze_h3.py"), "--baseline", str(ROOT / CONTROL), "--candidate", str(ROOT / RUN),
    "--diff", str(ROOT / ("framediff-" + RUN)), "--out", str(ANALYSIS), "--commit", COMMIT]
result = subprocess.run(explain, capture_output=True)
if not ANALYSIS.is_dir():
    print(result.stderr.decode())
    raise SystemExit(result.returncode or 2)
(ANALYSIS / "frame_explanation.stdout.txt").write_bytes(result.stdout)
(ANALYSIS / "frame_explanation.stderr.txt").write_bytes(result.stderr)
commands.append(dict(argv=explain, exit=result.returncode))
if result.returncode:
    print(result.stderr.decode())
    raise SystemExit(result.returncode)
for name, script, argv_args in (
    ("metric_collection", "metrics_h3.py", ["--baseline", "/evidence/" + CONTROL, "--candidate", "/evidence/" + RUN, "--analysis", "/evidence/analysis-" + RUN]),
    ("final_versions_and_config", "check_final_config.py", []),
):
    argv = ["docker", "run", "--rm", "--label", "resense.integration.owner=gate-frame-infra-20261016", "--network", "none", "--cpus", "1", "--memory", "1024m",
        "--mount", f"type=bind,source={ROOT},target=/evidence", "--mount", f"type=bind,source={ROOT / 'helpers'},target=/helpers,readonly",
        "--mount", "type=volume,source=rs-gate-candidate-52115654417a-20261016t110150z-d9084fe4-checkout,target=/evalworkspace,readonly",
        "--mount", f"type=bind,source={DEFAULT_GIT},target=/source.git,readonly",
        "--env", "PYTHONHASHSEED=0", "--env", "RESENSE_NATIVE=1", "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1", "--env", "MKL_NUM_THREADS=1", "--env", "NUMEXPR_NUM_THREADS=1",
        "--env", f"RESENSE_REPO=/evalworkspace/{RUN}", "--env", f"PYTHONPATH=/evalworkspace/{RUN}:/helpers",
        "--workdir", "/evalworkspace/" + RUN, "--entrypoint", "python3", IMAGE, "/helpers/" + script, *argv_args]
    started = time.time()
    result = subprocess.run(argv, capture_output=True)
    (ANALYSIS / (name + ".stdout.txt")).write_bytes(result.stdout)
    (ANALYSIS / (name + ".stderr.txt")).write_bytes(result.stderr)
    commands.append(dict(argv=argv, exit=result.returncode, wall_s=time.time() - started))
    if result.returncode:
        print(result.stderr.decode())
        raise SystemExit(result.returncode)
    if name == "final_versions_and_config":
        (ANALYSIS / "final_versions_and_config.json").write_bytes(result.stdout)
argv = [sys.executable, str(ROOT / "helpers/h5_report.py"), "--parent", args.parent]
result = subprocess.run(argv, capture_output=True)
(ANALYSIS / "final_identity_comparison.stdout.txt").write_bytes(result.stdout)
(ANALYSIS / "final_identity_comparison.stderr.txt").write_bytes(result.stderr)
commands.append(dict(argv=argv, exit=result.returncode))
(ANALYSIS / "analysis_commands.json").write_bytes((json.dumps(commands, indent=2) + "\n").encode())
print(result.stdout.decode())
if result.returncode:
    print(result.stderr.decode())
    raise SystemExit(result.returncode)
