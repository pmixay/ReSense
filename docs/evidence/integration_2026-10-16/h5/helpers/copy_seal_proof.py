#!/usr/bin/env python3
"""Archive a completed Linux seal session into owned H5 evidence; never write the manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent.parent
MEASURED = "52115654417a660669b8dddfce447692c1d782cc"
MANIFEST = "docs/evidence/detector_freeze_2026-10-16_1.1.0.json"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_bytes((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--parent", type=Path, required=True)
parser.add_argument("--run-id", required=True)
args = parser.parse_args()
h5 = args.parent / "docs/evidence/integration_2026-10-16/h5"
assert json.loads((h5 / "RUN.json").read_text())["measured_commit"] == MEASURED
origin = ROOT / args.run_id
done = json.loads((origin / "completion.json").read_text())
assert done["passed"] and done["manifest_measured_commit"] == MEASURED
original_manifest = (origin / "generated_manifest.json").read_bytes()
host_manifest = (args.parent / MANIFEST).read_bytes()
assert original_manifest == host_manifest and sha(host_manifest) == done["manifest_sha256"]
section = "seal_verify" if done["verify_only"] else "seal_create"
destination = h5 / section
destination.mkdir(exist_ok=False)
mapping = json.loads((h5 / "PACKAGE_MAP.json").read_text())
transforms = json.loads((h5 / "PACKAGE_TRANSFORMS.json").read_text())
external = json.loads((h5 / "EXTERNAL_ARTIFACTS.json").read_text())
sources = [(p, destination / (p.stem + ".txt" if p.suffix == ".log" else p.name)) for p in sorted(origin.iterdir()) if p.is_file()]
sources += [(p, destination / ("runtime" + p.name[len(args.run_id):]).replace(".log", ".txt")) for p in sorted(ROOT.glob(args.run_id + ".*")) if p.is_file()]
for source, target in sources:
    data = source.read_bytes()
    compact = data.replace(b"\r\n", b"\n")
    if source.name == "generated_manifest.json":
        assert compact == data, "generated seal must retain exact Linux bytes"
    target.write_bytes(compact)
    rel = target.relative_to(h5).as_posix()
    mode = "byte-identical copy"
    if compact != data:
        mode = "compact text CRLF to LF; external bytes unchanged"
        transforms.append(dict(path=rel, transformation="CRLF to LF only", original_sha256=sha(data), compact_sha256=sha(compact)))
    mapping.append(dict(external_path=source.relative_to(ROOT).as_posix(), package_path=rel, mode=mode))
    external["files"].append(dict(path=source.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data)))
write(destination / "manifest_copy_identity.json", dict(parent_manifest_path=MANIFEST, byte_identical_to_linux_generated=True,
    sha256=sha(host_manifest), bytes=len(host_manifest), manifest_source_commit=done["manifest_source_commit"],
    manifest_measured_commit=done["manifest_measured_commit"], checkout_commit=done["checkout_commit"],
    source_sha256=done["source_sha256"], validation_sha256=done["validation_sha256"], source_session=args.run_id))
for name, value in (("PACKAGE_MAP.json", mapping), ("PACKAGE_TRANSFORMS.json", transforms), ("EXTERNAL_ARTIFACTS.json", external)):
    write(h5 / name, value)
shutil.copyfile(Path(__file__), h5 / "helpers/copy_seal_proof.py")
print(json.dumps(dict(copied_to=str(destination), source_session=args.run_id, manifest_sha256=sha(host_manifest),
    manifest_source_commit=done["manifest_source_commit"], manifest_measured_commit=done["manifest_measured_commit"]), indent=2))
