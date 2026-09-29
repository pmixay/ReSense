"""Run the preregistered low-ray full gate with exact before/after identities."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

from resense import _native
from resense.config import DetectorConfig
from scripts.detector_freeze import source_digest, source_hashes


ROOT = Path(__file__).resolve().parents[4]
PROTOCOL = ROOT / "docs/evidence/low_return_support/full_gate/protocol.json"
OUT = Path("/cycle/low_return_support/full_gate")
BASELINE = ROOT / "docs/evidence/cycle_2026-09-28/complete_timing/default/gate.json"
OBSERVER_FILES = (
    "scripts/regression_gate.py",
    "scripts/eval_real.py",
    "scripts/far_range_eval.py",
    "scripts/score_fake_objects.py",
    "scripts/cache_io.py",
    "scripts/detector_freeze.py",
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(*args):
    return subprocess.check_output(
        ["git", "-c", f"safe.directory={ROOT}", *args], cwd=ROOT, text=True
    ).strip()


def identity():
    files = source_hashes(ROOT)
    config = DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")).to_dict()
    config_sha = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    native_path = Path(_native.LIBRARY) if _native.LIBRARY else None
    return {
        "commit": git("rev-parse", "HEAD"),
        "dirty": git("status", "--porcelain"),
        "source_sha256": source_digest(files),
        "source_files": files,
        "config_sha256": config_sha,
        "native_path": str(native_path) if native_path else None,
        "native_sha256": sha256(native_path) if native_path else None,
        "baseline_sha256": sha256(BASELINE),
        "protocol_sha256": sha256(PROTOCOL),
        "observer_files": {name: sha256(ROOT / name) for name in OBSERVER_FILES},
    }


def main():
    protocol = json.loads(PROTOCOL.read_text())
    before = identity()
    assert not before["dirty"], "refusing to run from a dirty worktree"
    assert before["source_sha256"] == protocol["candidate"]["source_sha256"]
    assert before["config_sha256"] == protocol["candidate"]["effective_config_sha256"]
    assert before["native_sha256"] == protocol["candidate"]["native_sha256"]
    assert before["baseline_sha256"] == protocol["full_gate_baseline"]["sha256"]
    OUT.mkdir(parents=True, exist_ok=True)
    assert not (OUT / "identity_pre.json").exists(), "refusing to overwrite an earlier run"
    (OUT / "identity_pre.json").write_text(json.dumps(before, indent=2) + "\n")
    started = time.time()
    command = protocol["command"]
    with (OUT / "gate.txt").open("w") as stream:
        result = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    after = identity()
    stable = (
        not after["dirty"]
        and after["commit"] == before["commit"]
        and after["source_sha256"] == before["source_sha256"]
        and after["config_sha256"] == before["config_sha256"]
        and after["native_sha256"] == before["native_sha256"]
        and after["observer_files"] == before["observer_files"]
    )
    completion = {
        "exit_code": result.returncode,
        "identity_stable": stable,
        "elapsed_s": round(time.time() - started, 1),
        "finished_unix": time.time(),
        "identity_post": after,
    }
    (OUT / "completion.json").write_text(json.dumps(completion, indent=2) + "\n")
    print(json.dumps({"exit_code": result.returncode, "identity_stable": stable}), flush=True)
    raise SystemExit(result.returncode or (0 if stable else 91))


if __name__ == "__main__":
    main()
