#!/usr/bin/env python3
"""Launch final seal creation or committed-seal verification in a unique clean Linux checkout."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import uuid

from launch_gate import IMAGE, DEFAULT_GIT

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-commit", required=True)
parser.add_argument("--verify-only", action="store_true")
parser.add_argument("--use-default", action="store_true")
args = parser.parse_args()
assert len(args.source_commit) == 40 and all(c in "0123456789abcdef" for c in args.source_commit)
if args.use_default and not args.verify_only:
    parser.error("--use-default is only for verification")
root = Path(__file__).resolve().parent.parent
assert root.is_dir() and Path(DEFAULT_GIT).is_dir()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
run_id = ("seal-verify" if args.verify_only else "seal-create") + "-1.1.0-" + args.source_commit[:12] + "-" + stamp + "-" + uuid.uuid4().hex[:8]
name = "rs-" + run_id.lower()
volume = name + "-checkout"
owner = "resense.integration.owner=gate-frame-infra-20261016"
subprocess.run(["docker", "volume", "create", "--label", owner, volume], check=True)
argv = ["docker", "run", "--detach", "--name", name, "--label", owner, "--network", "none", "--cpus", "2", "--memory", "1024m",
    "--env", "PYTHONHASHSEED=0", "--env", "OMP_NUM_THREADS=1", "--env", "OPENBLAS_NUM_THREADS=1", "--env", "MKL_NUM_THREADS=1", "--env", "NUMEXPR_NUM_THREADS=1", "--env", "RESENSE_NATIVE=1",
    "--mount", f"type=bind,source={DEFAULT_GIT},target=/source.git,readonly", "--mount", f"type=bind,source={root},target=/evidence",
    "--mount", f"type=bind,source={root / 'helpers'},target=/helpers,readonly", "--mount", f"type=volume,source={volume},target=/evalworkspace",
    "--workdir", "/evalworkspace", "--entrypoint", "python3", IMAGE, "/helpers/seal_in_linux.py", "--source-commit", args.source_commit, "--run-id", run_id]
if args.verify_only:
    argv.append("--verify-only")
if args.use_default:
    argv.append("--use-default")
cid = subprocess.check_output(argv, text=True).strip()
record = dict(run_id=run_id, container=name, container_id=cid, volume=volume, image=IMAGE, argv=argv,
              source_commit=args.source_commit, verify_only=args.verify_only, use_default=args.use_default)
(root / (run_id + ".launch.json")).write_bytes((json.dumps(record, indent=2) + "\n").encode())
exit_text = subprocess.check_output(["docker", "wait", name], text=True).strip()
logs = subprocess.run(["docker", "logs", name], capture_output=True)
(root / (run_id + ".container.log")).write_bytes(logs.stdout + logs.stderr)
inspect = subprocess.check_output(["docker", "inspect", name])
(root / (run_id + ".container-final.json")).write_bytes(inspect)
record["container_exit"] = int(exit_text)
(root / (run_id + ".result.json")).write_bytes((json.dumps(record, indent=2) + "\n").encode())
print(json.dumps(record, indent=2))
raise SystemExit(record["container_exit"])
