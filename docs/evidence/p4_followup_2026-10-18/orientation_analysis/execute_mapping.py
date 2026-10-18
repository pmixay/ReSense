"""Detached execution receipt for the registered L16 measurement."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    environment = dict(os.environ)
    environment.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                       OPENBLAS_CORETYPE="Haswell")
    command = ["nice", "-n", "5", sys.executable, str(HERE / "run_mapping.py"), "run"]
    receipt = {"started_utc": datetime.now(timezone.utc).isoformat(), "command": command,
               "pid": os.getpid(), "registration_sha256": sha(HERE / "registration.json"),
               "wrapper_sha256": sha(Path(__file__)), "status": "RUNNING"}
    path = HERE / "execution.json"
    assert not path.exists()
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    with (HERE / "run.log").open("x") as log:
        result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(completed_utc=datetime.now(timezone.utc).isoformat(), returncode=result.returncode,
                   status="COMPLETE" if result.returncode == 0 else "FAILED",
                   log_sha256=sha(HERE / "run.log"))
    if (HERE / "summary.json").exists():
        receipt["summary_sha256"] = sha(HERE / "summary.json")
    path.write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
