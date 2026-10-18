"""Measure all actual Falcon inputs on the committed opt-in-only detector default."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from detector_freeze import source_digest, source_hashes  # noqa: E402

SOURCE = Path("/home/resense/data/final_lidar_cecab1b")
COMMIT = "cecab1b696b8c2e101207601acd8faed96c8bfb8"
CACHE = Path("/home/resense/data/decoded/falcon_test_second_dark")
HERE = Path(__file__).resolve().parent
OUT = HERE / "falcon_default_off"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def main():
    import yaml

    assert subprocess.check_output(["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip() == COMMIT
    config = yaml.safe_load((SOURCE / "configs/default.yaml").read_text())["resense"]
    assert config["calibration"]["orientation_replay_frames"] == 0
    metadata = json.loads((CACHE / "meta.json").read_text())
    assert len(metadata) == 4443
    if (OUT / "summary.json").exists() or (OUT / "baseline.jsonl").exists():
        raise FileExistsError("Never overwrite an earlier measurement")
    OUT.mkdir(exist_ok=True)
    harness = HERE / "replay_inputs.py"
    sources = source_hashes(SOURCE)
    binaries = {str(path.relative_to(SOURCE)): sha(path)
                for path in (SOURCE / "resense").glob("*_native*.so")}
    assert list(binaries.values()) == ["511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8"]
    command = ["/home/resense/.venv/bin/python", str(harness), "--source", str(SOURCE),
               "--cache", str(CACHE), "--suite", "baseline", "--out", str(OUT)]
    receipt = {"status": "RUNNING", "started_utc": utc(), "pid": os.getpid(),
               "process_group": os.getpgrp(), "command": command, "source_commit": COMMIT,
               "source": str(SOURCE), "source_files": sources, "source_sha256": source_digest(sources),
               "native_files": binaries, "harness_sha256": sha(harness),
               "wrapper_sha256": sha(Path(__file__)), "input_meta_sha256": sha(CACHE / "meta.json"),
               "expected_frames": 4443, "default_replay_frames": 0,
               "config_overrides": [], "timing_scope": "Shared one-CPU host; informational only."}
    path = OUT / "execution.json"

    def save():
        path.write_text(json.dumps(receipt, indent=2) + "\n")

    save()
    env = {**os.environ, "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
           "MKL_NUM_THREADS": "1", "OPENBLAS_CORETYPE": "Haswell", "PYTHONPATH": str(SOURCE)}
    with (OUT / "run.log").open("w") as log:
        result = subprocess.run(command, cwd=SOURCE, env=env, stdout=log, stderr=subprocess.STDOUT)
    receipt.update(returncode=result.returncode, finished_utc=utc(),
                   source_unchanged=source_hashes(SOURCE) == sources,
                   harness_unchanged=sha(harness) == receipt["harness_sha256"],
                   run_log_sha256=sha(OUT / "run.log"))
    if result.returncode == 0:
        summary = json.loads((OUT / "summary.json").read_text())
        assert len(summary["cases"]) == 1 and summary["cases"][0]["frames"] == 4443
        assert summary["cases"][0]["overrides"] == {}
        receipt.update(summary_sha256=sha(OUT / "summary.json"), raw_sha256=sha(OUT / "baseline.jsonl"))
    receipt["status"] = "COMPLETE" if (result.returncode == 0 and receipt["source_unchanged"]
                                        and receipt["harness_unchanged"]) else "FAILED"
    save()
    print(json.dumps({key: receipt[key] for key in ("status", "returncode", "source_commit", "expected_frames")}))
    if receipt["status"] != "COMPLETE":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
