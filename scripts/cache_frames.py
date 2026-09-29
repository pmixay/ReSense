#!/usr/bin/env python3
"""Cache every N-th PointCloud2 frame of a bag as a compact *.npy (sensor frame).

    python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 10
    python scripts/cache_frames.py /data/new_data/new_data_30.db3 cache/new_data --every 10   # one split file
    python scripts/cache_frames.py /data/for_hackathon/roundT_doubleT cache/ --every 1 --int16   # 1.5 MB per frame
    python scripts/cache_frames.py /data/new_data/new_data_30.db3 cache/new_data --every 1 --int16 --stamps --zstd

``--int16`` writes the quantised cache (``resense.pointcloud.COMPACT16_DTYPE``: centimetres as
int16, intensity and ring as uint8; 8 bytes per point instead of 18), which every reader of
the package (``resense run/eval/inject --npy``) loads transparently. ``--stamps`` also writes
``<name>_stamps.json`` with the bag receive time of every cached frame (the cached files carry
none; per-hour rates and the measured frame interval need it).
"""
import argparse
import json
import os
import tempfile

import numpy as np

from resense.io import iter_bag_compact
from resense.pointcloud import compact_to_compact16


def _atomic_save(path, arr, zstd_level=None):
    """Write one cache frame completely before making its final name visible."""
    temp = f"{path}.tmp"
    try:
        with open(temp, "wb") as raw:
            if zstd_level is None:
                np.save(raw, arr, allow_pickle=False)
            else:
                try:
                    import zstandard
                except ImportError as exc:
                    raise RuntimeError("--zstd requires the zstandard package") from exc
                compressor = zstandard.ZstdCompressor(level=zstd_level)
                with compressor.stream_writer(raw, closefd=False) as writer:
                    np.save(writer, arr, allow_pickle=False)
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _atomic_json(path, value):
    """Publish the split stamp manifest last so its presence means the split finished."""
    fd, temp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.", suffix=".tmp",
                                dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(value, fh)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def cache_bag(bag, out, every=10, topic=None, int16=False, stamps=False, zstd_level=None):
    """Cache a bag or one split DB3; return (name, frame_count)."""
    if every < 1:
        raise ValueError("every must be at least 1")
    if zstd_level is not None:
        try:
            import zstandard  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("compressed frame caches require the zstandard package") from exc
    os.makedirs(out, exist_ok=True)
    name = os.path.basename(os.path.normpath(bag))
    if name.endswith(".db3"):
        name = name[:-4]
    stamp_path = os.path.join(out, f"{name}_stamps.json")
    if stamps and os.path.exists(stamp_path):
        os.unlink(stamp_path)
    n = 0
    stamp_values = {}
    frame_id = ""
    suffix = ".npy.zst" if zstd_level is not None else ".npy"
    other_suffix = ".npy" if zstd_level is not None else ".npy.zst"
    for i, stamp, frame_id, arr in iter_bag_compact(bag, topic=topic, every=every):
        if int16:
            arr = compact_to_compact16(arr)
        stem = f"{name}_{i:04d}"
        path = os.path.join(out, stem + suffix)
        _atomic_save(path, arr, zstd_level=zstd_level)
        # A successful replacement removes only this same frame's older encoding.
        other_path = os.path.join(out, stem + other_suffix)
        if os.path.exists(other_path):
            os.unlink(other_path)
        stamp_values[f"{i:04d}"] = stamp
        n += 1
    if stamps:
        _atomic_json(stamp_path, {"bag": name, "frame_id": frame_id if n else "",
                                  "frames": n, "stamps": stamp_values})
    return name, n


def main():
    p = argparse.ArgumentParser()
    p.add_argument("bag")
    p.add_argument("out")
    p.add_argument("--every", type=int, default=10)
    p.add_argument("--topic", default=None)
    p.add_argument("--int16", action="store_true", help="quantised 8-byte-per-point cache")
    p.add_argument("--stamps", action="store_true", help="write <name>_stamps.json (bag time per frame)")
    p.add_argument("--zstd", action="store_true", help="compress each NPY frame as .npy.zst")
    p.add_argument("--zstd-level", type=int, default=3, help="zstandard level used with --zstd (default: 3)")
    a = p.parse_args()
    name, n = cache_bag(a.bag, a.out, every=a.every, topic=a.topic, int16=a.int16,
                        stamps=a.stamps, zstd_level=a.zstd_level if a.zstd else None)
    encoding = ".npy.zst" if a.zstd else ".npy"
    print(f"cached {n} frames of {name} to {a.out} ({encoding})")


if __name__ == "__main__":
    main()
