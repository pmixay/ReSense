"""Pack explicitly selected completed evidence and verify every archived member.

The input is a JSON list of {source: absolute/local path, member: portable path}.
It must be assembled only after its producer has finished. Source files are kept.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile


def digest(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(chunk)
    return value.hexdigest()


def sha(path):
    with path.open("rb") as stream:
        return digest(stream)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if args.archive.exists() or args.manifest.exists():
        raise ValueError("refusing to replace evidence")
    entries = json.loads(args.inputs.read_text())
    members = set()
    for entry in entries:
        path, member = Path(entry["source"]), PurePosixPath(entry["member"])
        if (member.is_absolute() or not member.parts or ".." in member.parts
                or str(member) in members or not path.is_file() or path.is_symlink()):
            raise ValueError(f"invalid or duplicate source/member: {entry}")
        members.add(str(member))
        entry.update(source=str(path.resolve()), member=str(member), bytes=path.stat().st_size,
                     sha256=sha(path))
    if not entries:
        raise ValueError("no completed evidence selected")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    with args.archive.open("xb") as output:
        with gzip.GzipFile(filename="", fileobj=output, mode="wb", mtime=0, compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed, mode="w|") as archive:
                for entry in sorted(entries, key=lambda e: e["member"]):
                    info = tarfile.TarInfo(entry["member"])
                    info.size, info.mode, info.mtime = entry["bytes"], 0o644, 0
                    with Path(entry["source"]).open("rb") as source:
                        archive.addfile(info, source)
    expected = {entry["member"]: entry for entry in entries}
    verified = set()
    with tarfile.open(args.archive, "r:gz") as archive:
        for info in archive:
            if not info.isfile() or info.name not in expected or info.name in verified:
                raise ValueError("unexpected or duplicate archive member")
            entry = expected[info.name]
            with archive.extractfile(info) as source:
                actual = digest(source)
            if actual != entry["sha256"] or info.size != entry["bytes"]:
                raise ValueError(f"archived bytes differ: {info.name}")
            verified.add(info.name)
    if verified != members:
        raise ValueError("archive member set differs")
    for entry in entries:
        path = Path(entry["source"])
        if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"]:
            raise ValueError(f"source changed during packing: {path}")
    receipt = {"status": "ALL_MEMBERS_AND_RETAINED_ORIGINALS_VERIFIED",
               "verified_utc": datetime.now(timezone.utc).isoformat(),
               "archive": args.archive.name, "archive_bytes": args.archive.stat().st_size,
               "archive_sha256": sha(args.archive), "member_count": len(entries),
               "uncompressed_bytes": sum(entry["bytes"] for entry in entries),
               "input_list_sha256": sha(args.inputs), "archiver_sha256": sha(Path(__file__)),
               "members": sorted(entries, key=lambda e: e["member"])}
    args.manifest.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: value for key, value in receipt.items() if key != "members"}))


if __name__ == "__main__":
    main()
