#!/usr/bin/env python3
"""Cut a short demo bag out of the organizers' Falcon Prime recording (``falcon_test``).

    make_falcon_demo_bag.py SRC OUT_DIR --first-frame A --last-frame B [--manifest FRAMES.tsv]
    make_falcon_demo_bag.py SRC OUT_DIR --start-s 280 --end-s 330 [--manifest FRAMES.tsv]

SRC is the organizers' Yandex Disk link (https://disk.yandex.ru/d/SfBeRHbs8bNJAQ), the archive file
``falcon_test.zst``, or a rosbag2 sqlite split (``*.db3``, whole or a bag this script wrote). Nothing
but the output bag is stored: the archive is streamed (20.3 GB split, the first 75 % are read for a
window that ends at 330 s), every PointCloud2 message is recovered from the sqlite overflow chains
(``scripts/stream_falcon.py`` ``Recover``, ``byte_stream``) and sorted by receive time.

A frame is the k-th (from 0) ``/iv_points`` message by receive time, the same index as in the per-frame
detector records (``docs/evidence/l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz``, field ``i``).
``--first-frame/--last-frame`` are inclusive; ``--start-s/--end-s`` are seconds of receive time after the
first message, ``start <= t < end``. The two ways exclude each other.

The messages are written unchanged: payload bytes, receive time (the ``timestamp`` column), topic row (name,
type, serialization format, QoS profiles) and the ``schema`` table of the source are copied as they are, and
the header stamps are inside the payload. Message ids are renumbered 1..N (rosbag2 orders by timestamp).
Other topics of the source (``/rosout`` driver log, topics without messages) are not carried. The bag
directory holds ``<name>_0.db3`` and a ``metadata.yaml`` in the format of the source (version 5, Humble).
After writing, the bag is read back through sqlite and compared with what was recovered. The script exits
non-zero, and removes what it wrote, if a message was lost on the way (the frame numbers would no longer
match), if the stream ends before the window does, or if the window is empty.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import os
import resource
import shutil
import sqlite3
import struct
import sys
import tempfile
import time
from pathlib import Path

import yaml

POINTCLOUD2 = "sensor_msgs/msg/PointCloud2"
PREFIX_BYTES = 1 << 20          # the schema and topics tables lie in the first pages of the split
METADATA_VERSION = 5            # rosbag2 metadata version of the source (Humble)
MANIFEST_HEADER = "frame\tbag_time_ns\theader_stamp\tbytes\tsha256"


class DemoBagError(RuntimeError):
    """The bag could not be cut as asked."""


def recovery():
    """``(Recover, byte_stream)`` of ``scripts/stream_falcon.py``, imported on first use.

    That module takes the sqlite overflow-chain code from ``docs/evidence/extended_data_2026-10-17/scripts``,
    which the runtime image does not carry (docs/ is outside its build context); everything else here
    imports without it.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from stream_falcon import Recover, byte_stream
    return Recover, byte_stream


def header_info(data: bytes) -> tuple[str, str, int, int]:
    """(header stamp 'sec.nanosec', frame_id, width, point_step) of a little-endian CDR PointCloud2."""
    sec, nsec, flen = struct.unpack_from("<iII", data, 4)
    frame_id = bytes(data[16:16 + flen - 1]).decode("ascii", "replace")
    pos = 16 + flen
    pos += -pos % 4
    _, width = struct.unpack_from("<II", data, pos)         # height, width
    pos += 8
    n_fields = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    for _ in range(n_fields):                               # name (string), offset u32, datatype u8, count u32
        pos += 4 + struct.unpack_from("<I", data, pos)[0]
        pos += -pos % 4 + 4 + 1
        pos += -pos % 4 + 4
    pos += 1                                                # is_bigendian
    pos += -pos % 4
    return f"{sec}.{nsec:09d}", frame_id, width, struct.unpack_from("<I", data, pos)[0]


