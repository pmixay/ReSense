#!/usr/bin/env python3
"""Normalize only owned compact text evidence to LF and record exact transformations."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", type=Path, required=True)
parser.add_argument("--folder", choices=("h3", "h3_withdrawn", "h3_selected", "h5"), default="h3")
parser.add_argument("--commit", default="f8c088dc4f3243fbd15a3aae9be0459e8a0aa941")
args = parser.parse_args()
destination = args.parent / "docs/evidence/integration_2026-10-16" / args.folder
assert json.loads((destination / "RUN.json").read_text())["measured_commit"] == args.commit
transforms = []
for p in sorted(destination.rglob("*")):
    if p.is_file() and p.name != "HASHES.json":
        data = p.read_bytes()
        if b"\r\n" in data:
            assert p.suffix in (".json", ".md", ".txt", ".py", ".yaml", ".patch")
            new = data.replace(b"\r\n", b"\n")
            p.write_bytes(new)
            transforms.append(dict(path=p.relative_to(destination).as_posix(),
                transformation="CRLF to LF only", original_sha256=hashlib.sha256(data).hexdigest(), compact_sha256=hashlib.sha256(new).hexdigest()))
mapping = json.loads((destination / "PACKAGE_MAP.json").read_text())
normalized = {entry["path"] for entry in transforms}
for entry in mapping:
    if entry["package_path"] in normalized:
        entry["mode"] = "text copy normalized CRLF to LF; original external bytes retained and indexed"
(destination / "PACKAGE_MAP.json").write_bytes((json.dumps(mapping, indent=2, sort_keys=True) + "\n").encode())
(destination / "PACKAGE_TRANSFORMS.json").write_bytes((json.dumps(transforms, indent=2, sort_keys=True) + "\n").encode())
for name in ("normalize_h3_package.py", "verify_h3_package.py"):
    shutil.copyfile(Path(__file__).parent / name, destination / "helpers" / name)
print(json.dumps(dict(normalized_files=transforms, source_or_raw_evidence_modified=False), indent=2))
