#!/usr/bin/env python3
"""List (and optionally extract) a zstd-compressed tar read from stdin.

    curl -sSL "$HREF" | tee >(sha256sum > a.sha256) | zst_tar_stdin.py --list > members.txt
    curl -sSL "$HREF" | zst_tar_stdin.py --out DIR --only name1,name2 [--max-bytes N]

``--max-bytes`` stops extracting a member after N bytes (a truncated sample of a large split
file); members are written only when selected (exact name or basename match).
"""
from __future__ import annotations

import argparse
import os
import sys
import tarfile

import zstandard


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true")
    p.add_argument("--out", default="")
    p.add_argument("--only", default="")
    a = p.parse_args()
    only = {s for s in a.only.split(",") if s}
    reader = zstandard.ZstdDecompressor().stream_reader(sys.stdin.buffer, read_across_frames=True)
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for m in tar:
            name = m.name.removeprefix("./")
            if a.list:
                print(f"{m.size:>14d}  {m.type.decode() if isinstance(m.type, bytes) else m.type}  {name}", flush=True)
                continue
            if a.out and (name in only or os.path.basename(name) in only):
                tar.extract(m, a.out)
                print(f"extracted {m.size} {name}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