def read_source_schema(prefix: bytes, topic: str) -> dict:
    """DDL, ``schema`` rows and the topic's row from the first bytes of the split.

    The header of the prefix still declares the page count of the whole split, which sqlite refuses
    unless ``writable_schema`` is on (it then takes the size of the file; the file is opened read-only).
    """
    with tempfile.TemporaryDirectory(prefix="falcon_demo_head_") as tmp:
        head = os.path.join(tmp, "head.db3")
        with open(head, "wb") as fh:
            fh.write(prefix)
        con = sqlite3.connect(f"file:{head}?mode=ro", uri=True)
        try:
            con.execute("PRAGMA writable_schema=ON")
            ddl = [sql for (sql,) in con.execute(
                "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY rowid")]
            schema_rows = list(con.execute("SELECT * FROM schema"))
            topics = list(con.execute(
                "SELECT id, name, type, serialization_format, offered_qos_profiles FROM topics ORDER BY id"))
        except sqlite3.DatabaseError as exc:
            raise DemoBagError(f"cannot read the schema and topics from the first {len(prefix)} bytes: {exc}")
        finally:
            con.close()
    rows = [t for t in topics if t[1] == topic]
    if len(rows) != 1:
        raise DemoBagError(f"topic {topic} is not in the source (topics: {[t[1] for t in topics]})")
    if rows[0][2] != POINTCLOUD2:
        raise DemoBagError(f"topic {topic} has type {rows[0][2]}, not {POINTCLOUD2}")
    return {"ddl": ddl, "schema_rows": schema_rows, "topic_row": rows[0]}


def ordered_frames(chunks, rec, topic_id: int, reorder: int, stats: dict):
    """Every message of the topic from the byte chunks, in receive-time order: (index, ts, data).

    The recovery returns messages roughly in file order; ``reorder`` newer messages must be known before
    one is released, the same rule as ``stream_falcon.py``. A repeated timestamp is dropped and counted.
    """
    heap: list = []
    seen: set[int] = set()
    prev = None
    index = 0

    def take(messages):
        for tid, ts, data in messages:
            if tid != topic_id:
                stats["other_topics"] += 1
            elif ts in seen:
                stats["duplicates"] += 1
            else:
                seen.add(ts)
                heapq.heappush(heap, (ts, data))

    def release(force):
        nonlocal prev, index
        while heap and (force or len(heap) > reorder):
            ts, data = heapq.heappop(heap)
            if prev is not None and ts < prev:
                stats["order_violations"] += 1
            prev = ts
            yield index, ts, data
            index += 1

    for chunk in chunks:
        stats["bytes"] += len(chunk)
        take(rec.feed(chunk))
        yield from release(False)
        if stats["bytes"] >= stats["next_progress"]:
            stats["next_progress"] += 1 << 30
            print(f"{stats['bytes'] / 1e9:6.2f} GB read, {rec.kept} messages recovered, {rec.lost} lost, "
                  f"frame {index}", flush=True)
    take(rec.feed(b"", final=True))
    yield from release(True)


class Window:
    """Which frames are kept: by index (inclusive), or by receive time after the first message."""

    def __init__(self, first_frame=None, last_frame=None, start_s=None, end_s=None):
        by_frame = first_frame is not None or last_frame is not None
        by_time = start_s is not None or end_s is not None
        if by_frame == by_time:
            raise DemoBagError("give either --first-frame and --last-frame, or --start-s and --end-s")
        if by_frame:
            if first_frame is None or last_frame is None or not 0 <= first_frame <= last_frame:
                raise DemoBagError("--first-frame and --last-frame must both be given, 0 <= first <= last")
        elif start_s is None or end_s is None or not 0 <= start_s < end_s:
            raise DemoBagError("--start-s and --end-s must both be given, 0 <= start < end")
        self.first_frame, self.last_frame, self.start_s, self.end_s = first_frame, last_frame, start_s, end_s
        self.t0 = None

    def contains(self, index: int, ts: int) -> bool:
        if self.first_frame is not None:
            return self.first_frame <= index <= self.last_frame
        return self.start_s <= (ts - self.t0) / 1e9 < self.end_s

    def past(self, index: int, ts: int) -> bool:
        if self.first_frame is not None:
            return index > self.last_frame
        return (ts - self.t0) / 1e9 >= self.end_s

    def expected(self):
        return None if self.first_frame is None else self.last_frame - self.first_frame + 1

    def describe(self) -> dict:
        if self.first_frame is not None:
            return {"first_frame": self.first_frame, "last_frame": self.last_frame}
        return {"start_s": self.start_s, "end_s": self.end_s}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while block := fh.read(1 << 24):
            h.update(block)
    return h.hexdigest()


