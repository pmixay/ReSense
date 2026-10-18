#!/usr/bin/env python3
"""Recreate byte-identical historical X3 cache ZIPs and relocate verified raw evidence.

Only ZIP version/size headers change. Every output must match the archived whole-file
SHA-256 before it is written; point arrays and compressed data are never modified.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import shutil
import struct
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHIVED = ROOT / "docs/evidence/p4_eval_1.1.0_2026-10-16"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def old_zip_headers(path):
    """Emulate Python 3.10's force_zip64 header convention, retaining compressed bytes."""
    data = bytearray(path.read_bytes())
    with zipfile.ZipFile(path) as archive:
        central = archive.start_dir
        for info in archive.infolist():
            if data[central:central + 4] != b"PK\x01\x02":
                raise ValueError("invalid central directory")
            data[central + 4] = 20
            data[central + 5] = 3
            data[central + 6] = 20
            local = info.header_offset
            if data[local:local + 4] != b"PK\x03\x04":
                raise ValueError("invalid local header")
            data[local + 4] = 20
            struct.pack_into("<II", data, local + 18, info.compress_size, info.file_size)
            central += 46 + len(info.filename.encode()) + len(info.extra) + len(info.comment)
    return bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    reference_path = ARCHIVED / "battery_1.1.0_linux_haswell.json"
    reference = json.loads(reference_path.read_text())
    portable = copy.deepcopy(reference)
    receipt = {"method": __doc__, "original_reference_sha256": digest(reference_path.read_bytes()),
               "script_sha256": digest(Path(__file__).read_bytes()), "bags": {}, "status": "RUNNING"}
    receipt_path = args.out / "preparation.json"
    try:
        for bag, expected in reference["sources"].items():
            source, target = args.cache / bag, args.out / "cache" / bag
            target.mkdir(parents=True)
            meta = (source / "meta.json").read_bytes()
            if digest(meta) != expected["meta_sha256"]:
                raise ValueError(f"metadata mismatch: {bag}")
            (target / "meta.json").write_bytes(meta)
            inventory = []
            for item in expected["files"]:
                if shutil.disk_usage(args.out).free < 4 * 1024**3:
                    raise ValueError("less than 4 GiB free; preserve intake reserve")
                path = source / item["name"]
                data = old_zip_headers(path)
                actual = {"name": path.name, "bytes": len(data), "sha256": digest(data)}
                if actual != item:
                    raise ValueError(f"historical ZIP reconstruction mismatch: {bag}/{path.name}")
                (target / path.name).write_bytes(data)
                inventory.append(actual)
            payload = digest(json.dumps(inventory, sort_keys=True).encode())
            if payload != expected["payload_sha256"]:
                raise ValueError(f"inventory mismatch: {bag}")
            receipt["bags"][bag] = {"frames": len(inventory), "payload_sha256": payload,
                                     "meta_sha256": digest(meta), "all_files_exact": True}
            print(bag, len(inventory), "exact archived hashes", flush=True)

        archive_path = ARCHIVED / "raw/p4_raw_2026-10-16.tar.xz"
        expected_archive = (ARCHIVED / "raw/SHA256SUMS").read_text().split()[0]
        if digest(archive_path.read_bytes()) != expected_archive:
            raise ValueError("raw archive checksum mismatch")
        with tarfile.open(archive_path) as archive:
            for entry in portable["entries"].values():
                relative = Path(entry["raw_path"]).relative_to("/home/user/rs-data")
                for name in (relative, relative.with_suffix(".complete.json")):
                    member = archive.getmember(str(name))
                    if not member.isfile():
                        raise ValueError("raw archive member is not a regular file")
                    data = archive.extractfile(member).read()
                    target = args.out / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    if name == relative and digest(data) != entry["raw_sha256"]:
                        raise ValueError(f"raw hash mismatch: {name}")
                entry["raw_path"] = str((args.out / relative).resolve())
        portable_path = args.out / "reference.json"
        portable_path.write_text(json.dumps(portable, indent=2) + "\n")
        spec = importlib.util.spec_from_file_location("x3_driver", ROOT / "scripts/robustness_battery.py")
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        driver.validated_entries(portable, args.out / "cache", ROOT)
        receipt.update(status="PASS", raw_entries_revalidated=len(portable["entries"]),
                       portable_reference_sha256=digest(portable_path.read_bytes()),
                       relocated_fields="entries.*.raw_path only; all source/evaluation identities preserved",
                       raw_archive_sha256=expected_archive)
    except Exception as error:
        receipt.update(status="FAIL", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(receipt["status"], receipt_path, flush=True)


if __name__ == "__main__":
    main()
