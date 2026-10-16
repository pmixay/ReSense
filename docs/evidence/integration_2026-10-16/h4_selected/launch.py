"""Launch only this review's focused checks, never the full integration gate."""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
IMAGE = "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
NAME = "rs-h4-selected-independent-c9aea87-01"
VOLUME = NAME + "-source"
OUT = HERE / "run-001"
OUT.mkdir(exist_ok=False)
subprocess.run(["docker", "volume", "create", VOLUME], check=True, capture_output=True)
cmd = ["docker", "run", "--detach", "--name", NAME, "--network", "none", "--cpus", "2",
       "--memory", "2048m", "--mount", f"type=volume,source={VOLUME},target=/work",
       "--mount", r"type=bind,source=C:\Users\alikh\OneDrive\Desktop\projects\ReSense\.git,target=/source.git,readonly",
       "--mount", f"type=bind,source={HERE},target=/review", "--entrypoint", "python3"]
for k, v in dict(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                 NUMEXPR_NUM_THREADS="1", PYTHONHASHSEED="0", RESENSE_NATIVE="1",
                 RESENSE_REQUIRE_SYNTHETIC="1", PYTHONDONTWRITEBYTECODE="1").items():
    cmd += ["--env", k + "=" + v]
cmd += [IMAGE, "/review/worker.py"]
r = subprocess.run(cmd, capture_output=True, text=True)
(OUT / "launch.json").write_text(json.dumps(dict(argv=cmd, stdout=r.stdout, stderr=r.stderr,
                                               returncode=r.returncode), indent=2) + "\n", encoding="utf-8")
print(r.stdout + r.stderr)
raise SystemExit(r.returncode)
