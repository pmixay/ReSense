"""Verify and extract the organizer Falcon stream without retaining a duplicate archive."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tarfile
import time
import urllib.request

import zstandard

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
DATA = Path("/home/resense/data")
URL = "https://disk.yandex.ru/d/DK6H3Lxiyi-M-Q"
EXPECTED_SHA = "90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611"
EXPECTED_BYTES = 6758209772


class HashedReader:
    def __init__(self, stream):
        self.stream = stream
        self.sha = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        data = self.stream.read(size)
        self.sha.update(data)
        self.count += len(data)
        return data


def main():
    spec = importlib.util.spec_from_file_location(
        "organizer_unpack", ROOT / "scripts/unpack_dataset.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    href = module.resolve_yadisk(URL)
    started = time.monotonic()
    members = []
    with urllib.request.urlopen(href, timeout=120) as response:
        raw = HashedReader(response)
        with zstandard.ZstdDecompressor().stream_reader(
            raw, read_across_frames=True, closefd=False
        ) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    relative = Path(member.name.removeprefix("./"))
                    destination = (DATA / "raw" / relative).resolve()
                    if not destination.is_relative_to((DATA / "raw").resolve()):
                        raise ValueError("unsafe archive path")
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    if destination.exists():
                        raise FileExistsError(destination)
                    digest = hashlib.sha256()
                    total = 0
                    with (
                        archive.extractfile(member) as source,
                        destination.open("xb") as target,
                    ):
                        while block := source.read(8 << 20):
                            if shutil.disk_usage(DATA).free < 512 << 20:
                                raise OSError(
                                    "less than 512 MiB free: extraction stopped before exhausting disk"
                                )
                            target.write(block)
                            digest.update(block)
                            total += len(block)
                            if total % (1 << 30) < len(block):
                                print(
                                    f"{relative.name}: {total / 1e9:.2f} GB extracted; "
                                    f"disk free {shutil.disk_usage(DATA).free / 1e9:.2f} GB",
                                    flush=True,
                                )
                    if total != member.size:
                        raise ValueError("short archive member")
                    members.append(
                        {
                            "name": str(relative),
                            "bytes": total,
                            "sha256": digest.hexdigest(),
                        }
                    )
            while reader.read(8 << 20):
                pass
        while raw.read(8 << 20):
            pass
    verified = raw.count == EXPECTED_BYTES and raw.sha.hexdigest() == EXPECTED_SHA
    receipt = {
        "source": URL,
        "archive": "falcon_test.zst",
        "bytes": raw.count,
        "sha256": raw.sha.hexdigest(),
        "verified": verified,
        "retained_compressed_archive": False,
        "members": members,
        "elapsed_s": time.monotonic() - started,
        "free_bytes_after_extraction": shutil.disk_usage(DATA).free,
    }
    (EVIDENCE / "source_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if not verified:
        raise ValueError(
            "organizer archive hash/size mismatch; extracted data must not be used"
        )
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
