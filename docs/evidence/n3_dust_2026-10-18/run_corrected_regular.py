import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/resense/ReSense")
HARNESS = Path("/home/resense/data/dust/harness_b9ad5f4")
SOURCE = Path("/home/resense/data/n2/baseline_9b92df5")
OUT = ROOT / "docs/evidence/n3_dust_2026-10-18"
STATUS = Path("/home/resense/data/dust/corrected_regular_status.json")


def now():
    return datetime.now(timezone.utc).isoformat()


jobs = [
    ("baseline_pose_fixed", []),
    ("dark_baseline_pose_fixed", ["--bags", "doubleT_obstacle", "--dim-labels", "1"]),
    (
        "dark_health_pose_fixed",
        ["--bags", "doubleT_obstacle", "--dim-labels", "1", "--health-only"],
    ),
    (
        "health_platform_pose_fixed",
        [
            "--bags",
            "doubleT_platform",
            "--levels",
            "clean,medium,high",
            "--health-only",
        ],
    ),
]
state = {
    "pid": os.getpid(),
    "pgid": os.getpgrp(),
    "harness_commit": "b9ad5f4",
    "detector_source": "9b92df5",
    "started_utc": now(),
    "jobs": [],
}
env = {
    **os.environ,
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OPENBLAS_CORETYPE": "Haswell",
}
os.nice(5)
for name, extra in jobs:
    cmd = [
        sys.executable,
        str(HARNESS / "scripts/dust_battery.py"),
        "--cache",
        "/home/resense/data/decoded",
        "--out",
        str(OUT / name),
        "--detector-root",
        str(SOURCE),
        *extra,
    ]
    row = {"name": name, "command": cmd, "started_utc": now(), "status": "running"}
    state["jobs"].append(row)
    STATUS.write_text(json.dumps(state, indent=2) + "\n")
    result = subprocess.run(cmd, cwd=HARNESS, env=env)
    row.update(
        returncode=result.returncode,
        finished_utc=now(),
        status="complete" if result.returncode == 0 else "failed",
    )
    STATUS.write_text(json.dumps(state, indent=2) + "\n")
    if result.returncode:
        sys.exit(result.returncode)
state.update(status="complete", finished_utc=now())
STATUS.write_text(json.dumps(state, indent=2) + "\n")
