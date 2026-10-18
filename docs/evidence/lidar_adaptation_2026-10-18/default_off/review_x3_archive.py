"""Read-only independent producer and durable-byte review of selected-default X3."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
COMMIT = "cecab1b696b8c2e101207601acd8faed96c8bfb8"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    identity = read(HERE / "runtime_identity.json")
    receipt = read(HERE / "x3_execution.json")
    producer = receipt["producer_status"]
    source = Path(identity["source_root"])
    assert producer["status"] == "finished" and producer["returncode"] == 0
    assert producer["source_commit"] == identity["source_commit"] == COMMIT
    assert producer["source_unchanged"] and producer["native_unchanged"]
    assert producer["source_files"] == identity["files"] and len(producer["source_files"]) == 38
    assert producer["native_libraries"] == {"resense/" + k: v for k, v in identity["native_files"].items()}
    assert producer["preflight"] == {"native": True, "replay_default": 0}
    assert producer["command"] == [
        "/home/resense/.venv/bin/python", str(source / "scripts/robustness_battery.py"),
        "--repo", str(source), "--cache", "/home/resense/data/x3_reference/cache",
        "--reference", "/home/resense/data/x3_reference/reference.json",
        "--out", str(HERE / "x3.json"), "-j", "1"]
    assert sha(HERE / "runtime_identity.json") == receipt["source_identity_sha256"]
    assert sha(HERE / "x3.json") == receipt["report_sha256"] == producer["report_sha256"]
    assert sha(HERE / "x3_independent_review.json") == receipt["review_sha256"]
    artifacts = {row["member"]: row for row in receipt["artifact_members"]}
    assert artifacts["x3/run/wrapper.py"]["sha256"] == producer["wrapper_sha256"]
    assert read(Path(artifacts["x3/run/status.json"]["source"])) == producer

    manifest = read(HERE / "raw/x3_manifest.json")
    archive_path = HERE / "raw/x3.tar.gz"
    assert sha(archive_path) == manifest["archive_sha256"]
    expected = {row["member"]: row for row in manifest["members"]}
    report = read(HERE / "x3.json")
    required = {f"x3/{case}/{name}" for case in report["entries"]
                for name in ("job.json", "probe.complete.json", "probe.jsonl", "process.log")}
    required |= set(artifacts) | {"x3.json", "x3_execution.json", "x3_independent_review.json"}
    assert set(expected) == required and len(required) == manifest["member_count"] == 167
    assert all(expected[name] == row for name, row in artifacts.items())
    seen = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for info in archive:
            assert info.isfile() and info.name in expected and info.name not in seen
            row = expected[info.name]
            with archive.extractfile(info) as stream:
                assert hashlib.sha256(stream.read()).hexdigest() == row["sha256"]
            assert info.size == row["bytes"] and sha(Path(row["source"])) == row["sha256"]
            seen.add(info.name)
    assert seen == required
    inputs = [Path(__file__), HERE / "runtime_identity.json", HERE / "x3_execution.json",
              HERE / "x3.json", HERE / "x3_independent_review.json", HERE / "raw/x3_manifest.json", archive_path]
    result = {"status": "PRODUCER_AND_ALL167_ARCHIVED_AND_RETAINED_MEMBERS_VERIFIED",
              "checked_utc": datetime.now(timezone.utc).isoformat(), "source_commit": COMMIT,
              "producer_exit": 0, "source_files": 38, "default_replay_frames": 0,
              "no_configuration_overrides": True, "cases": len(report["entries"]),
              "verified_members": len(seen), "archive_sha256": manifest["archive_sha256"],
              "input_sha256": {str(path): sha(path) for path in inputs},
              "limit": "Original archived Linux reference; unavailable historical Windows SetO frame332 is not reconstructed."}
    (HERE / "independent_x3_archive.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "source_commit", "verified_members")}))


if __name__ == "__main__":
    main()