def metadata_dict(db_name: str, topic_row: tuple, count: int, first_ns: int, last_ns: int) -> dict:
    """The ``metadata.yaml`` content. Every time value is its own dict: YAML anchors and aliases would
    otherwise appear in the file (PyYAML emits them for an object used twice), which the source does not have."""
    def start():
        return {"nanoseconds_since_epoch": first_ns}

    def duration():
        return {"nanoseconds": last_ns - first_ns}

    return {"rosbag2_bagfile_information": {
        "version": METADATA_VERSION,
        "storage_identifier": "sqlite3",
        "duration": duration(),
        "starting_time": start(),
        "message_count": count,
        "topics_with_message_count": [{
            "topic_metadata": {"name": topic_row[1], "type": topic_row[2], "serialization_format": topic_row[3],
                               "offered_qos_profiles": topic_row[4]},
            "message_count": count}],
        "compression_format": "",
        "compression_mode": "",
        "relative_file_paths": [db_name],
        "files": [{"path": db_name, "starting_time": start(), "duration": duration(), "message_count": count}]}}


def read_back(db_path: str, expected: list[tuple[int, str]]) -> None:
    """Compare what sqlite reads from the written bag with what was recovered (timestamp, payload hash)."""
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = con.execute("SELECT timestamp, data FROM messages ORDER BY timestamp, id")
        n = 0
        for n, (ts, data) in enumerate(rows, 1):
            if n > len(expected) or (ts, hashlib.sha256(data).hexdigest()) != expected[n - 1]:
                raise DemoBagError(f"read-back: message {n} of the written bag differs from the recovered one")
        if n != len(expected):
            raise DemoBagError(f"read-back: {n} messages in the written bag, {len(expected)} recovered")
        if con.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise DemoBagError("read-back: sqlite quick_check failed")
    finally:
        con.close()


def cut(src: str, out_dir: str, window: Window, *, topic="/iv_points", frame_id="seyond", name="falcon_demo",
        member="falcon_test.zst", inner="falcon_test_second_dark_0.db3", back_mb=256, reorder=50,
        manifest="", force=False) -> dict:
    Recover, byte_stream = recovery()
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()) and not force:
        raise DemoBagError(f"{out} exists and is not empty (use --force to replace it)")
    made_dir = not out.exists()
    out.mkdir(parents=True, exist_ok=True)
    db_name = f"{name}_0.db3"
    db_path = str(out / db_name)
    meta_path = str(out / "metadata.yaml")
    for stale in (db_path, meta_path, db_path + "-journal"):
        if os.path.exists(stale):
            os.remove(stale)

    t0, cpu0 = time.time(), time.process_time()
    stats = {"bytes": 0, "other_topics": 0, "duplicates": 0, "order_violations": 0, "next_progress": 1 << 30}
    dst = None
    try:
        chunks = byte_stream(src, member, inner)
        first = next(chunks, None)
        if first is None:
            raise DemoBagError("the source holds no data")
        sch = read_source_schema(first[:PREFIX_BYTES], topic)
        topic_row = sch["topic_row"]
        rec = Recover(frame_id, back_mb)

        dst = sqlite3.connect(db_path)
        dst.execute("PRAGMA synchronous=OFF")
        for sql in sch["ddl"]:
            dst.execute(sql)
        if sch["schema_rows"]:
            dst.executemany(f"INSERT INTO schema VALUES ({','.join('?' * len(sch['schema_rows'][0]))})",
                            sch["schema_rows"])
        dst.execute("INSERT INTO topics VALUES (?, ?, ?, ?, ?)", topic_row)

        kept: list[tuple[int, str]] = []                 # (timestamp, sha256 of the payload) as recovered
        rows_tsv: list[str] = []
        first_index = None
        gap = 0.0
        frames = ordered_frames(_chain(first, chunks), rec, topic_row[0], reorder, stats)
        for index, ts, data in frames:
            if rec.lost:
                raise DemoBagError(f"{rec.lost} message(s) could not be recovered before frame {index}: the frame "
                                   "numbers would not match the detector records; raise --back or check the source")
            if window.t0 is None:
                window.t0 = ts
            if window.past(index, ts):
                break
            if not window.contains(index, ts):
                continue
            if first_index is None:
                first_index = index
            digest = hashlib.sha256(data).hexdigest()
            if kept:
                gap = max(gap, (ts - kept[-1][0]) / 1e9)
            kept.append((ts, digest))
            stamp, fid, width, step = header_info(data)
            if fid != frame_id or step <= 0 or len(data) < width * step:
                raise DemoBagError(f"frame {index}: unexpected PointCloud2 header (frame_id {fid!r}, "
                                   f"width {width}, point_step {step}, {len(data)} bytes)")
            dst.execute("INSERT INTO messages (id, topic_id, timestamp, data) VALUES (?, ?, ?, ?)",
                        (len(kept), topic_row[0], ts, data))
            rows_tsv.append(f"{index}\t{ts}\t{stamp}\t{len(data)}\t{digest}")
        frames.close()
        if rec.lost:
            raise DemoBagError(f"{rec.lost} message(s) could not be recovered: the frame numbers would not "
                               "match the detector records; raise --back or check the source")
        if stats["order_violations"]:
            raise DemoBagError(f"{stats['order_violations']} messages came out of order: raise --reorder")
        if not kept:
            raise DemoBagError("the window holds no frames (the stream ends before it, or it is empty)")
        if window.expected() is not None and len(kept) != window.expected():
            raise DemoBagError(f"the window holds {len(kept)} frames, expected {window.expected()}: "
                               "the stream ended before the last frame")
        dst.commit()
        dst.close()
        read_back(db_path, kept)
    except BaseException:
        if dst is not None:
            dst.close()
        for p in (db_path, meta_path, db_path + "-journal"):
            if os.path.exists(p):
                os.remove(p)
        if made_dir:
            shutil.rmtree(out, ignore_errors=True)
        raise
    first_ns, last_ns = kept[0][0], kept[-1][0]
    with open(meta_path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(metadata_dict(db_name, topic_row, len(kept), first_ns, last_ns), fh, sort_keys=False,
                       default_flow_style=False, width=float("inf"))
    if manifest:
        with open(manifest, "w", encoding="utf-8") as fh:
            fh.write(MANIFEST_HEADER + "\n" + "\n".join(rows_tsv) + "\n")
    receipt = {
        "src": src, "out": str(out), "window": window.describe(), "topic": topic, "topic_id": topic_row[0],
        "frames": len(kept), "first_frame": first_index, "last_frame": first_index + len(kept) - 1,
        "first_bag_time_ns": first_ns, "last_bag_time_ns": last_ns, "t0_bag_time_ns": window.t0,
        "first_s": round((first_ns - window.t0) / 1e9, 4), "last_s": round((last_ns - window.t0) / 1e9, 4),
        "max_gap_s": round(gap, 4), "duplicates": stats["duplicates"], "other_topic_messages_skipped":
        stats["other_topics"], "recovered": rec.kept, "lost": rec.lost, "found": rec.found,
        "bytes_streamed": stats["bytes"], "wall_s": round(time.time() - t0, 1),
        "cpu_s": round(time.process_time() - cpu0, 1),
        "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "files": {n: {"bytes": os.path.getsize(out / n), "sha256": sha256_file(str(out / n))}
                  for n in (db_name, "metadata.yaml")}}
    return receipt


