"""Retained raw messages must remain playable, with a real SQLite schema row."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3

import yaml


def test_subset_preserves_schema_and_exact_cdr_with_subset_metadata(tmp_path):
    script = Path(__file__).resolve().parents[1] / "docs/evidence/n2_falcon_2026-10-18/retain_playback_subset.py"
    spec = importlib.util.spec_from_file_location("retained_falcon", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, output = tmp_path / "source", tmp_path / "subset"
    source.mkdir()
    connection = sqlite3.connect(source / "falcon_test_second_dark_0.db3")
    connection.executescript("""
        CREATE TABLE schema(schema_version INTEGER PRIMARY KEY, ros_distro TEXT NOT NULL);
        INSERT INTO schema VALUES(3, 'humble');
        CREATE TABLE metadata(id INTEGER PRIMARY KEY, metadata_version INTEGER NOT NULL, metadata TEXT NOT NULL);
        CREATE TABLE topics(id INTEGER PRIMARY KEY, name TEXT, type TEXT, serialization_format TEXT, offered_qos_profiles TEXT);
        INSERT INTO topics VALUES(3, '/iv_points', 'sensor_msgs/msg/PointCloud2', 'cdr', '[]');
        CREATE TABLE messages(id INTEGER PRIMARY KEY, topic_id INTEGER, timestamp INTEGER, data BLOB);
        CREATE INDEX timestamp_idx ON messages(timestamp);
    """)
    messages = [(i + 11, 3, 1000000000 + i * 100000000, bytes([i]) * 5) for i in range(101)]
    connection.executemany("INSERT INTO messages VALUES(?,?,?,?)", messages)
    connection.commit()
    connection.close()
    topic = {"name": "/iv_points", "type": "sensor_msgs/msg/PointCloud2", "serialization_format": "cdr"}
    document = {"rosbag2_bagfile_information": {
        "version": 5, "storage_identifier": "sqlite3", "message_count": 101,
        "topics_with_message_count": [{"topic_metadata": topic, "message_count": 101}],
    }}
    (source / "metadata.yaml").write_text(yaml.safe_dump(document))
    receipt_path = tmp_path / "receipt.json"
    module.retain(source, output, receipt_path)
    with sqlite3.connect(output / "falcon_first100_0.db3") as result:
        assert result.execute("SELECT * FROM schema").fetchall() == [(3, "humble")]
        assert result.execute("SELECT * FROM messages ORDER BY timestamp,id").fetchall() == messages[:100]
        assert result.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    metadata = yaml.safe_load((output / "metadata.yaml").read_text())["rosbag2_bagfile_information"]
    assert metadata["message_count"] == metadata["files"][0]["message_count"] == 100
    assert metadata["duration"]["nanoseconds"] == messages[99][2] - messages[0][2]
    receipt = json.loads(receipt_path.read_text())
    assert receipt["storage_schema_preserved"]
    assert receipt["raw_cdr_sha256"] == [hashlib.sha256(row[3]).hexdigest() for row in messages[:100]]
