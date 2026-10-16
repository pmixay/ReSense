#!/usr/bin/env python3
"""Run metric collection and the registered explanatory state replay; retain commands."""
import json
from pathlib import Path
import subprocess
import time

from launch_gate import IMAGE, DEFAULT_CACHE, DEFAULT_GIT

ROOT = Path(__file__).resolve().parent.parent
RUN = "candidate-f8c088dc4f32-20261016T073403Z-4b64ec55"
CONTROL = "baseline-707ea9cda051-20261016T060147Z-68fb3429"
ANALYSIS = ROOT / ("analysis-" + RUN)
assert ANALYSIS.is_dir()
commands = []
for name, script, args in (
    ("metric_collection", "metrics_h3.py", ["--baseline", "/evidence/" + CONTROL, "--candidate", "/evidence/" + RUN, "--analysis", "/evidence/analysis-" + RUN]),
    ("candidate_promotion_trace", "trace_h3_candidate.py", []),
):
    argv = ["docker", "run", "--rm", "--label", "resense.integration.owner=gate-frame-infra-20261016", "--network", "none", "--cpus", "1", "--memory", "1024m",
        "--mount", f"type=bind,source={ROOT},target=/evidence", "--mount", f"type=bind,source={ROOT / 'helpers'},target=/helpers,readonly",
        "--mount", f"type=volume,source=rs-gate-candidate-f8c088dc4f32-20261016t073403z-4b64ec55-checkout,target=/evalworkspace,readonly",
        "--mount", f"type=bind,source={DEFAULT_GIT},target=/source.git,readonly",
        "--mount", f"type=bind,source={DEFAULT_CACHE},target=/data/cache,readonly",
        "--env", "PYTHONHASHSEED=0", "--env", "RESENSE_NATIVE=1", "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1", "--env", "MKL_NUM_THREADS=1", "--env", "NUMEXPR_NUM_THREADS=1",
        "--env", "/".join(["RESENSE_REPO=/evalworkspace", RUN]), "--env", f"PYTHONPATH=/evalworkspace/{RUN}:/helpers",
        "--workdir", "/evalworkspace/" + RUN, "--entrypoint", "python3", IMAGE, "/helpers/" + script, *args]
    started = time.time()
    result = subprocess.run(argv, capture_output=True)
    (ANALYSIS / (name + ".stdout.txt")).write_bytes(result.stdout)
    (ANALYSIS / (name + ".stderr.txt")).write_bytes(result.stderr)
    commands.append(dict(argv=argv, exit=result.returncode, wall_s=time.time() - started))
    (ANALYSIS / "analysis_commands.json").write_bytes((json.dumps(commands, indent=2) + "\n").encode())
    print(result.stdout.decode(), flush=True)
    if result.returncode:
        print(result.stderr.decode(), flush=True)
        raise SystemExit(result.returncode)