def _chain(first, rest):
    yield first
    yield from rest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="Yandex Disk link, falcon_test.zst, or a rosbag2 .db3 split")
    ap.add_argument("out_dir", help="bag directory to create (<name>_0.db3 and metadata.yaml)")
    ap.add_argument("--first-frame", type=int, help="first frame kept (inclusive, 0-based, by receive time)")
    ap.add_argument("--last-frame", type=int, help="last frame kept (inclusive)")
    ap.add_argument("--start-s", type=float, help="receive time after the first message, seconds (inclusive)")
    ap.add_argument("--end-s", type=float, help="receive time after the first message, seconds (exclusive)")
    ap.add_argument("--name", default="falcon_demo", help="bag file name stem (default falcon_demo)")
    ap.add_argument("--manifest", default="", help="write frame, receive time, header stamp, bytes, sha256 per frame")
    ap.add_argument("--receipt", default="", help="write the JSON summary to this file")
    ap.add_argument("--member", default="falcon_test.zst", help="archive file when SRC is a Yandex Disk folder")
    ap.add_argument("--inner", default="falcon_test_second_dark_0.db3", help="split file inside the archive")
    ap.add_argument("--topic", default="/iv_points")
    ap.add_argument("--frame-id", default="seyond")
    ap.add_argument("--back", type=int, default=256, help="MB kept behind the read position (Recover)")
    ap.add_argument("--reorder", type=int, default=50, help="messages held back for timestamp ordering")
    ap.add_argument("--force", action="store_true", help="replace a non-empty OUT_DIR")
    a = ap.parse_args(argv)
    try:
        window = Window(a.first_frame, a.last_frame, a.start_s, a.end_s)
        receipt = cut(a.src, a.out_dir, window, topic=a.topic, frame_id=a.frame_id, name=a.name, member=a.member,
                      inner=a.inner, back_mb=a.back, reorder=a.reorder, manifest=a.manifest, force=a.force)
    except DemoBagError as exc:
        print(f"make_falcon_demo_bag: {exc}", file=sys.stderr)
        return 1
    text = json.dumps(receipt, indent=1)
    if a.receipt:
        Path(a.receipt).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
