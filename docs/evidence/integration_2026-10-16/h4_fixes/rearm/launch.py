"""Isolated, commit-pinned Linux verification; no host production imports."""
import argparse
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
IMAGE = "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
ap = argparse.ArgumentParser()
ap.add_argument("commit")
ap.add_argument("label")
args = ap.parse_args()
commit = subprocess.check_output(["git", "rev-parse", args.commit], cwd=ROOT, text=True).strip()
common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, text=True).strip()
common = (ROOT / common).resolve()
out = HERE / args.label
assert HERE.is_dir() and not out.exists(), out
out.mkdir()
name = "rs-h4-rearm-" + args.label
script = "docs/evidence/integration_2026-10-16/h4_fixes/rearm/verify.py"
bootstrap = (
    "import pathlib,subprocess,sys; "
    "assert pathlib.Path('/tmp').is_dir(); "
    "subprocess.run(['git','-c','safe.directory=/source.git','clone','--no-hardlinks','--no-checkout','/source.git','/tmp/repo'],check=True); "
    f"subprocess.run(['git','-C','/tmp/repo','checkout','--detach','{commit}'],check=True); "
    f"subprocess.run(['python3','/tmp/repo/{script}'],cwd='/tmp/repo',check=True)"
)
cmd = ["docker", "run", "--name", name, "--network", "none", "--cpus", "2", "--memory", "2048m",
       "--memory-swap", "3072m", "--mount", f"type=bind,source={common},target=/source.git,readonly",
       "--mount", f"type=bind,source={out},target=/out"]
for key, value in dict(PYTHONPATH="/tmp/repo", RESENSE_REPO="/tmp/repo", H4_OUT="/out",
                       RESENSE_NATIVE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0",
                       OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       NUMEXPR_NUM_THREADS="1", H4_SOURCE_COMMIT=commit).items():
    cmd += ["--env", key + "=" + value]
cmd += ["--entrypoint", "python3", IMAGE, "-c", bootstrap]
result = subprocess.run(cmd, capture_output=True, text=True)
(out / "launch.json").write_text(json.dumps(dict(argv=cmd, source_commit=commit, image=IMAGE,
                                               returncode=result.returncode), indent=2) + "\n")
(out / "console.txt").write_text(result.stdout + result.stderr)
print(result.stdout + result.stderr)
raise SystemExit(result.returncode)
