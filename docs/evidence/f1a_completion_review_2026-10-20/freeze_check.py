#!/usr/bin/env python3
"""Reviewer script (own): independent check of the freeze manifest, without scripts/detector_freeze.py.

1. every file named in the manifest: sha256 of the file in the checkout == manifest value;
2. the 'source_sha256' digest: recomputed with my own reading of the algorithm (sha256 over the sorted
   "path\\0sha\\n" lines is only a guess) is NOT claimed -- instead the same 40 per-file digests are compared with the
   digests recorded by the author's execution record for the candidate (gate-c-candidate-execution.json,
   'source_sha256') and for the reference (gate-c-reference-execution.json);
3. the 'validation' file digest == sha256 of docs/evidence/f1a_completion_2026-10-20/gate-c-candidate.json.

    python freeze_check.py <checkout root>
"""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
m = json.load(open(root / "docs/evidence/detector_freeze_2026-10-20_1.2.0_f1a.json"))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731
bad = []
files = m["files"]
for rel, want in files.items():
    got = sha(root / rel) if (root / rel).is_file() else None
    if got != want:
        # the native .so is generated and not in the repository
        bad.append((rel, want, got))
print("manifest files:", len(files), "mismatches:", len(bad))
for b in bad:
    print("  MISMATCH", b)
ev = root / "docs/evidence/f1a_completion_2026-10-20"
for side in ("candidate", "reference"):
    rec = json.load(open(ev / f"gate-c-{side}-execution.json"))["source_sha256"]
    both = set(rec) & set(files)
    diff = sorted(k for k in both if rec[k] != files[k])
    print(f"execution record ({side}) vs manifest: {len(both)} files in both, differing: {diff};"
          f" only in record: {len(set(rec) - set(files))}, only in manifest: {len(set(files) - set(rec))}")
v = m["validation"]
print("validation file", v["path"], "manifest", v["sha256"][:16], "actual", sha(root / v["path"])[:16],
      "OK" if sha(root / v["path"]) == v["sha256"] else "MISMATCH")
print("source_commit", m["source_commit"], "measured_commit", m["measured_commit"])
