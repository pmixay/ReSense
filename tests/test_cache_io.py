"""Compressed frame-cache I/O and completeness checks for the organizer ride."""

import json

import numpy as np
import pytest

from scripts.cache_io import (cache_file_stem, cache_files, load_cache_array,
                              validate_extended_ride_cache)
from resense.pointcloud import COMPACT16_DTYPE
from scripts.cache_frames import _atomic_save


def _frame(value=1):
    out = np.zeros(3, dtype=COMPACT16_DTYPE)
    out["x"] = value
    out["ring"] = 7
    return out


def _split(directory, split, stamps, frames=3):
    name = f"new_data_{split}"
    values = {}
    for frame in range(frames):
        stem = f"{name}_{frame:04d}"
        _atomic_save(str(directory / f"{stem}.npy.zst"), _frame(frame + 1), zstd_level=3)
        values[f"{frame:04d}"] = stamps[frame]
    (directory / f"{name}_stamps.json").write_text(
        json.dumps({"bag": name, "frames": frames, "stamps": values}), encoding="utf-8")


def test_npy_zstd_round_trip_and_natural_order(tmp_path):
    a = _frame(2)
    b = _frame(10)
    _atomic_save(str(tmp_path / "new_data_2_0000.npy.zst"), a, zstd_level=3)
    np.save(tmp_path / "new_data_10_0000.npy", b, allow_pickle=False)

    files = cache_files(str(tmp_path), "*.npy")
    assert [cache_file_stem(p) for p in files] == ["new_data_2_0000", "new_data_10_0000"]
    assert np.array_equal(load_cache_array(files[0]), a)
    assert np.array_equal(load_cache_array(files[1]), b)


def test_cache_file_list_rejects_duplicate_encodings(tmp_path):
    np.save(tmp_path / "frame.npy", _frame(), allow_pickle=False)
    _atomic_save(str(tmp_path / "frame.npy.zst"), _frame(), zstd_level=3)
    with pytest.raises(ValueError, match="duplicate cached frame stems"):
        cache_files(str(tmp_path))


def test_ride_cache_validator_checks_complete_splits_and_preserves_gaps(tmp_path):
    _split(tmp_path, 0, [100.0, 100.1, 100.2])
    _split(tmp_path, 1, [101.0, 101.1, 101.2])

    report = validate_extended_ride_cache(str(tmp_path), expected_splits=2,
                                          frames_per_split=3, load_arrays=True)
    assert report["splits"] == 2
    assert report["frames"] == report["arrays_read"] == 6
    assert report["first_stamp"] == 100.0
    assert report["last_stamp"] == 101.2
    assert report["intervals_over_0_15_s"] == 1


def test_ride_cache_validator_rejects_missing_frame_or_stamp(tmp_path):
    _split(tmp_path, 0, [100.0, 100.1, 100.2])
    (tmp_path / "new_data_0_0001.npy.zst").unlink()
    with pytest.raises(ValueError, match="split 0 is incomplete"):
        validate_extended_ride_cache(str(tmp_path), expected_splits=1, frames_per_split=3)

    _atomic_save(str(tmp_path / "new_data_0_0001.npy.zst"), _frame(), zstd_level=3)
    (tmp_path / "new_data_0_stamps.json").unlink()
    with pytest.raises(ValueError, match="timestamp manifest"):
        validate_extended_ride_cache(str(tmp_path), expected_splits=1, frames_per_split=3)
