"""Split cache writes are atomic and publish timestamps only after all frames succeed."""

import json

import numpy as np
import pytest

import scripts.cache_frames as cache_frames
from scripts.cache_io import cache_files, load_cache_array
from resense.pointcloud import COMPACT_DTYPE


def _points(x):
    out = np.zeros(4, dtype=COMPACT_DTYPE)
    out["x"] = x
    out["intensity"] = 20
    out["ring"] = 4
    return out


def test_real_standalone_split_matches_directory_and_preserves_selection(tmp_path):
    """The streaming ride intake hands the reader a DB3 without metadata.yaml."""
    from rosbags.typesys import Stores, get_typestore

    from resense.io import iter_bag_compact
    from scripts.make_smoke_bag import FRAME_ID, make_message, write_bag

    bag = tmp_path / "tiny"
    ts = get_typestore(Stores.ROS2_HUMBLE)
    t0 = 1_700_000_000_000_000_000
    period = 100_000_000
    xyz = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.float32)
    messages = [make_message(ts, xyz + i, np.array([10, 20], dtype=np.float32),
                             np.array([2, 3], dtype=np.uint16), t0 + i * period,
                             i * 0.1, np.random.default_rng(i)) for i in range(4)]
    write_bag(str(bag), messages, t0, period)
    expected = list(iter_bag_compact(str(bag), start=1, every=2, limit=2))
    (bag / "metadata.yaml").unlink()
    split = next(bag.glob("*.db3"))
    actual = list(iter_bag_compact(str(split), start=1, every=2, limit=2))
    assert [row[0] for row in actual] == [1, 3]
    for got, want in zip(actual, expected, strict=True):
        assert got[:3] == want[:3]
        assert got[1] == (t0 + got[0] * period) / 1e9
        assert got[2] == FRAME_ID
        np.testing.assert_array_equal(got[3], want[3])
    with pytest.raises(RuntimeError, match="no PointCloud2 topic"):
        list(iter_bag_compact(str(split), topic="/absent"))


def test_compressed_split_cache_writes_readable_frames_and_stamp_manifest(tmp_path, monkeypatch):
    frames = [
        (0, 100.0, "lidar", _points(1.0)),
        (1, 100.1, "lidar", _points(2.0)),
    ]
    monkeypatch.setattr(cache_frames, "iter_bag_compact", lambda *a, **kw: iter(frames))

    name, count = cache_frames.cache_bag("/bags/new_data_5.db3", str(tmp_path), every=1,
                                         int16=True, stamps=True, zstd_level=3)
    assert (name, count) == ("new_data_5", 2)
    files = cache_files(str(tmp_path))
    assert [p.rsplit("/", 1)[-1] for p in files] == [
        "new_data_5_0000.npy.zst", "new_data_5_0001.npy.zst"]
    assert all(load_cache_array(path).dtype.names == ("x", "y", "z", "intensity", "ring")
               for path in files)
    stamps = json.loads((tmp_path / "new_data_5_stamps.json").read_text())
    assert stamps["frames"] == 2
    assert stamps["stamps"] == {"0000": 100.0, "0001": 100.1}


def test_failed_split_cache_has_no_completion_manifest(tmp_path, monkeypatch):
    (tmp_path / "new_data_5_stamps.json").write_text("old completion marker", encoding="utf-8")
    frames = [(0, 100.0, "lidar", _points(1.0)), (1, 100.1, "lidar", _points(2.0))]
    monkeypatch.setattr(cache_frames, "iter_bag_compact", lambda *a, **kw: iter(frames))
    save = cache_frames._atomic_save
    calls = 0

    def fail_second(path, arr, zstd_level=None):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated interrupted split")
        return save(path, arr, zstd_level=zstd_level)

    monkeypatch.setattr(cache_frames, "_atomic_save", fail_second)
    with pytest.raises(OSError, match="simulated interrupted split"):
        cache_frames.cache_bag("/bags/new_data_5.db3", str(tmp_path), every=1,
                               int16=True, stamps=True, zstd_level=3)
    assert not (tmp_path / "new_data_5_stamps.json").exists()
    assert (tmp_path / "new_data_5_0000.npy.zst").exists()
    assert not list(tmp_path.glob("*.tmp"))
