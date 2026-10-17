#!/usr/bin/env python3
"""List (and optionally extract) a zstd-compressed tar read from stdin.

    curl -sSL "$HREF" | tee >(sha256sum > a.sha256) | zst_tar_stdin.py --list > members.txt
    curl -sSL "$HREF" | zst_tar_stdin.py --out DIR --only name1,name2 [--max-bytes N]

``--max-bytes`` stops extracting a member after N bytes (a truncated sample of a large split
file), ``--skip-bytes`` starts that window later (written as ``<name>.at<offset>``); members are
written only when selected (exact name or basename match).
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
    p.add_argument("--max-bytes", type=int, default=0, help="write at most N bytes of each selected member")
    p.add_argument("--skip-bytes", type=int, default=0,
                   help="with --max-bytes: discard the first N bytes of the member (a window of a large split)")
    p.add_argument("--stop-after", type=int, default=0, help="stop the stream after N extracted members")
    a = p.parse_args()
    done = 0
    only = {s for s in a.only.split(",") if s}
    reader = zstandard.ZstdDecompressor().stream_reader(sys.stdin.buffer, read_across_frames=True)
    with tarfile.open(fileobj=reader, mode="r|") as tar:
        for m in tar:
            name = m.name.removeprefix("./")
            if a.list:
                print(f"{m.size:>14d}  {m.type.decode() if isinstance(m.type, bytes) else m.type}  {name}", flush=True)
                continue
            if a.out and (name in only or os.path.basename(name) in only):
                if a.max_bytes and m.size > a.max_bytes:
                    dst = os.path.join(a.out, name) + (f".at{a.skip_bytes}" if a.skip_bytes else "")
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    src, left = tar.extractfile(m), a.max_bytes
                    skip = a.skip_bytes
                    while skip > 0:
                        buf = src.read(min(skip, 1 << 22))
                        if not buf:
                            break
                        skip -= len(buf)
                    with open(dst, "wb") as f:
                        while left > 0:
                            buf = src.read(min(left, 1 << 22))
                            if not buf:
                                break
                            f.write(buf)
                            left -= len(buf)
                    print(f"extracted {a.max_bytes} bytes from offset {a.skip_bytes} of {m.size} bytes of {name}",
                          flush=True)
                else:
                    tar.extract(m, a.out)
                    print(f"extracted {m.size} {name}", flush=True)
                done += 1
                if a.stop_after and done >= a.stop_after:
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
