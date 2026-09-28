"""Helpers for offline *.npy and *.npy.zst frame caches.

This module stays in ``scripts`` because the validated detector source is sealed independently.
The cache encoding changes storage only; arrays remain the same compact16 NPY payload.
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

from resense.pointcloud import COMPACT16_DTYPE


def cache_file_stem(path: str | os.PathLike) -> str:
    """Remove the complete cache suffix from ``frame.npy`` or ``frame.npy.zst``."""
    name = os.path.basename(os.fspath(path))
    if name.endswith(".npy.zst"):
        return name[:-8]
    if name.endswith(".npy"):
        return name[:-4]
    return os.path.splitext(name)[0]


def natural_key(path: str):
    """Sort cache names numerically (split 2 before split 10)."""
    return [int(token) if token.isdigit() else token
            for token in re.split(r"(\d+)", os.path.basename(path))]


def cache_files(directory: str, pattern: Optional[str] = None) -> list[str]:
    """Return frame caches in natural order and reject duplicate stems."""
    if pattern in (None, "*.npy"):
        files = (glob.glob(os.path.join(directory, "*.npy"))
                 + glob.glob(os.path.join(directory, "*.npy.zst")))
    else:
        files = glob.glob(os.path.join(directory, pattern))
        if pattern.endswith(".npy"):
            files += glob.glob(os.path.join(directory, pattern + ".zst"))
    files = sorted(files, key=natural_key)
    seen, duplicates = set(), []
    for path in files:
        stem = cache_file_stem(path)
        if stem in seen:
            duplicates.append(stem)
        seen.add(stem)
    if duplicates:
        raise ValueError(f"duplicate cached frame stems in {directory}: {sorted(set(duplicates))[:5]}")
    return files


def load_cache_array(path: str | os.PathLike) -> np.ndarray:
    """Load a compact frame from NPY or zstandard-compressed NPY without pickle support."""
    path = os.fspath(path)
    if not path.endswith(".npy.zst"):
        return np.load(path, allow_pickle=False)
    try:
        import zstandard
    except ImportError as exc:
        raise RuntimeError("reading .npy.zst caches requires the zstandard package") from exc
    with open(path, "rb") as raw, zstandard.ZstdDecompressor().stream_reader(raw) as reader:
        payload = reader.read()
    return np.load(io.BytesIO(payload), allow_pickle=False)


def load_cache_stamps(directory: str) -> dict:
    """Return cache frame stems mapped to bag receive times."""
    out = {}
    for path in glob.glob(os.path.join(directory, "*_stamps.json")):
        try:
            manifest = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name = manifest.get("bag") or os.path.basename(path)[:-len("_stamps.json")]
        for frame, stamp in manifest.get("stamps", {}).items():
            out[f"{name}_{frame}"] = float(stamp)
    return out


def validate_extended_ride_cache(directory: str, expected_splits=221, frames_per_split: int = 51,
                                 load_arrays: bool = False) -> dict:
    """Validate split identities, complete stamp sidecars and optionally every cached array.

    ``expected_splits`` may be the full count (split ids 0..N-1) or an iterable of ids to validate
    while resuming intake. Timestamp gaps are preserved and reported; no time or frame is filled.
    """
    full = isinstance(expected_splits, int)
    split_ids = list(range(expected_splits)) if full else sorted(set(int(n) for n in expected_splits))
    files = cache_files(directory)
    file_pattern = re.compile(r"new_data_(\d+)_(\d+)$")
    by_split = defaultdict(dict)
    for path in files:
        match = file_pattern.fullmatch(cache_file_stem(path))
        if not match:
            raise ValueError(f"unexpected file in extended ride cache: {os.path.basename(path)}")
        split, frame = map(int, match.groups())
        by_split[split][frame] = path
    if full and set(by_split) != set(split_ids):
        missing = sorted(set(split_ids) - set(by_split))
        extra = sorted(set(by_split) - set(split_ids))
        raise ValueError(f"ride split inventory mismatch; missing={missing[:8]} extra={extra[:8]}")

    ordered_stamps = []
    compressed_bytes = arrays_read = 0
    for split in split_ids:
        expected_frames = set(range(frames_per_split))
        actual_frames = set(by_split.get(split, {}))
        if actual_frames != expected_frames:
            missing = sorted(expected_frames - actual_frames)
            extra = sorted(actual_frames - expected_frames)
            raise ValueError(f"new_data split {split} is incomplete; missing={missing[:8]} extra={extra[:8]}")
        name = f"new_data_{split}"
        stamp_path = Path(directory) / f"{name}_stamps.json"
        try:
            manifest = json.loads(stamp_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"missing or invalid timestamp manifest for split {split}: {stamp_path}") from exc
        stamp_map = manifest.get("stamps")
        wanted_keys = {f"{frame:04d}" for frame in expected_frames}
        if manifest.get("bag") != name or not isinstance(stamp_map, dict) or set(stamp_map) != wanted_keys:
            raise ValueError(f"timestamp manifest for split {split} does not cover frames 0000..{frames_per_split-1}")
        split_stamps = []
        for frame in range(frames_per_split):
            key = f"{frame:04d}"
            try:
                stamp = float(stamp_map[key])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid timestamp {name}_{key}") from exc
            if not np.isfinite(stamp):
                raise ValueError(f"non-finite timestamp {name}_{key}")
            split_stamps.append(stamp)
            path = by_split[split][frame]
            compressed_bytes += os.path.getsize(path)
            if load_arrays:
                arr = load_cache_array(path)
                if arr.dtype != COMPACT16_DTYPE or arr.ndim != 1 or arr.size == 0:
                    raise ValueError(f"invalid int16 compact frame {os.path.basename(path)}: {arr.dtype}/{arr.shape}")
                arrays_read += 1
        if any(b <= a for a, b in zip(split_stamps, split_stamps[1:])):
            raise ValueError(f"timestamps are not strictly increasing within split {split}")
        ordered_stamps.extend((f"{name}_{frame:04d}", stamp)
                              for frame, stamp in enumerate(split_stamps))

    if any(b[1] <= a[1] for a, b in zip(ordered_stamps, ordered_stamps[1:])):
        raise ValueError("ride timestamps are not strictly increasing across split boundaries")
    intervals = [b[1] - a[1] for a, b in zip(ordered_stamps, ordered_stamps[1:])]
    return {
        "splits": len(split_ids), "frames": len(ordered_stamps), "arrays_read": arrays_read,
        "compressed_bytes": compressed_bytes,
        "first_frame": ordered_stamps[0][0] if ordered_stamps else None,
        "first_stamp": ordered_stamps[0][1] if ordered_stamps else None,
        "last_frame": ordered_stamps[-1][0] if ordered_stamps else None,
        "last_stamp": ordered_stamps[-1][1] if ordered_stamps else None,
        "duration_s": ordered_stamps[-1][1] - ordered_stamps[0][1] if len(ordered_stamps) > 1 else 0.0,
        "max_interval_s": max(intervals, default=0.0),
        "intervals_over_0_15_s": sum(dt > 0.15 for dt in intervals),
    }


def validate_ride_intake_manifest(directory: str, cache_report: dict,
                                  expected_splits: int = 221, frames_per_split: int = 51) -> dict:
    """Require a complete cache whose organizer archive size/checksum was verified at intake."""
    path = Path(directory) / "intake_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"missing or invalid verified ride intake manifest: {path}") from exc
    if manifest.get("status") != "complete":
        raise ValueError("ride intake manifest is not marked complete")
    if manifest.get("archive_size_verified") is not True:
        raise ValueError("ride archive byte count was not verified")
    if manifest.get("archive_checksum_published"):
        if manifest.get("archive_sha256_verified") is not True:
            raise ValueError("published ride archive SHA-256 was not verified")
        if manifest.get("archive_sha256_actual") != manifest.get("archive_sha256_published"):
            raise ValueError("ride archive SHA-256 fields disagree")
    expected_frames = expected_splits * frames_per_split
    if (manifest.get("cache_splits") != expected_splits
            or manifest.get("cache_frames") != expected_frames
            or cache_report.get("splits") != expected_splits
            or cache_report.get("frames") != expected_frames
            or manifest.get("cache_bytes") != cache_report.get("compressed_bytes")):
        raise ValueError("ride intake manifest counts do not match the current complete cache")
    return manifest
