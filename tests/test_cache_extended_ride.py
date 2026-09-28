"""The archive stream hashes its source and publishes a completion manifest last."""

import hashlib
import io
import json
import tarfile

import numpy as np
import pytest
import zstandard

import scripts.cache_extended_ride as intake
from scripts.cache_frames import _atomic_json, _atomic_save
from resense.pointcloud import COMPACT16_DTYPE


def _tar_zst():
    tar_bytes = io.BytesIO()
    with tarfile.open(fileobj=tar_bytes, mode="w") as archive:
        metadata = b"rosbag2_bagfile_information: {}\n"
        info = tarfile.TarInfo("./new_data/metadata.yaml")
        info.size = len(metadata)
        archive.addfile(info, io.BytesIO(metadata))
        payload = b"fake split payload"
        info = tarfile.TarInfo("./new_data/new_data_0.db3")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    return zstandard.ZstdCompressor(level=3).compress(tar_bytes.getvalue())


def _fake_cache_bag(_bag, out, every=1, topic=None, int16=True, stamps=True, zstd_level=3):
    assert every == 1 and int16 and stamps and zstd_level == 3
    stamp_map = {}
    for frame in range(3):
        arr = np.zeros(2, dtype=COMPACT16_DTYPE)
        arr["x"] = frame + 1
        stem = f"new_data_0_{frame:04d}"
        _atomic_save(f"{out}/{stem}.npy.zst", arr, zstd_level=3)
        stamp_map[f"{frame:04d}"] = 100.0 + frame * 0.1
    _atomic_json(f"{out}/new_data_0_stamps.json",
                 {"bag": "new_data_0", "frames": 3, "stamps": stamp_map})
    return "new_data_0", 3


def _configure(monkeypatch, compressed, checksum=None):
    monkeypatch.setattr(intake, "EXPECTED_SPLITS", 1)
    monkeypatch.setattr(intake, "FRAMES_PER_SPLIT", 3)
    monkeypatch.setattr(intake, "cache_bag", _fake_cache_bag)
    expected = checksum if checksum is not None else hashlib.sha256(compressed).hexdigest()
    monkeypatch.setattr(intake, "resolve_yadisk_asset", lambda **_kw: {
        "name": "new_data.zst", "size": len(compressed), "sha256": expected,
        "modified": "2026-09-17T12:51:29+00:00", "download_url": "https://example.invalid/archive"})
    monkeypatch.setattr(intake, "_require_space", lambda *_args: None)
    return lambda _url, **_kw: io.BytesIO(compressed)


def test_stream_cache_verifies_hash_and_writes_complete_manifest(tmp_path, monkeypatch):
    compressed = _tar_zst()
    opener = _configure(monkeypatch, compressed)
    cache = tmp_path / "cache"
    spool = tmp_path / "spool"

    report = intake.stream_cache(str(cache), str(spool), opener=opener)

    assert report["status"] == "complete"
    assert report["archive_sha256_verified"] is True
    assert report["cache_splits"] == 1 and report["cache_frames"] == 3
    saved = json.loads((cache / "intake_manifest.json").read_text())
    assert saved["archive_sha256_actual"] == hashlib.sha256(compressed).hexdigest()
    assert saved["timestamp_coverage"]["first_stamp"] == 100.0
    assert (cache / "metadata.yaml").exists()
    assert not list(spool.iterdir())


def test_hash_mismatch_never_marks_cache_complete(tmp_path, monkeypatch):
    compressed = _tar_zst()
    opener = _configure(monkeypatch, compressed, checksum="0" * 64)
    cache = tmp_path / "cache"

    with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
        intake.stream_cache(str(cache), str(tmp_path / "spool"), opener=opener)
    assert not (cache / "intake_manifest.json").exists()
