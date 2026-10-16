"""One-shot raw-byte proof of the authorized archival move, against the original Git blob."""
import hashlib
import json
from pathlib import Path
import subprocess

P = Path(__file__).resolve().parent
ROOT = P.parents[5]
OLD = "4c6ea250f85192bbf252c0c6058a1dedac98b5a0"
SOURCE = "tests/test_h4_column_evidence.py"
DEST = "docs/evidence/integration_2026-10-16/h4_fixes/columns/withdrawn_acceptance.py.txt"
original = subprocess.check_output(["git", "show", OLD + ":" + SOURCE], cwd=ROOT)
archived = (ROOT / DEST).read_bytes()
assert original == archived, "withdrawn acceptance criteria must be preserved byte-for-byte"
blob = subprocess.check_output(["git", "rev-parse", OLD + ":" + SOURCE], cwd=ROOT, text=True).strip()
actual_blob = subprocess.check_output(["git", "hash-object", "--no-filters", "--", DEST], cwd=ROOT, text=True).strip()
assert blob == actual_blob
result = dict(original_commit=OLD, original_path=SOURCE, archived_path=DEST,
              byte_exact=True, bytes=len(original), git_blob=blob, archived_git_blob=actual_blob,
              sha256=hashlib.sha256(original).hexdigest(),
              reason="Withdrawn feature's unmet acceptance criteria; not a passing shipping test or waiver.")
out = P / "withdrawn_test_byte_proof.json"
assert not out.exists()
out.write_bytes((json.dumps(result, indent=2) + "\n").encode())
print(json.dumps(result, indent=2))
