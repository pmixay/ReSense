#!/usr/bin/env python3
"""Play a whole rosbag2 sqlite split through ONE detector straight from the archive stream (B2).

    stream_falcon.py <yadisk url | file.zst | file.db3> [--member NAME] [--inner NAME] --out <prefix>
        [--messages-only <out.db3>] [--limit N]

The Falcon recording is one 20.3 GB sqlite split. sqlite needs its B-tree pages to read rows, but each
message blob is a plain overflow chain (``docs/evidence/extended_data_2026-10-17/scripts/window_bag.py``).
This script reads the split once as a byte stream (zstd tar from the organizers' link or a local file),
keeps a rolling buffer of pages, recovers every complete PointCloud2 message, and feeds them in
timestamp order to the judge's node replica (``judge_runner.NodeReplica``: node decode, continuity rules,
decision rule). Nothing is written but the per-frame records (``<prefix>.jsonl``, ``.csv``, ``.meta.json``).
``--messages-only`` instead writes the recovered messages into a bag (the positive control: compare it
with the source bag).

A cell's first bytes sit in a leaf page that may precede its overflow pages by many messages, so the
buffer keeps ``--back`` MB behind the read position; a message whose chain reaches past the buffer end
waits for more data. Messages are released in timestamp order once ``--reorder`` newer ones are known.
"""
from __future__ import annotations

import argparse
import csv
import heapq
import json
import os
import resource
import sqlite3
import struct
import sys
import tarfile
import time
from pathlib import Path

