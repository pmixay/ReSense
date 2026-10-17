"""Read-only exact-ID evidence and staged checksum validation."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    expected, name = line.split("  ", 1)
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    relative = (ROOT / name).relative_to(REPO).as_posix()
    staged = subprocess.run(["git", "show", f":{relative}"], cwd=REPO,
                            capture_output=True, check=True).stdout
    assert hashlib.sha256(staged).hexdigest() == expected
before = {a["id"]: a for a in load("inventory-before.json")["artifacts"]}
after = {a["id"]: a for a in load("inventory-after.json")["artifacts"]}
assert set(before) - set(after) == {11990270962}
assert len(after) == 60 and all(a["name"].startswith("p1-cold-dry-run-") for a in after.values())
assert sum(a["size_in_bytes"] for a in after.values()) == 7059109
records = load("manifest.json")["records"]
assert set(records) == {"11990270962"}
record = records["11990270962"]
proof = record["verification"]
assert proof["verified_at"] < record["delete_requested_at"] < record["delete_succeeded_at"] < record["absence_checked_at"]
assert record["absence_http_status"] == 404
assert proof["api_sha256_match"] and proof["zip_crc_all_members"]
assert proof["zip_bytes"] == 529881425
assert before[11990270962]["digest"] == "sha256:" + proof["zip_sha256"]
final = load("local-final-verification.json")
assert len(final) == 1 and final[0]["zip_sha256"] == proof["zip_sha256"]
assert final[0]["embedded_tar_checksums"] == proof["embedded_tar_checksums"]
assert load("release-before.json") == load("release-after.json")
summary = load("summary.json")
assert summary["cumulative_archived_image_count"] == 86
assert summary["cumulative_archived_image_bytes"] == 45133154952
assert summary["prior_proof_unchanged"] and not summary["errors"]
print("PASS: 11 local/staged hashes; exact-ID deletion/404; ZIP and tar digest proofs; 60 logs / 7,059,109 bytes remain; release unchanged.")
