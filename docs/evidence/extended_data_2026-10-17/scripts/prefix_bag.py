#!/usr/bin/env python3
"""Turn a truncated rosbag2 sqlite3 file (the first N bytes of a split, streamed from the archive)
into a valid small bag holding every message that is readable from the prefix.

    prefix_bag.py TRUNCATED.db3 OUT_DIR/OUT.db3 [--every K]

The header of the prefix still declares the full page count, which sqlite rejects as corrupt
unless ``writable_schema`` is on (then it uses the file size; the source is opened read-only).
Rows are read in rowid order until the first page beyond the end of the prefix (sqlite reports the
image as malformed there); the schema (topics, metadata tables) is copied as is. ``--every K`` keeps
every K-th PointCloud2 message (all messages of other types). The output is a sqlite3 file the
judge runner and the analysis scripts read like any bag.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--every", type=int, default=1)
    a = p.parse_args()
    src = sqlite3.connect(f"file:{a.src}?mode=ro", uri=True)
    # the header still counts the pages of the whole split; with writable_schema sqlite takes the
    # page count from the file size instead of refusing the file as corrupt (nothing is written)
    src.execute("PRAGMA writable_schema=ON")
    if os.path.exists(a.dst):
        os.remove(a.dst)
    dst = sqlite3.connect(a.dst)
    for (sql,) in src.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"):
        dst.execute(sql)
    tables = [t for (t,) in src.execute("SELECT name FROM sqlite_master WHERE type='table'") if t != "messages"]
    for t in tables:
        try:
            rows = list(src.execute(f"SELECT * FROM {t}"))
        except sqlite3.DatabaseError as e:
            print(f"table {t}: {e}", file=sys.stderr)
            continue
        if rows:
            dst.executemany(f"INSERT INTO {t} VALUES ({','.join('?' * len(rows[0]))})", rows)
    pc = {tid for tid, typ in src.execute("SELECT id, type FROM topics") if typ == "sensor_msgs/msg/PointCloud2"}
    n = kept = k = 0
    last_ts = None
    try:
        for row in src.execute("SELECT id, topic_id, timestamp, data FROM messages ORDER BY id"):
            n += 1
            last_ts = row[2]
            if row[1] in pc:
                k += 1
                if (k - 1) % a.every:
                    continue
            dst.execute("INSERT INTO messages (id, topic_id, timestamp, data) VALUES (?, ?, ?, ?)", row)
            kept += 1
            if kept % 200 == 0:
                dst.commit()
                print(f"{n} rows read, {kept} kept", flush=True)
    except sqlite3.DatabaseError as e:
        print(f"prefix ends after {n} rows (last timestamp {last_ts}): {e}", file=sys.stderr)
    dst.commit()
    dst.close()
    print(f"read {n} rows ({k} PointCloud2), kept {kept}, last timestamp {last_ts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
