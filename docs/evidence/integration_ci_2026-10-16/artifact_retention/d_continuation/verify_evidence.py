"""Read-only consistency and optional staged-byte verification of final proof."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    repo = ROOT.parents[4]
    for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
        if args.staged:
            relative = (ROOT / name).relative_to(repo).as_posix()
            blob = subprocess.run(["git", "show", f":{relative}"], cwd=repo,
                                  capture_output=True, check=True).stdout
            assert hashlib.sha256(blob).hexdigest() == expected, f"staged: {name}"
    for name in ("continue_retention.py", "retain_artifacts_base.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"))
    original = load(ROOT.parent / "inventory-before.json")
    final = load(ROOT / "inventory-after.json")
    before_ids = {a["id"] for a in original["artifacts"]}
    after_ids = {a["id"] for a in final["artifacts"]}
    manifest = load(ROOT / "manifest.json")
    records = manifest["records"]
    assert len(records) == 85
    assert before_ids - after_ids == {int(key) for key in records}
    assert sum(r["verification"]["zip_bytes"] for r in records.values()) == 44603273527
    original_records = load(ROOT.parent / "manifest.json")["records"]
    for key in manifest["prior_completed_ids"]:
        assert records[key] == original_records[key], f"prior record changed: {key}"
    proofs = {str(p["id"]): p for p in load(ROOT / "local-final-verification.json")}
    assert set(proofs) == set(records)
    for key, record in records.items():
        artifact, proof = record["artifact"], record["verification"]
        assert record["absence_http_status"] == 404 and record.get("delete_succeeded_at")
        assert proof["verified_at"] < record["delete_requested_at"] < record["delete_succeeded_at"] < record["absence_checked_at"]
        assert artifact["size_in_bytes"] == proof["zip_bytes"] == proofs[key]["zip_bytes"]
        assert artifact["digest"] == "sha256:" + proof["zip_sha256"]
        assert proofs[key]["zip_sha256"] == proof["zip_sha256"]
        assert proofs[key]["embedded_tar_checksums"] == proof["embedded_tar_checksums"]
        assert proofs[key]["api_sha256_match"] and proofs[key]["zip_crc_all_members"]
    assert len(after_ids) == 61 and 11990270962 in after_ids
    assert sum(a["name"].startswith("p1-cold-dry-run-") for a in final["artifacts"]) == 60
    assert load(ROOT / "d-release-before.json") == load(ROOT / "release-after.json")
    assert load(ROOT.parent / "release-before.json") == load(ROOT / "release-after.json")
    summary = load(ROOT / "combined-summary.json")
    assert summary["all_original_85_complete"] and summary["original_c_proof_unchanged"]
    assert summary["d_archive_count"] == 71 and summary["c_archive_count"] == 14
    assert summary["d_archive_bytes"] == 37301919561
    assert not summary["errors"] and not summary["protected_missing_ids"]
    print("PASS: 11 evidence hashes; 85 exact-ID deletions and final ZIP/tar proofs reconcile; prior 14 records unchanged; 60 logs, main image and release assets preserved.")


if __name__ == "__main__":
    main()
