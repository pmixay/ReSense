"""Retain first 100 original Falcon CDR frames for same-node DDS validation."""

import hashlib
import json
from pathlib import Path
import sqlite3

import yaml


def main():
    source = Path("/home/resense/data/raw/falcon_test_second_dark")
    output = Path("/home/resense/data/n2/falcon_first100")
    output.mkdir(exist_ok=False)
    original = source / "falcon_test_second_dark_0.db3"
    target = output / "falcon_first100_0.db3"
    reader = sqlite3.connect(f"file:{original}?mode=ro", uri=True)
    writer = sqlite3.connect(target)
    for (sql,) in reader.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        writer.execute(sql)
    topic = reader.execute("SELECT * FROM topics WHERE name='/iv_points'").fetchone()
    writer.execute(
        "INSERT INTO topics VALUES(" + ",".join("?" for _ in topic) + ")", topic
    )
    rows = reader.execute(
        "SELECT * FROM messages WHERE topic_id=? ORDER BY timestamp,id LIMIT 100",
        (topic[0],),
    )
    stamps, raw_hashes = [], []
    for row in rows:
        writer.execute(
            "INSERT INTO messages VALUES(" + ",".join("?" for _ in row) + ")", row
        )
        stamps.append(row[2])
        raw_hashes.append(hashlib.sha256(row[3]).hexdigest())
    assert len(stamps) == 100
    for (sql,) in reader.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"
    ):
        writer.execute(sql)
    writer.commit()
    assert writer.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    reader.close()
    writer.close()
    document = yaml.safe_load((source / "metadata.yaml").read_text())
    meta = document["rosbag2_bagfile_information"]
    meta["message_count"] = 100
    meta["duration"] = {"nanoseconds": stamps[-1] - stamps[0]}
    meta["starting_time"] = {"nanoseconds_since_epoch": stamps[0]}
    meta["relative_file_paths"] = [target.name]
    meta["topics_with_message_count"] = [
        item
        for item in meta["topics_with_message_count"]
        if item["topic_metadata"]["name"] == "/iv_points"
    ]
    meta["topics_with_message_count"][0]["message_count"] = 100
    meta["files"] = [
        {
            "path": target.name,
            "starting_time": meta["starting_time"],
            "duration": meta["duration"],
            "message_count": 100,
        }
    ]
    (output / "metadata.yaml").write_text(yaml.safe_dump(document, sort_keys=False))
    checksum = hashlib.sha256()
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            checksum.update(block)
    receipt = {
        "original": str(original),
        "subset": str(output),
        "frames": 100,
        "indices": [0, 99],
        "raw_cdr_sha256": raw_hashes,
        "bytes": target.stat().st_size,
        "db3_sha256": checksum.hexdigest(),
        "metadata_sha256": hashlib.sha256(
            (output / "metadata.yaml").read_bytes()
        ).hexdigest(),
        "sqlite_integrity": "ok",
        "preserved": [
            "raw CDR",
            "header stamps",
            "bag timestamps",
            "field layout",
            "topic",
            "frame_id",
        ],
    }
    (Path(__file__).resolve().parent / "playback_subset_receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )
    print(
        json.dumps(
            {key: value for key, value in receipt.items() if key != "raw_cdr_sha256"}
        )
    )


if __name__ == "__main__":
    main()
