#!/usr/bin/env python3
"""Record the compact compiler-banner EOF formatting; preserve original stdout."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", type=Path, required=True)
args = parser.parse_args()
folder = args.parent / "docs/evidence/integration_2026-10-16/h3_selected"
run = json.loads((folder / "RUN.json").read_text())
assert run["measured_commit"] == "c9aea87cb5322092070158cd8987115ee44833c9"
mapping = json.loads((folder / "PACKAGE_MAP.json").read_text())
transforms = json.loads((folder / "PACKAGE_TRANSFORMS.json").read_text())
for name in ("baseline/compiler.txt", "candidate/compiler.txt"):
    entry = next(row for row in mapping if row["package_path"] == name)
    original = (Path(run["external_root"]) / entry["external_path"]).read_bytes()
    compact = (folder / name).read_bytes()
    assert original.endswith(b"\n\n") and compact == original[:-1]
    entry["mode"] = "compiler stdout text with final empty banner line removed; complete external bytes retained and indexed"
    transforms.append(dict(path=name, transformation="remove one terminal empty compiler-banner line only",
        original_sha256=hashlib.sha256(original).hexdigest(), compact_sha256=hashlib.sha256(compact).hexdigest()))
for name, value in (("PACKAGE_MAP.json", mapping), ("PACKAGE_TRANSFORMS.json", transforms)):
    (folder / name).write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())
shutil.copyfile(Path(__file__), folder / "helpers/record_selected_banner_format.py")
print("Recorded compact compiler-banner formatting; both complete original stdout files remain external.")
