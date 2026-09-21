#!/usr/bin/env python3
"""Unpack the organizers' dataset archive without intermediate copies.

The download is nested: ``Датасет.zip`` (stored) → ``Датасет/датасет.zip`` (deflate) →
``archive/for_hackathon.zst`` (zstd-compressed tar, ~4 GB) → ``for_hackathon/<bag>/``
(six ROS 2 bags, ~22 GB). Unpacking it by hand needs ~30 GB of scratch space; this script
streams zip → zip → zstd → tar and writes only the bags you ask for.

    python scripts/unpack_dataset.py Датасет.zip --list
    python scripts/unpack_dataset.py Датасет.zip --out /data                       # all six bags
    python scripts/unpack_dataset.py Датасет.zip --out /data --only doubleT_obstacle,roundT_doubleT

Needs the ``zstandard`` package (installed with ``pip install -e ".[dev]"``). Also accepts the
inner ``датасет.zip`` or the bare ``for_hackathon.zst`` as input.
"""
from __future__ import annotations

import argparse
import os
import sys
import tarfile
import time
import zipfile


def open_zst_stream(path: str):
    """Return a readable binary stream positioned at the start of the zstd payload."""
    if path.endswith(".zst"):
        return open(path, "rb")
    outer = zipfile.ZipFile(path)
    names = outer.namelist()
    inner_zip = [n for n in names if n.lower().endswith(".zip")]
    zst = [n for n in names if n.endswith(".zst")]
    if zst:
        return outer.open(zst[0])
    if not inner_zip:
        sys.exit(f"{path}: no .zip or .zst member found ({names})")
    inner = zipfile.ZipFile(outer.open(inner_zip[0]))   # the outer member is stored → seekable
    zst = [n for n in inner.namelist() if n.endswith(".zst")]
    if not zst:
        sys.exit(f"{inner_zip[0]}: no .zst member found ({inner.namelist()})")
    return inner.open(zst[0])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("archive", help="Датасет.zip, датасет.zip or for_hackathon.zst")
    p.add_argument("--out", default="/data", help="directory that will contain for_hackathon/ (default /data)")
    p.add_argument("--only", default="", help="comma-separated bag names to extract (default: all)")
    p.add_argument("--list", action="store_true", help="only list the archive members")
    a = p.parse_args()
    try:
        import zstandard
    except ImportError:
        sys.exit("pip install zstandard   (or: pip install -e '.[dev]')")

    only = {b.strip() for b in a.only.split(",") if b.strip()}
    raw = open_zst_stream(a.archive)
    dctx = zstandard.ZstdDecompressor()
    reader = dctx.stream_reader(raw, read_across_frames=True)
    t0 = time.time()
    n_files, n_bytes = 0, 0
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for member in tar:
            parts = member.name.split("/")
            bag = parts[1] if len(parts) > 1 else ""
            if a.list:
                print(f"{member.size:>14,d}  {member.name}")
                continue
            if only and bag not in only:
                continue
            if member.isdir() or member.isfile():
                tar.extract(member, a.out)
                if member.isfile():
                    n_files += 1
                    n_bytes += member.size
                    print(f"{time.time() - t0:7.0f} s  {member.size / 1e9:6.2f} GB  {member.name}", flush=True)
    if not a.list:
        print(f"extracted {n_files} files, {n_bytes / 1e9:.1f} GB to {a.out} in {time.time() - t0:.0f} s")
        if only:
            print("bags:", ", ".join(sorted(only)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
