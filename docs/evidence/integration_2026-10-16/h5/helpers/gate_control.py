#!/usr/bin/env python3
"""Launch/wait/verify/diff a committed candidate using the sealed same-runtime control.

Candidate usage: python gate_control.py --commit <full-committed-candidate-SHA>
Existing baseline: python gate_control.py --finish-run-id <baseline-run-id> --self-compare
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

from launch_gate import IMAGE

CONTROL = "baseline-707ea9cda051-20261016T060147Z-68fb3429"
OWNER = "resense.integration.owner=gate-frame-infra-20261016"


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def finish(root, record, control, self_compare):
    name, run_id = record["container"], record["run_id"]
    run = root / run_id
    status_path = root / (run_id + ".finalization.json")
    telemetry_path = root / (run_id + ".resource_telemetry.jsonl")
    write(status_path, dict(stage="waiting", run_id=run_id, container=name))
    while True:
        inspect = json.loads(subprocess.check_output(["docker", "inspect", name]))[0]
        if not inspect["State"]["Running"]:
            break
        stats = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{json .}}", name], capture_output=True, text=True)
        with telemetry_path.open("a", encoding="utf-8") as log:
            log.write(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                docker_stats=json.loads(stats.stdout) if stats.stdout.strip() else None,
                error=stats.stderr if stats.returncode else None)) + "\n")
        time.sleep(20)
    (root / (run_id + ".container-final.json")).write_text(json.dumps(inspect, indent=2) + "\n")
    logs = subprocess.run(["docker", "logs", name], capture_output=True)
    (root / (run_id + ".container.log")).write_bytes(logs.stdout + logs.stderr)
    gate_exit = inspect["State"]["ExitCode"]
    completed_metric_failure = gate_exit == 1 and (run / "completion.json").exists() and not inspect["State"]["OOMKilled"]
    if gate_exit != 0 and not completed_metric_failure:
        write(status_path, dict(stage="container_failed", state=inspect["State"], run_id=run_id))
        raise RuntimeError(f"gate container exited {inspect['State']['ExitCode']}; see {run}")
    cmd = ["docker", "run", "--rm", "--label", OWNER, "--network", "none", "--cpus", "1", "--memory", "512m",
           "--mount", f"type=bind,source={root},target=/evidence",
           "--mount", f"type=bind,source={root / 'helpers'},target=/helpers,readonly",
           "--mount", f"type=volume,source={record['volume']},target=/evalworkspace,readonly",
           "--mount", f"type=bind,source={record['source_git']},target=/source.git,readonly",
           "--entrypoint", "python3", IMAGE, "/helpers/verify_run.py", "/evidence/" + run_id]
    write(status_path, dict(stage="verifying", run_id=run_id, verification_argv=cmd))
    verification = subprocess.run(cmd, capture_output=True)
    (root / (run_id + ".verification.log")).write_bytes(verification.stdout + verification.stderr)
    if verification.returncode:
        raise RuntimeError("frame coverage verification failed")
    compare_out = root / (("selfdiff-" if self_compare else "framediff-") + run_id)
    diff = [sys.executable, str(root / "helpers/frame_diff.py"), "--baseline", str(run if self_compare else root / control),
            "--candidate", str(run), "--out", str(compare_out)]
    comparison = subprocess.run(diff, capture_output=True)
    (root / (run_id + ".framediff.log")).write_bytes(comparison.stdout + comparison.stderr)
    if comparison.returncode:
        raise RuntimeError("same-runtime frame comparison failed")
    tests = subprocess.run([sys.executable, "-m", "unittest", "-v", "test_frame_diff"],
                           cwd=root / "helpers", capture_output=True)
    (root / (run_id + ".infrastructure_tests.log")).write_bytes(tests.stdout + tests.stderr)
    if tests.returncode:
        raise RuntimeError("frame comparison contract checks failed")
    # Hash provenance outside the run directory as well as artifacts inside it.
    external = [dict(path=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in sorted(root.glob(run_id + ".*")) if p.is_file() and p != status_path]
    write(status_path, dict(stage="ready" if gate_exit == 0 else "gate_failed", run_id=run_id, gate_exit=gate_exit, verified=True,
          completion=json.loads((run / "completion.json").read_text()),
          frame_comparison=str(compare_out), verification_argv=cmd, comparison_argv=diff,
          infrastructure_tests_exit=tests.returncode, external_provenance=external))
    print(status_path.read_text(), flush=True)
    return gate_exit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--commit")
    group.add_argument("--finish-run-id")
    ap.add_argument("--control", default=CONTROL)
    ap.add_argument("--self-compare", action="store_true")
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    if a.commit:
        if a.self_compare:
            ap.error("--self-compare is only for finalizing the existing baseline")
        done = json.loads((root / (a.control + ".finalization.json")).read_text())
        if done["stage"] != "ready":
            raise ValueError("same-runtime control is not ready")
        if len(a.commit) != 40 or any(c not in "0123456789abcdef" for c in a.commit):
            ap.error("--commit must be an actual full committed SHA")
        output = subprocess.check_output([sys.executable, str(root / "helpers/launch_gate.py"), "--commit", a.commit], text=True)
        print(output, flush=True)
        record = json.loads(output[output.index("{"):])
    else:
        record = json.loads((root / (a.finish_run_id + ".launch.json")).read_text())
    return finish(root, record, a.control, a.self_compare)


if __name__ == "__main__":
    raise SystemExit(main())
