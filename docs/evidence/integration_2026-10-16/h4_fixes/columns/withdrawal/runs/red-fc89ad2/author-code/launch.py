"""Committed-source Linux withdrawal checks; no production overlays or host native builds."""
import argparse
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
ROOT = P.parents[5]
TEMP = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode")
IMAGE = "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
ap = argparse.ArgumentParser()
ap.add_argument("run")
ap.add_argument("task", choices=["tests", "probes", "dark"])
ap.add_argument("--mode", default="all")
ap.add_argument("--sealed", action="store_true")
a = ap.parse_args()
assert TEMP.is_dir() and (ROOT / "resense").is_dir()
base = TEMP / "resense-h4-column-withdrawal-20261016"
base.mkdir(exist_ok=True)
run = base / a.run
run.mkdir(exist_ok=False)
code = run / "author-code"
code.mkdir()
for p in P.glob("*.py"):
    (code / p.name).write_bytes(p.read_bytes().replace(b"\r\n", b"\n"))
head = "707ea9cda051369326fb9407c42488c1033dad76" if a.sealed else subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
name = "rs-h4-withdrawal-" + a.run
volume = name + "-source"
subprocess.run(["docker", "volume", "create", volume], check=True, capture_output=True)
cmd = ["docker", "run", "--detach", "--name", name, "--network", "none", "--cpus", "2",
       "--memory", "2048m", "--memory-swap", "3072m",
       "--mount", f"type=volume,source={volume},target=/source",
       "--mount", r"type=bind,source=C:\Users\alikh\OneDrive\Desktop\projects\ReSense\.git,target=/source.git,readonly",
       "--mount", f"type=bind,source={code},target=/author,readonly",
       "--mount", f"type=bind,source={ROOT / 'docs/evidence/integration_2026-10-16/h4_safety'},target=/review,readonly",
       "--mount", f"type=bind,source={run},target=/out",
       "--mount", "type=volume,source=rs-gate-candidate-f8c088dc4f32-20261016t073403z-4b64ec55-checkout,target=/reference,readonly",
       "--mount", r"type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-p3-data\cache,target=/data/cache,readonly",
       "--mount", r"type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-p3-data\decoded,target=/data/decoded,readonly",
       "--mount", r"type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-p3-data\odometry,target=/data/odometry,readonly",
       "--mount", r"type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs,target=/h3,readonly"]
for k, v in dict(PYTHONPATH="/source/repo", RESENSE_REPO="/source/repo", H4_OUT="/out/results",
                 WITHDRAWAL_HEAD=head, WITHDRAWAL_SEALED="1" if a.sealed else "0", RESENSE_NATIVE="1",
                 RESENSE_REQUIRE_SYNTHETIC="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
                 MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1", PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1").items():
    cmd += ["--env", k + "=" + v]
cmd += ["--entrypoint", "python3", IMAGE, "/author/worker.py", a.task, "--mode", a.mode]
r = subprocess.run(cmd, capture_output=True, text=True)
(run / "launch.json").write_bytes((json.dumps(dict(argv=cmd, stdout=r.stdout, stderr=r.stderr,
                                                  returncode=r.returncode), indent=2) + "\n").encode())
print(r.stdout + r.stderr)
raise SystemExit(r.returncode)
