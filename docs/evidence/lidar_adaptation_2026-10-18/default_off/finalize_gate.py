"""Wait for the selected-default gate, revalidate its rows and retain exact bytes."""
from __future__ import annotations

from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
DATA = Path("/home/resense/data")
STATUS = DATA / "default_off_gate_status.json"
SOURCE = DATA / "final_lidar_cecab1b"
WORK = DATA / "final_gate_work_cecab1b"
CONTROL = HERE.parent / "control_9b_native"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def main():
    while (status := read(STATUS))["status"] != "finished":
        time.sleep(20)
    assert status["returncode"] == 0, status
    assert status["source_commit"] == "cecab1b696b8c2e101207601acd8faed96c8bfb8"
    assert read(HERE / "gate.json")["gate"]["passed"] is True
    wrapper = DATA / "run_default_off_gate.py"
    assert sha(wrapper) == status["wrapper_sha256"]
    assert not (HERE / "gate_execution_manifest.json").exists()
    (HERE / "gate_execution_status.json").write_bytes(STATUS.read_bytes())
    (HERE / "gate_console.txt").write_bytes((DATA / "logs/default_off_gate.log").read_bytes())
    with (HERE / "run_default_off_gate.py.gz").open("xb") as target:
        with gzip.GzipFile(filename="", fileobj=target, mode="wb", mtime=0) as stream:
            stream.write(wrapper.read_bytes())
    command = [
        sys.executable, str(HERE.parent / "review_gate_frames.py"),
        "--reference", str(CONTROL / "gate.json"), "--candidate", str(HERE / "gate.json"),
        "--reference-work", str(CONTROL / "work"), "--candidate-work", str(WORK),
        "--reference-source", str(DATA / "control_lidar_9b92df5"),
        "--candidate-source", str(SOURCE), "--cache", str(DATA / "gate_cache"),
        "--out", str(HERE / "gate_independent_review.json"),
    ]
    env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1", "OPENBLAS_CORETYPE": "Haswell"}
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    raw = HERE / "raw"
    raw.mkdir(exist_ok=True)
    paths = [(path, "candidate_work/" + path.name) for path in sorted(WORK.iterdir()) if path.is_file()]
    paths += [(HERE / name, "candidate/" + name) for name in (
        "gate.json", "gate_execution_status.json", "gate_console.txt", "runtime_identity.json",
        "gate_intake_originals.json", "gate_intake_set_o.json", "gate_intake_ride.json", "gate_launch.json",
    )]
    paths += [(wrapper, "producer/run_default_off_gate.py"),
              (Path(__file__), "producer/finalize_gate.py")]
    inputs = raw / "gate_inputs.json"
    write(inputs, [{"source": str(path), "member": member} for path, member in paths])
    subprocess.run([
        sys.executable, str(HERE.parent / "archive_verified.py"), "--inputs", str(inputs),
        "--archive", str(raw / "gate.tar.gz"), "--manifest", str(raw / "gate_manifest.json"),
    ], cwd=ROOT, env=env, check=True)
    names = ("gate.json", "gate_execution_status.json", "gate_console.txt", "run_default_off_gate.py.gz",
             "gate_independent_review.json", "raw/gate_inputs.json", "raw/gate.tar.gz", "raw/gate_manifest.json")
    write(HERE / "gate_execution_manifest.json", {
        "status": "COMPLETED_REVALIDATED_AND_ARCHIVED", "verified_utc": datetime.now(timezone.utc).isoformat(),
        "producer_source_sha256": sha(wrapper), "finalizer_sha256": sha(Path(__file__)),
        "review_command": command, "files": {name: sha(HERE / name) for name in names},
        "control_archive": {"path": str(HERE.parent / "raw/gate_control_and_7b.tar.gz"),
                            "sha256": sha(HERE.parent / "raw/gate_control_and_7b.tar.gz")},
        "scope": "Fresh selected-default source. Earlier same-runtime native control reused unchanged.",
        "timing_scope": "Concurrent replay; wall time and latency are not throughput benchmarks.",
    })


if __name__ == "__main__":
    main()