import zstandard

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "docs/evidence/extended_data_2026-10-17/scripts"))
sys.path.insert(0, str(ROOT / "docs/evidence/judgement_2026-10-13/scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
from window_bag import PAGE, U, cdr_blob_len, local_size  # noqa: E402

CHUNK = 64 << 20


class Recover:
    """Rolling-buffer recovery of PointCloud2 blobs from a sqlite byte stream."""

    def __init__(self, frame_id: str, back_mb: int):
        fid = frame_id.encode() + b"\x00"
        self.sig = struct.pack("<I", len(fid)) + fid
        self.buf = bytearray()
        self.base = 0                  # file offset of buf[0]
        self.scanned = 0               # file offset up to which signatures were searched
        self.pending: list[int] = []   # file offsets of cell starts whose chain is not complete yet
        self.back = back_mb << 20
        self.found = self.kept = self.lost = 0

    def page(self, pgno: int):
        off = (pgno - 1) * PAGE
        if off < self.base:
            return "gone"
        if off + PAGE > self.base + len(self.buf):
            return None
        return self.buf[off - self.base: off - self.base + PAGE]

    def _try(self, ps: int):
        """(topic_id, ts, data) | None (needs more data) | 'lost' (chain left the buffer behind)."""
        b, i = self.buf, ps - self.base
        cdr = i + 17
        topic_id = b[i + 8]
        ts = struct.unpack_from(">q", b, i + 9)[0]
        try:
            blen = cdr_blob_len(b, cdr)
        except struct.error:
            return None
        loc = local_size(17 + blen)
        if i + loc + 4 > len(b):
            return None
        parts, got = [bytes(b[cdr: i + loc])], loc - 17
        nxt = struct.unpack_from(">I", b, i + loc)[0] if loc < 17 + blen else 0
        while got < blen:
            pg = self.page(nxt)
            if pg is None:
                return None
            if pg == "gone":
                return "lost"
            nxt = struct.unpack_from(">I", pg, 0)[0]
            take = min(U - 4, blen - got)
            parts.append(bytes(pg[4:4 + take]))
            got += take
        return topic_id, ts, b"".join(parts)

    def feed(self, data: bytes, final: bool = False):
        """Append stream bytes; yield every message that became complete."""
        self.buf += data
        end = self.base + len(self.buf)
        limit = end if final else end - 64
        start = max(self.scanned, self.base)
        pos = self.buf.find(self.sig, start - self.base)
        while 0 <= pos and self.base + pos < limit:
            cdr = pos - 12
            if cdr >= 17 and self.buf[cdr:cdr + 4] == b"\x00\x01\x00\x00" and self.buf[cdr - 17] == 8:
                self.found += 1
                self.pending.append(self.base + cdr - 17)
            pos = self.buf.find(self.sig, pos + 1)
        self.scanned = limit
        still = []
        for ps in self.pending:
            r = self._try(ps)
            if r is None:
                if final:
                    self.lost += 1
                else:
                    still.append(ps)
            elif r == "lost":
                self.lost += 1
            else:
                self.kept += 1
                yield r
        self.pending = still
        # drop what no pending cell and no future chain can need
        keep_from = min([end - self.back] + self.pending)
        cut = max(0, (keep_from - self.base) // PAGE * PAGE)
        if cut:
            del self.buf[:cut]
            self.base += cut


def byte_stream(src: str, member: str, inner: str):
    """Yield the bytes of the split: from a .db3, from a local .zst tar, or from a Yandex Disk link."""
    if src.endswith(".db3"):
        with open(src, "rb") as f:
            while chunk := f.read(CHUNK):
                yield chunk
        return
    if src.startswith("http"):
        from unpack_dataset import open_zst_stream
        raw = open_zst_stream(src, member)
    else:
        raw = open(src, "rb")
    stream = zstandard.ZstdDecompressor().stream_reader(raw, read_size=1 << 20)
    with tarfile.open(fileobj=stream, mode="r|") as tar:
        for ti in tar:
            if ti.isfile() and os.path.basename(ti.name) == inner:
                with tar.extractfile(ti) as f:
                    while chunk := f.read(CHUNK):
                        yield chunk
                return
    raise SystemExit(f"{inner} not found in the archive")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--member", default="falcon_test.zst")
    ap.add_argument("--inner", default="falcon_test_second_dark_0.db3")
    ap.add_argument("--frame-id", default="seyond")
    ap.add_argument("--topic-id", type=int, default=3, help="the PointCloud2 topic's id (falcon_test: 3 = /iv_points)")
    ap.add_argument("--topic", default="/iv_points")
    ap.add_argument("--out", required=True)
    ap.add_argument("--messages-only", default="", help="write the recovered messages into this bag instead")
    ap.add_argument("--schema-from", default="", help="with --messages-only: copy schema and topics from this bag")
    ap.add_argument("--back", type=int, default=256, help="MB kept behind the read position")
    ap.add_argument("--reorder", type=int, default=50, help="messages held back for timestamp ordering")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dump", default="", help="comma list of frame numbers whose decoded cloud is saved as <prefix>_f<k>.npz")
    a = ap.parse_args()

    rec = Recover(a.frame_id, a.back)
    heap: list = []
    log = {"order_violations": 0, "max_gap_s": 0.0, "first_ts": None, "last_ts": None, "duplicates": 0}
    seen: set[int] = set()
    t0, cpu0, n_bytes = time.time(), time.process_time(), 0

    if a.messages_only:
        dst = sqlite3.connect(a.messages_only)
        src = sqlite3.connect(f"file:{a.schema_from}?mode=ro", uri=True)
        for (sql,) in src.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"):
            dst.execute(sql)
        for t in ("topics", "schema", "metadata"):
            rows = list(src.execute(f"SELECT * FROM {t}"))
            if rows:
                dst.executemany(f"INSERT INTO {t} VALUES ({','.join('?' * len(rows[0]))})", rows)
        src.close()

        def emit(topic_id, ts, data):
            dst.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (?, ?, ?)", (topic_id, ts, data))
    else:
        import numpy as np
        from judge_runner import CSV_COLS, NodeReplica, csv_row, record
        from resense_ros import fastcloud
        rep = NodeReplica()
        dump = {int(v) for v in a.dump.split(",") if v}
        fj, fc = open(a.out + ".jsonl", "w"), open(a.out + ".csv", "w", newline="")
        w = csv.writer(fc)
        w.writerow(CSV_COLS)

        def emit(topic_id, ts, data):
            n = emit.n
            msg, stamp, res, dec_ms, det_ms = rep.process_raw(data, a.topic, n)
            if n in dump:       # the node decode (sensor frame) and the vehicle-frame rotation of this frame
                xyz, inten, _, _, _ = fastcloud.decode(fastcloud.packed(fastcloud.parse_pointcloud2(data)), 2.5, 250.0)
                np.savez_compressed(f"{a.out}_f{n:05d}.npz", xyz=xyz, inten=inten, R_vs=rep.R_vs,
                                    mount=np.asarray(rep.detector.mount_rotation))
            r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, a.topic)
            fj.write(json.dumps(r) + "\n")
            w.writerow(csv_row(r))
            emit.n += 1
        emit.n = 0

    last = None

    def release(force=False):
        nonlocal last
        while heap and (force or len(heap) > a.reorder):
            ts, topic_id, data = heapq.heappop(heap)
            if last is not None:
                if ts < last:
                    log["order_violations"] += 1
                log["max_gap_s"] = max(log["max_gap_s"], (ts - last) / 1e9)
            last = ts
            log["first_ts"] = log["first_ts"] or ts
            log["last_ts"] = ts
            emit(topic_id, ts, data)
            if a.limit and (emit.n if not a.messages_only else 0) >= a.limit:
                return True
        return False

    done = False
    for chunk in byte_stream(a.src, a.member, a.inner):
        n_bytes += len(chunk)
        for topic_id, ts, data in rec.feed(chunk):
            if topic_id != a.topic_id:
                log["other_topics"] = log.get("other_topics", 0) + 1
                continue
            if ts in seen:
                log["duplicates"] += 1
                continue
            seen.add(ts)
            heapq.heappush(heap, (ts, topic_id, data))
        if release():
            done = True
            break
        print(f"{n_bytes / 1e9:6.2f} GB read, {rec.kept} messages, {rec.lost} lost, buffer "
              f"{len(rec.buf) >> 20} MB, pending {len(rec.pending)}", flush=True)
    if not done:
        for topic_id, ts, data in rec.feed(b"", final=True):
            if topic_id == a.topic_id and ts not in seen:
                seen.add(ts)
                heapq.heappush(heap, (ts, topic_id, data))
        release(force=True)
    meta = {"src": a.src, "bytes": n_bytes, "found": rec.found, "kept": rec.kept, "lost": rec.lost, **log,
            "wall_s": round(time.time() - t0, 1), "cpu_s": round(time.process_time() - cpu0, 1),
            "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)}
    if a.messages_only:
        dst.commit()
        dst.close()
    else:
        fj.close()
        fc.close()
        meta.update(frames=emit.n, resets=rep.resets)
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
