#!/usr/bin/env python3
"""Recover the PointCloud2 messages held in a byte window of a large rosbag2 sqlite3 split.

    window_bag.py WINDOW_FILE --base OFFSET --schema-from SMALL.db3 OUT.db3 [--frame-id seyond]

A window (bytes OFFSET .. OFFSET+len of the split, streamed out of the archive) is not a database:
sqlite needs the B-tree pages, which lie elsewhere. The message blobs, though, are plain sqlite
overflow chains: a table-leaf cell holds the record header, ``topic_id``, ``timestamp`` and the
first bytes of ``data``; the rest is in overflow pages (4-byte next-page number + 4092 bytes each,
page size 4096). The script finds every CDR PointCloud2 start (encapsulation 00 01 00 00, then a
``frame_id`` string), reads the blob length from the CDR header, computes the cell's local payload
size with sqlite's formula, and follows the overflow chain while its pages are inside the window.
Complete blobs are written, with their timestamp and topic id, into a new bag that copies the
schema and the ``topics`` rows of SCHEMA_FROM (a bag made from the same recording).
"""
from __future__ import annotations

import argparse
import mmap
import os
import sqlite3
import struct
import sys

PAGE = 4096
U = PAGE                              # no reserved bytes per page (checked in the header)
X = U - 35                            # max local payload of a table-leaf cell
M = ((U - 12) * 32 // 255) - 23       # min local payload


def local_size(p: int) -> int:
    if p <= X:
        return p
    k = M + ((p - M) % (U - 4))
    return k if k <= X else M


def cdr_blob_len(buf, cdr: int) -> int:
    """Length of a little-endian plain-CDR PointCloud2 blob starting at ``cdr``."""
    pos = 4

    def align(n):
        nonlocal pos
        pos += (-(pos - 4)) % n

    def u32():
        nonlocal pos
        align(4)
        v = struct.unpack_from("<I", buf, cdr + pos)[0]
        pos += 4
        return v

    def string():
        nonlocal pos
        n = u32()
        pos += n
    u32()
    u32()
    string()                           # stamp, frame_id
    u32()
    u32()                              # height, width
    for _ in range(u32()):
        string()
        u32()
        pos += 1
        u32()                          # name, offset, datatype, count
    pos += 1                           # is_bigendian
    u32()
    u32()                              # point_step, row_step
    n = u32()
    return (pos + n + 1 + 3) // 4 * 4  # data + is_dense, padded to 4 bytes as the serializer does


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("window")
    p.add_argument("--base", type=int, required=True, help="byte offset of the window in the split")
    p.add_argument("--schema-from", required=True)
    p.add_argument("out")
    p.add_argument("--frame-id", default="seyond")
    a = p.parse_args()
    f = open(a.window, "rb")
    buf = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    end = a.base + len(buf)
    fid = a.frame_id.encode() + b"\x00"
    sig = struct.pack("<I", len(fid)) + fid

    def page_bytes(pgno: int):
        off = (pgno - 1) * PAGE
        if off < a.base or off + PAGE > end:
            return None
        return buf[off - a.base: off - a.base + PAGE]

    src = sqlite3.connect(f"file:{a.schema_from}?mode=ro", uri=True)
    if os.path.exists(a.out):
        os.remove(a.out)
    dst = sqlite3.connect(a.out)
    for (sql,) in src.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"):
        dst.execute(sql)
    for t in ("topics", "schema", "metadata"):
        rows = list(src.execute(f"SELECT * FROM {t}"))
        if rows:
            dst.executemany(f"INSERT INTO {t} VALUES ({','.join('?' * len(rows[0]))})", rows)
    src.close()
    found = kept = 0
    pos = buf.find(sig)
    while pos >= 0:
        cdr = pos - 12
        if cdr >= 17 and buf[cdr:cdr + 4] == b"\x00\x01\x00\x00" and buf[cdr - 17] == 8:
            found += 1
            ps = cdr - 17                                # record start (payload start)
            topic_id = buf[ps + 8]
            ts = struct.unpack_from(">q", buf, ps + 9)[0]
            try:
                blen = cdr_blob_len(buf, cdr)
            except struct.error:
                blen = -1
            if blen > 0:
                loc = local_size(17 + blen)
                parts = [buf[cdr: ps + loc]]
                got = loc - 17
                nxt = struct.unpack_from(">I", buf, ps + loc)[0] if loc < 17 + blen else 0
                ok = True
                while got < blen and ok:
                    pg = page_bytes(nxt)
                    if pg is None:
                        ok = False
                        break
                    nxt = struct.unpack_from(">I", pg, 0)[0]
                    take = min(U - 4, blen - got)
                    parts.append(pg[4:4 + take])
                    got += take
                if ok and got == blen:
                    data = b"".join(parts)
                    dst.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (?, ?, ?)",
                                (topic_id, ts, data))
                    kept += 1
                    if kept % 100 == 0:
                        dst.commit()
                        print(f"{kept} messages, last timestamp {ts}", flush=True)
        pos = buf.find(sig, pos + 1)
    dst.commit()
    dst.close()
    print(f"found {found} message starts, wrote {kept} complete messages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
