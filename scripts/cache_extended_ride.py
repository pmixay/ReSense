#!/usr/bin/env python3
"""Stream and cache the organizer's 20-minute ride without unpacking its 90 GB rosbag.

The archive is read once from the published Yandex Disk link. At most one ~408 MB DB3 split is
spooled at a time; each split becomes 51 atomic ``.npy.zst`` compact16 frames plus its timestamp
manifest. The archive size and SHA-256 published by Yandex are verified before a complete intake
manifest is written. Existing complete splits are validated and reused on a resumed run.

    python scripts/cache_extended_ride.py --cache /data/cache/new_data \\
        --spool /data/.resense_new_data_spool --reserve-gib 3
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for _path in (str(ROOT), str(HERE)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from scripts.cache_frames import _atomic_json, cache_bag  # noqa: E402
from scripts.cache_io import validate_extended_ride_cache  # noqa: E402

YADISK_API = "https://cloud-api.yandex.net/v1/disk/public/resources"
PUBLIC_URL = "https://disk.yandex.ru/d/N8IUpAyd7jyvow"
ARCHIVE_NAME = "new_data.zst"
SPLIT_RE = re.compile(r"(?:^|/)new_data_(\d+)\.db3$")
EXPECTED_SPLITS = 221
FRAMES_PER_SPLIT = 51


def resolve_yadisk_asset(public_url: str = PUBLIC_URL, member: str = ARCHIVE_NAME,
                         urlopen=urllib.request.urlopen) -> dict:
    """Resolve a public folder item and return its published size, checksum and download URL."""
    resource_url = f"{YADISK_API}?public_key={urllib.parse.quote(public_url, safe='')}"
    with urlopen(resource_url, timeout=60) as response:
        resource = json.load(response)
    if resource.get("type") == "dir":
        files = [item for item in resource.get("_embedded", {}).get("items", [])
                 if item.get("type") == "file" and item.get("name") == member]
        if len(files) != 1:
            raise RuntimeError(f"expected exactly one {member} in organizer folder")
        item = files[0]
        path = item.get("path")
    else:
        if resource.get("name") != member:
            raise RuntimeError(f"Yandex link names {resource.get('name')!r}, expected {member}")
        item = resource
        path = item.get("path")
    query = {"public_key": public_url}
    if path:
        query["path"] = path
    download_url = f"{YADISK_API}/download?{urllib.parse.urlencode(query)}"
    with urlopen(download_url, timeout=60) as response:
        href = json.load(response)["href"]
    return {"name": member, "size": int(item["size"]), "sha256": item.get("sha256"),
            "modified": item.get("modified"), "download_url": href}


class HashingReader:
    """File-like download wrapper that hashes every compressed archive byte as it is read."""

    def __init__(self, raw):
        self.raw = raw
        self.digest = hashlib.sha256()
        self.bytes_read = 0

    def read(self, size=-1):
        data = self.raw.read(size)
        self.digest.update(data)
        self.bytes_read += len(data)
        return data

    def drain(self, block_size=1024 * 1024):
        while self.read(block_size):
            pass


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    temp = path.with_name(f".{path.name}.tmp")
    try:
        with open(temp, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _same_device(first: Path, second: Path) -> bool:
    return os.stat(first).st_dev == os.stat(second).st_dev


def _require_space(cache: Path, spool: Path, reserve_bytes: int, split_bytes: int,
                   projected_cache_bytes: int) -> None:
    cache_free = shutil.disk_usage(cache).free
    spool_free = shutil.disk_usage(spool).free
    if _same_device(cache, spool):
        required = reserve_bytes + split_bytes + projected_cache_bytes
        if min(cache_free, spool_free) < required:
            raise RuntimeError(f"disk headroom guard: need {required / 1e9:.2f} GB free before a split; "
                               f"have {min(cache_free, spool_free) / 1e9:.2f} GB")
    else:
        if cache_free < reserve_bytes + projected_cache_bytes:
            raise RuntimeError(f"cache filesystem headroom guard: need "
                               f"{(reserve_bytes + projected_cache_bytes) / 1e9:.2f} GB; "
                               f"have {cache_free / 1e9:.2f} GB")
        if spool_free < reserve_bytes + split_bytes:
            raise RuntimeError(f"spool filesystem headroom guard: need "
                               f"{(reserve_bytes + split_bytes) / 1e9:.2f} GB; "
                               f"have {spool_free / 1e9:.2f} GB")


def _split_complete(cache: Path, split: int) -> bool:
    try:
        validate_extended_ride_cache(str(cache), expected_splits=[split],
                                     frames_per_split=FRAMES_PER_SPLIT, load_arrays=True)
    except Exception:
        return False
    return True


def _store_metadata(tar: tarfile.TarFile, member: tarfile.TarInfo, cache: Path) -> str:
    src = tar.extractfile(member)
    if src is None:
        raise RuntimeError(f"cannot read archive member {member.name}")
    payload = src.read()
    _atomic_write_bytes(cache / "metadata.yaml", payload)
    return hashlib.sha256(payload).hexdigest()


def stream_cache(cache_dir: str, spool_dir: str, reserve_gib: float = 3.0,
                 public_url: str = PUBLIC_URL, only_splits=None, opener=urllib.request.urlopen) -> dict:
    """Stream source into per-split caches and return a verified compact intake report.

    ``only_splits`` is for controlled local diagnosis. It still drains and checks the complete
    archive but intentionally does not write a full-recording intake manifest.
    """
    try:
        import zstandard
    except ImportError as exc:
        raise RuntimeError("cache_extended_ride.py requires the zstandard package") from exc
    cache = Path(cache_dir).resolve()
    spool = Path(spool_dir).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    spool.mkdir(parents=True, exist_ok=True)
    if cache == spool or cache in spool.parents or spool in cache.parents:
        raise ValueError("cache and spool must be separate directories")
    if reserve_gib < 3.0:
        raise ValueError("reserve-gib must be at least 3")
    reserve_bytes = int(reserve_gib * 1e9)
    selected = None if only_splits is None else {int(n) for n in only_splits}
    if selected is not None and (not selected or min(selected) < 0 or max(selected) >= EXPECTED_SPLITS):
        raise ValueError(f"split ids must be in 0..{EXPECTED_SPLITS - 1}")

    source = resolve_yadisk_asset(public_url=public_url, urlopen=opener)
    print(f"source: {source['name']} {source['size']} bytes sha256={source.get('sha256')}", flush=True)
    intake_path = cache / "intake_manifest.json"
    if selected is None and not intake_path.exists():
        print("full cache manifest absent; resuming only individually validated splits", flush=True)
    elif selected is None:
        print("existing full intake manifest found; verifying source and cached frame contents", flush=True)

    response = opener(source["download_url"], timeout=180)
    hashed = HashingReader(response)
    written_splits, reused_splits, seen_splits = set(), set(), set()
    metadata_sha = None
    output_bytes = 0
    started = time.monotonic()
    splitter = zstandard.ZstdDecompressor().stream_reader(hashed, read_across_frames=True, closefd=False)
    try:
        with tarfile.open(fileobj=splitter, mode="r|") as archive:
            for member in archive:
                normalized = member.name.removeprefix("./")
                if normalized.endswith("/metadata.yaml") and member.isfile():
                    metadata_sha = _store_metadata(archive, member, cache)
                    continue
                match = SPLIT_RE.search(normalized)
                if not match or not member.isfile():
                    continue
                split = int(match.group(1))
                if split >= EXPECTED_SPLITS or split in seen_splits:
                    raise RuntimeError(f"unexpected or duplicate archive split {member.name}")
                seen_splits.add(split)
                if selected is not None and split not in selected:
                    continue
                if _split_complete(cache, split):
                    reused_splits.add(split)
                    continue

                projected_cache = max(64 * 1024 * 1024, int(output_bytes / max(len(written_splits), 1) * 2))
                _require_space(cache, spool, reserve_bytes, int(member.size), projected_cache)
                spool_file = spool / f"new_data_{split}.db3"
                if spool_file.exists():
                    spool_file.unlink()  # task-owned partial from an interrupted prior invocation
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise RuntimeError(f"cannot read archive member {member.name}")
                copied = 0
                try:
                    with open(spool_file, "wb") as raw:
                        while True:
                            block = extracted.read(4 * 1024 * 1024)
                            if not block:
                                break
                            raw.write(block)
                            copied += len(block)
                        raw.flush()
                        os.fsync(raw.fileno())
                    if copied != member.size:
                        raise RuntimeError(f"truncated {member.name}: expected {member.size}, got {copied}")
                    name, count = cache_bag(str(spool_file), str(cache), every=1, int16=True,
                                            stamps=True, zstd_level=3)
                    if name != f"new_data_{split}" or count != FRAMES_PER_SPLIT:
                        raise RuntimeError(f"{member.name}: expected 51 cached frames, got {name}/{count}")
                    validation = validate_extended_ride_cache(
                        str(cache), expected_splits=[split], frames_per_split=FRAMES_PER_SPLIT,
                        load_arrays=True)
                    output_bytes += validation["compressed_bytes"]
                    written_splits.add(split)
                    print(f"cached split {split:03d}: {count} frames, "
                          f"{validation['compressed_bytes'] / 1e6:.1f} MB; "
                          f"{len(written_splits)} new / {len(reused_splits)} reused; "
                          f"{time.monotonic() - started:.0f} s", flush=True)
                finally:
                    if spool_file.exists():
                        spool_file.unlink()

                free_after = min(shutil.disk_usage(cache).free, shutil.disk_usage(spool).free)
                if free_after < reserve_bytes:
                    raise RuntimeError(f"stopping: only {free_after / 1e9:.2f} GB free; "
                                       f"the required {reserve_gib:.1f} GB reserve would be violated")
        splitter.close()
        hashed.drain()
    finally:
        splitter.close()
        response.close()

    actual_sha = hashed.digest.hexdigest()
    if hashed.bytes_read != source["size"]:
        raise RuntimeError(f"archive size mismatch: Yandex says {source['size']}, read {hashed.bytes_read}")
    expected_sha = source.get("sha256")
    if expected_sha and actual_sha.lower() != expected_sha.lower():
        raise RuntimeError(f"archive SHA-256 mismatch: Yandex says {expected_sha}, got {actual_sha}")
    expected_ids = set(range(EXPECTED_SPLITS))
    if seen_splits != expected_ids:
        raise RuntimeError(f"archive split inventory mismatch: saw {len(seen_splits)} of {EXPECTED_SPLITS}; "
                           f"missing {sorted(expected_ids - seen_splits)[:8]}")
    validated_ids = sorted(selected) if selected is not None else EXPECTED_SPLITS
    validation = validate_extended_ride_cache(str(cache), expected_splits=validated_ids,
                                              frames_per_split=FRAMES_PER_SPLIT, load_arrays=False)
    expected_frames = len(validated_ids) * FRAMES_PER_SPLIT if isinstance(validated_ids, list) else \
        EXPECTED_SPLITS * FRAMES_PER_SPLIT
    if validation["frames"] != expected_frames:
        raise RuntimeError(f"cache frame count mismatch: {validation['frames']}")
    report = {
        "schema": "resense-extended-ride-intake-v1",
        "status": "complete" if selected is None else "selected_splits_only",
        "source_url": public_url,
        "source_member": source["name"],
        "source_modified": source.get("modified"),
        "archive_bytes": hashed.bytes_read,
        "archive_size_published": source["size"],
        "archive_size_verified": hashed.bytes_read == source["size"],
        "archive_checksum_published": bool(expected_sha),
        "archive_sha256_published": expected_sha,
        "archive_sha256_actual": actual_sha,
        "archive_sha256_verified": (actual_sha.lower() == expected_sha.lower()) if expected_sha else None,
        "metadata_sha256": metadata_sha,
        "cache_location": str(cache),
        "encoding": "compact16 NPY, each frame independently zstd level 3 (.npy.zst)",
        "cache_splits": validation["splits"],
        "cache_frames": validation["frames"],
        "cache_bytes": validation["compressed_bytes"],
        "timestamp_coverage": {key: validation[key] for key in (
            "first_frame", "first_stamp", "last_frame", "last_stamp", "duration_s",
            "max_interval_s", "intervals_over_0_15_s")},
        "written_splits_this_run": sorted(written_splits),
        "reused_splits_this_run": sorted(reused_splits),
        "elapsed_s": round(time.monotonic() - started, 1),
    }
    if selected is None:
        _atomic_json(str(intake_path), report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache", default="/data/cache/new_data")
    parser.add_argument("--spool", default="/data/.resense_new_data_spool")
    parser.add_argument("--reserve-gib", type=float, default=3.0)
    parser.add_argument("--url", default=PUBLIC_URL, help="organizer's public Yandex Disk link")
    parser.add_argument("--only-splits", default="", help="comma-separated split ids for partial diagnosis only")
    args = parser.parse_args(argv)
    only = [int(v) for v in args.only_splits.split(",") if v.strip()] or None
    try:
        report = stream_cache(args.cache, args.spool, reserve_gib=args.reserve_gib,
                              public_url=args.url, only_splits=only)
    except (OSError, RuntimeError, ValueError, tarfile.TarError) as exc:
        print(f"ride intake failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
