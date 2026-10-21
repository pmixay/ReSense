"""Recover an original-CDR demo window while hashing the complete organizer archive.

Run with the project's rosbags/zstandard environment. Output data stays outside git.
The complete raw SQLite digest is compared with the independently recorded intake.
"""
import argparse
import hashlib
import heapq
import json
from pathlib import Path
import sqlite3
import sys
import tarfile

import yaml
import zstandard

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from stream_falcon import Recover  # noqa: E402
from unpack_dataset import open_zst_stream  # noqa: E402

ARCHIVE_SHA = "90dea27d8636bcb2e5cdddf9bc15add3eae0e05196c2b3de959482da7e505611"
RAW_SHA = "5a1df8dd6040a2196386cf686356dccc8dcb5e90a3c57a1a0df20d2eb7b2ce31"


class HashedReader:
    def __init__(self, source):
        self.source = source
        self.digest = hashlib.sha256()
        self.size = 0

    def read(self, size=-1):
        data = self.source.read(size)
        self.digest.update(data)
        self.size += len(data)
        return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--start", type=float, default=280)
    parser.add_argument("--end", type=float, default=330)
    args = parser.parse_args()
    assert 0 <= args.start < args.end
    args.output.mkdir(parents=True, exist_ok=False)
    db_path = args.output / "falcon_person_0.db3"
    db = sqlite3.connect(db_path)
    db.executescript("""
        CREATE TABLE schema(schema_version INTEGER PRIMARY KEY, ros_distro TEXT NOT NULL);
        INSERT INTO schema VALUES(3, 'humble');
        CREATE TABLE metadata(id INTEGER PRIMARY KEY, metadata_version INTEGER NOT NULL, metadata TEXT NOT NULL);
        CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL,
          serialization_format TEXT NOT NULL, offered_qos_profiles TEXT NOT NULL);
        CREATE TABLE messages(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL,
          timestamp INTEGER NOT NULL, data BLOB NOT NULL);
        CREATE INDEX timestamp_idx ON messages(timestamp);
    """)
    original = yaml.safe_load((ROOT / "data/k1-k2/raw/falcon_test_second_dark/metadata.yaml").read_text())
    info = original["rosbag2_bagfile_information"]
    topic = next(t for t in info["topics_with_message_count"] if t["topic_metadata"]["name"] == "/iv_points")
    tm = topic["topic_metadata"]
    db.execute("INSERT INTO topics VALUES(3,?,?,?,?)", (tm["name"], tm["type"], tm["serialization_format"], tm["offered_qos_profiles"]))
    source_url = "https://disk.yandex.ru/d/SfBeRHbs8bNJAQ"
    raw = HashedReader(open_zst_stream(source_url, "falcon_test.zst"))
    stream = zstandard.ZstdDecompressor().stream_reader(raw)
    recovered, digest, raw_size = Recover("seyond", 256), hashlib.sha256(), 0
    heap, seen, selected = [], set(), []
    first = None
    index = 0
    previous = None
    max_gap = 0

    def emit(force=False):
        nonlocal first, index, previous, max_gap
        while heap and (force or len(heap) > 50):
            timestamp, tid, payload = heapq.heappop(heap)
            if first is None:
                first = timestamp
            if previous is not None:
                assert timestamp > previous
                max_gap = max(max_gap, timestamp - previous)
            previous = timestamp
            elapsed = (timestamp - first) / 1e9
            if args.start <= elapsed < args.end:
                db.execute("INSERT INTO messages(topic_id,timestamp,data) VALUES(?,?,?)", (tid, timestamp, payload))
                selected.append({"source_frame": index, "bag_timestamp_ns": timestamp,
                                 "source_elapsed_s": elapsed, "cdr_sha256": hashlib.sha256(payload).hexdigest()})
            index += 1

    def accept(rows):
        for tid, timestamp, payload in rows:
            if tid == 3:
                assert timestamp not in seen, "duplicate timestamp"
                seen.add(timestamp)
                heapq.heappush(heap, (timestamp, tid, payload))
        emit()

    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for member in archive:
            if Path(member.name).name != "falcon_test_second_dark_0.db3":
                continue
            with archive.extractfile(member) as source:
                while chunk := source.read(64 << 20):
                    digest.update(chunk)
                    raw_size += len(chunk)
                    accept(recovered.feed(chunk))
                    if raw_size % (512 << 20) == 0:
                        print(f"read {raw_size / 1e9:.2f} GB; frames {index}; selected {len(selected)}", flush=True)
            accept(recovered.feed(b"", final=True))
            emit(True)
    while stream.read(1 << 20):
        pass
    while raw.read(1 << 20):
        pass
    assert raw.digest.hexdigest() == ARCHIVE_SHA, "archive digest mismatch"
    assert digest.hexdigest() == RAW_SHA, "raw SQLite digest mismatch"
    assert index == 4443 and recovered.lost == 0 and max_gap < 200_000_000
    assert 490 <= len(selected) <= 510
    db.commit()
    assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    actual = [(ts, hashlib.sha256(blob).hexdigest()) for ts, blob in db.execute("SELECT timestamp,data FROM messages ORDER BY timestamp")]
    assert actual == [(r["bag_timestamp_ns"], r["cdr_sha256"]) for r in selected]
    db.close()
    info.update(message_count=len(selected),
                starting_time={"nanoseconds_since_epoch": selected[0]["bag_timestamp_ns"]},
                duration={"nanoseconds": selected[-1]["bag_timestamp_ns"] - selected[0]["bag_timestamp_ns"]},
                relative_file_paths=[db_path.name])
    topic["message_count"] = len(selected)
    info["topics_with_message_count"] = [topic]
    info["files"] = [{"path": db_path.name, "starting_time": info["starting_time"],
                      "duration": info["duration"], "message_count": len(selected)}]
    meta = args.output / "metadata.yaml"
    meta.write_text(yaml.safe_dump(original, sort_keys=False))
    hashes = {}
    for path in (db_path, meta):
        with path.open("rb") as file:
            hashes[path.name] = hashlib.file_digest(file, "sha256").hexdigest()
    (args.output / "SHA256SUMS").write_text("".join(f"{sha}  {name}\n" for name, sha in hashes.items()))
    receipt = {"source": source_url, "archive_sha256": raw.digest.hexdigest(), "archive_bytes": raw.size,
               "raw_sha256": digest.hexdigest(), "raw_bytes": raw_size, "source_frames": index,
               "recovery_lost": recovered.lost, "source_max_gap_s": max_gap / 1e9,
               "window_s": [args.start, args.end], "frames": len(selected), "files": hashes,
               "output": str(args.output.resolve()), "rows": selected}
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "rows"}, indent=2))


if __name__ == "__main__":
    main()
