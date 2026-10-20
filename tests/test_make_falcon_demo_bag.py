"""scripts/make_falcon_demo_bag.py on a small synthetic rosbag2 split: no data, no network.

The split is built here with sqlite3 in the rosbag2 layout (tables schema / metadata / topics / messages,
7 topics as in the Falcon recording), holding PointCloud2 messages in the real CDR layout (48-byte points,
frame_id ``seyond``) of just over 1 MiB each, as the recovery code expects of a Falcon message, inserted
slightly out of order, plus a message on another topic and a PointCloud2 on a second topic id.

The recovery code (``stream_falcon.Recover``) lives under ``docs/evidence/extended_data_2026-10-17/scripts``,
which the runtime image does not carry (``.dockerignore`` leaves ``docs/`` out). The tests that run it
carry ``realdata`` on that directory: they run on a checkout (the ``pytest`` job) and are deselected, not
skipped, in the image. The tests of the pure parts run everywhere.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import sys
import random
import sqlite3
import struct
import tarfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("resense_make_falcon_demo_bag", ROOT / "scripts" / "make_falcon_demo_bag.py")
assert SPEC is not None and SPEC.loader is not None
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)

needs_recovery = pytest.mark.realdata(str(ROOT / "docs/evidence/extended_data_2026-10-17/scripts"))

QOS = ("- history: 1\n  depth: 10\n  reliability: 1\n  durability: 2\n  deadline:\n    sec: 9223372036\n"
       "    nsec: 854775807\n  lifespan:\n    sec: 9223372036\n    nsec: 854775807\n  liveliness: 1\n"
       "  liveliness_lease_duration:\n    sec: 9223372036\n    nsec: 854775807\n"
       "  avoid_ros_namespace_conventions: false")
TOPICS = [(1, "/rosout", "rcl_interfaces/msg/Log", "cdr", "- history: 1\n  depth: 1000"),
          (2, "/parameter_events", "rcl_interfaces/msg/ParameterEvent", "cdr", "- history: 1\n  depth: 1000"),
          (3, "/iv_points", "sensor_msgs/msg/PointCloud2", "cdr", QOS),
          (4, "/other_points", "sensor_msgs/msg/PointCloud2", "cdr", QOS)]
FIELDS = [("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("timestamp", 16, 8), ("intensity", 24, 7), ("flags", 28, 2),
          ("elongation", 29, 2), ("scan_id", 30, 4), ("scan_idx", 32, 4), ("is_2nd_return", 34, 2)]
T0 = 1_791_508_466_987_400_000          # a receive time of the real recording's size (8-byte sqlite integer)
N_FRAMES = 12


def cdr_pointcloud2(sec: int, nsec: int, frame_id: str, n_points: int, seed: int) -> bytes:
    """A little-endian CDR sensor_msgs/msg/PointCloud2 with the Falcon field layout."""
    out = bytearray(b"\x00\x01\x00\x00")

    def align(n):
        out.extend(b"\0" * (-(len(out) - 4) % n))

    def u32(v):
        align(4)
        out.extend(struct.pack("<I", v))

    def string(text):
        raw = text.encode() + b"\0"
        u32(len(raw))
        out.extend(raw)

    align(4)
    out.extend(struct.pack("<i", sec))
    u32(nsec)
    string(frame_id)
    u32(1)
    u32(n_points)
    u32(len(FIELDS))
    for name, offset, datatype in FIELDS:
        string(name)
        u32(offset)
        out.append(datatype)
        u32(1)
    out.append(0)
    u32(48)
    u32(48 * n_points)
    u32(48 * n_points)
    out.extend(random.Random(seed).randbytes(48 * n_points))
    out.append(1)
    align(4)
    return bytes(out)


def make_split(path: Path) -> list[tuple[int, bytes]]:
    """Write the synthetic split; return its /iv_points messages (receive time, payload) in time order."""
    frames = []
    for i in range(N_FRAMES):
        ts = T0 + i * 100_000_000 + (i * 7919) % 5_000_000
        frames.append((ts, cdr_pointcloud2(3105 + i // 10, (i % 10) * 100_000_000 + 392_500_000, "seyond",
                                           22_200 + 7 * i, seed=i)))
    con = sqlite3.connect(path)
    con.executescript(
        "CREATE TABLE schema(schema_version INTEGER PRIMARY KEY,ros_distro TEXT NOT NULL);"
        "CREATE TABLE metadata(id INTEGER PRIMARY KEY,metadata_version INTEGER NOT NULL,metadata TEXT NOT NULL);"
        "CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,"
        "serialization_format TEXT NOT NULL,offered_qos_profiles TEXT NOT NULL);"
        "CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL,timestamp INTEGER NOT NULL,"
        " data BLOB NOT NULL);"
        "CREATE INDEX timestamp_idx ON messages (timestamp ASC);")
    con.execute("INSERT INTO schema VALUES (3, 'humble')")
    con.executemany("INSERT INTO topics VALUES (?, ?, ?, ?, ?)", TOPICS)
    order = list(range(N_FRAMES))
    for a in range(0, N_FRAMES - 1, 4):                       # written out of order: 1 0 2 3 | 5 4 6 7 | ...
        order[a], order[a + 1] = order[a + 1], order[a]
    for k, i in enumerate(order):
        con.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (3, ?, ?)", frames[i])
        if k == 3:
            con.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (1, ?, ?)", (T0 + 1, b"log" * 20))
            con.execute("INSERT INTO messages (topic_id, timestamp, data) VALUES (4, ?, ?)",
                        (T0 + 2, cdr_pointcloud2(1, 2, "seyond", 22_300, seed=99)))
    con.commit()
    con.close()
    return frames


@pytest.fixture(scope="module")
def split(tmp_path_factory):
    d = tmp_path_factory.mktemp("split")
    frames = make_split(d / "falcon_test_second_dark_0.db3")
    return d / "falcon_test_second_dark_0.db3", frames


def read_bag(bag: Path):
    con = sqlite3.connect(f"file:{bag / 'falcon_demo_0.db3'}?mode=ro", uri=True)
    try:
        return (list(con.execute("SELECT id, topic_id, timestamp, data FROM messages ORDER BY id")),
                list(con.execute("SELECT * FROM topics")), list(con.execute("SELECT * FROM schema")),
                list(con.execute("SELECT * FROM metadata")), con.execute("PRAGMA quick_check").fetchone()[0])
    finally:
        con.close()


# ---- the parts that need no recovery code -------------------------------------------------------------

def test_header_info_reads_the_pointcloud2_header():
    data = cdr_pointcloud2(3105, 392_500_000, "seyond", 1000, seed=5)
    assert demo.header_info(data) == ("3105.392500000", "seyond", 1000, 48)
    assert demo.header_info(cdr_pointcloud2(-1, 5, "lidar_x", 3, seed=1)) == ("-1.000000005", "lidar_x", 3, 48)


def test_window_by_frame_and_by_time():
    w = demo.Window(first_frame=3, last_frame=5)
    assert [w.contains(i, 0) for i in range(2, 7)] == [False, True, True, True, False]
    assert not w.past(5, 0) and w.past(6, 0) and w.expected() == 3
    t = demo.Window(start_s=1.0, end_s=2.0)
    t.t0 = 1_000
    assert t.expected() is None

    def ns(seconds):
        return 1_000 + int(seconds * 1e9)

    assert [t.contains(0, ns(s)) for s in (0.99, 1.0, 1.5, 1.999, 2.0)] == [False, True, True, True, False]
    assert t.past(0, ns(2.0)) and not t.past(0, ns(1.999))


@pytest.mark.parametrize("kwargs", [{}, {"first_frame": 1}, {"first_frame": 4, "last_frame": 3},
                                    {"first_frame": 0, "last_frame": 3, "start_s": 0.0, "end_s": 1.0},
                                    {"start_s": 2.0, "end_s": 1.0}, {"start_s": 1.0}, {"first_frame": -1, "last_frame": 3}])
def test_window_rejects_unusable_arguments(kwargs):
    with pytest.raises(demo.DemoBagError):
        demo.Window(**kwargs)


def test_schema_and_topic_are_read_from_a_truncated_prefix(tmp_path):
    # the first 1 MiB of a bigger split: the header still counts the pages of the whole file
    src = tmp_path / "s.db3"
    make_split(src)
    assert src.stat().st_size > demo.PREFIX_BYTES
    sch = demo.read_source_schema(src.read_bytes()[:demo.PREFIX_BYTES], "/iv_points")
    assert sch["topic_row"] == TOPICS[2]
    assert sch["schema_rows"] == [(3, "humble")]
    assert [s.split("(")[0] for s in sch["ddl"]] == ["CREATE TABLE schema", "CREATE TABLE metadata",
                                                     "CREATE TABLE topics", "CREATE TABLE messages",
                                                     "CREATE INDEX timestamp_idx ON messages "]
    with pytest.raises(demo.DemoBagError, match="not in the source"):
        demo.read_source_schema(src.read_bytes()[:demo.PREFIX_BYTES], "/missing")
    with pytest.raises(demo.DemoBagError, match="not sensor_msgs/msg/PointCloud2"):
        demo.read_source_schema(src.read_bytes()[:demo.PREFIX_BYTES], "/rosout")


def test_metadata_has_the_rosbag2_version_5_layout():
    meta = demo.metadata_dict("falcon_demo_0.db3", TOPICS[2], 3, 100, 350)
    info = meta["rosbag2_bagfile_information"]
    assert list(info) == ["version", "storage_identifier", "duration", "starting_time", "message_count",
                          "topics_with_message_count", "compression_format", "compression_mode",
                          "relative_file_paths", "files"]
    assert info["version"] == 5 and info["storage_identifier"] == "sqlite3"
    assert info["duration"] == {"nanoseconds": 250} and info["starting_time"] == {"nanoseconds_since_epoch": 100}
    assert info["topics_with_message_count"] == [{"topic_metadata": {
        "name": "/iv_points", "type": "sensor_msgs/msg/PointCloud2", "serialization_format": "cdr",
        "offered_qos_profiles": QOS}, "message_count": 3}]
    assert info["files"] == [{"path": "falcon_demo_0.db3", "starting_time": {"nanoseconds_since_epoch": 100},
                              "duration": {"nanoseconds": 250}, "message_count": 3}]
    # no object is shared between two places: the YAML file would get anchors and aliases
    assert info["starting_time"] is not info["files"][0]["starting_time"]
    assert info["duration"] is not info["files"][0]["duration"]


# ---- the whole tool on the synthetic split (recovery code needed) -------------------------------------

def check_window(out: Path, frames, first: int, last: int, manifest: Path, numbered_from: int | None = None):
    """The bag holds exactly frames first..last, byte for byte, with the source's topic and schema rows.

    ``numbered_from``: the frame number the manifest gives the first frame (the source's own, by default)."""
    base = first if numbered_from is None else numbered_from
    rows, topics, schema, metadata, quick = read_bag(out)
    want = frames[first:last + 1]
    assert quick == "ok" and metadata == [] and schema == [(3, "humble")]
    assert topics == [TOPICS[2]]
    assert [(r[0], r[1], r[2]) for r in rows] == [(k + 1, 3, ts) for k, (ts, _) in enumerate(want)]
    assert [r[3] for r in rows] == [d for _, d in want]                          # payloads byte for byte
    text = (out / "metadata.yaml").read_text()
    assert "&id" not in text and "*id" not in text                                # plain YAML, as the source's
    info = yaml.safe_load(text)["rosbag2_bagfile_information"]
    assert info == demo.metadata_dict("falcon_demo_0.db3", TOPICS[2], len(want), want[0][0], want[-1][0])[
        "rosbag2_bagfile_information"]
    assert info["topics_with_message_count"][0]["topic_metadata"]["offered_qos_profiles"] == QOS
    lines = manifest.read_text().splitlines()
    assert lines[0] == demo.MANIFEST_HEADER and len(lines) == len(want) + 1
    for k, line in enumerate(lines[1:]):
        frame, ts, stamp, size, digest = line.split("\t")
        assert (int(frame), int(ts), int(size), digest) == (base + k, want[k][0], len(want[k][1]),
                                                              hashlib.sha256(want[k][1]).hexdigest())
        assert stamp == demo.header_info(want[k][1])[0]


@needs_recovery
def test_cut_by_frame_is_byte_for_byte(split, tmp_path, capsys):
    path, frames = split
    out = tmp_path / "bag"
    receipt_file = tmp_path / "receipt.json"
    rc = demo.main([str(path), str(out), "--first-frame", "3", "--last-frame", "9", "--manifest",
                    str(tmp_path / "frames.tsv"), "--receipt", str(receipt_file), "--reorder", "3"])
    assert rc == 0
    check_window(out, frames, 3, 9, tmp_path / "frames.tsv")
    assert sorted(p.name for p in out.iterdir()) == ["falcon_demo_0.db3", "metadata.yaml"]
    receipt = json.loads(receipt_file.read_text())
    assert receipt["frames"] == 7 and (receipt["first_frame"], receipt["last_frame"]) == (3, 9)
    assert receipt["lost"] == 0 and receipt["duplicates"] == 0 and receipt["other_topic_messages_skipped"] >= 1
    assert receipt["files"]["metadata.yaml"]["sha256"] == hashlib.sha256((out / "metadata.yaml").read_bytes()).hexdigest()
    assert receipt["files"]["falcon_demo_0.db3"]["bytes"] == (out / "falcon_demo_0.db3").stat().st_size
    assert json.loads(capsys.readouterr().out)["frames"] == 7


@needs_recovery
def test_cut_by_seconds_selects_the_same_frames(split, tmp_path):
    path, frames = split
    by_frame, by_time = tmp_path / "a", tmp_path / "b"
    assert demo.main([str(path), str(by_frame), "--first-frame", "2", "--last-frame", "6"]) == 0
    # frames 2..6 start at (receive time of frame 2) - T0_first; end just before frame 7
    t0 = frames[0][0]
    start, end = (frames[2][0] - t0) / 1e9, (frames[7][0] - t0) / 1e9
    assert demo.main([str(path), str(by_time), "--start-s", repr(start), "--end-s", repr(end)]) == 0
    assert read_bag(by_frame)[0] == read_bag(by_time)[0]
    assert (by_frame / "metadata.yaml").read_bytes() == (by_time / "metadata.yaml").read_bytes()
    assert (by_frame / "falcon_demo_0.db3").read_bytes() == (by_time / "falcon_demo_0.db3").read_bytes()


@needs_recovery
def test_cut_from_the_zst_archive_member(split, tmp_path):
    import zstandard
    path, frames = split
    archive = tmp_path / "falcon_test.zst"
    with open(archive, "wb") as raw, zstandard.ZstdCompressor().stream_writer(raw) as zw:
        with tarfile.open(fileobj=zw, mode="w|") as tar:
            for name, payload in (("falcon_test_second_dark/metadata.yaml", b"rosbag2_bagfile_information: {}\n"),
                                  ("falcon_test_second_dark/falcon_test_second_dark_0.db3", path.read_bytes())):
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                tar.addfile(info, io.BytesIO(payload))
    out = tmp_path / "bag"
    assert demo.main([str(archive), str(out), "--first-frame", "0", "--last-frame", str(N_FRAMES - 1),
                      "--manifest", str(tmp_path / "m.tsv")]) == 0
    check_window(out, frames, 0, N_FRAMES - 1, tmp_path / "m.tsv")


@needs_recovery
def test_a_cut_bag_can_be_cut_again(split, tmp_path):
    """The written bag is a valid split: cutting it reproduces the same messages (a second, independent path)."""
    path, frames = split
    first, second = tmp_path / "first", tmp_path / "second"
    assert demo.main([str(path), str(first), "--first-frame", "1", "--last-frame", "10"]) == 0
    assert demo.main([str(first / "falcon_demo_0.db3"), str(second), "--first-frame", "2", "--last-frame", "5",
                      "--manifest", str(tmp_path / "m.tsv")]) == 0
    check_window(second, frames, 3, 6, tmp_path / "m.tsv", numbered_from=2)


@needs_recovery
@pytest.mark.parametrize("args, message", [
    (["--first-frame", "40", "--last-frame", "50"], "holds no frames"),
    (["--first-frame", "8", "--last-frame", "20"], "expected 13"),
    (["--start-s", "500", "--end-s", "600"], "holds no frames"),
    (["--first-frame", "3"], "must both be given"),
])
def test_a_window_the_source_cannot_fill_fails_and_leaves_nothing(split, tmp_path, capsys, args, message):
    path, _ = split
    out = tmp_path / "bag"
    assert demo.main([str(path), str(out), *args]) == 1
    assert message in capsys.readouterr().err
    assert not out.exists()


@needs_recovery
def test_a_wrong_frame_id_is_an_error_not_an_empty_bag(split, tmp_path, capsys):
    path, _ = split
    assert demo.main([str(path), str(tmp_path / "bag"), "--first-frame", "0", "--last-frame", "1",
                      "--frame-id", "hesai_lidar"]) == 1
    assert "holds no frames" in capsys.readouterr().err


@needs_recovery
def test_an_existing_output_is_kept_unless_forced(split, tmp_path, capsys):
    path, frames = split
    out = tmp_path / "bag"
    out.mkdir()
    (out / "keep.txt").write_text("mine")
    assert demo.main([str(path), str(out), "--first-frame", "0", "--last-frame", "1"]) == 1
    assert "use --force" in capsys.readouterr().err
    assert (out / "keep.txt").read_text() == "mine" and not (out / "falcon_demo_0.db3").exists()
    assert demo.main([str(path), str(out), "--first-frame", "0", "--last-frame", "1", "--force",
                      "--manifest", str(tmp_path / "m.tsv")]) == 0
    check_window(out, frames, 0, 1, tmp_path / "m.tsv")


@needs_recovery
def test_messages_arriving_out_of_order_are_sorted_inside_the_reorder_window(split, tmp_path, monkeypatch, capsys):
    """Small stream chunks make the swapped neighbours of the split arrive in file order, as in the real file.

    ``--reorder 0`` is the positive control: with no look-ahead the swap is released unsorted and refused."""
    path, frames = split
    demo.recovery()
    monkeypatch.setattr(sys.modules["stream_falcon"], "CHUNK", 1 << 20)
    assert demo.main([str(path), str(tmp_path / "none"), "--first-frame", "0", "--last-frame", "11",
                      "--reorder", "0"]) == 1
    assert "came out of order" in capsys.readouterr().err
    out = tmp_path / "bag"
    assert demo.main([str(path), str(out), "--first-frame", "0", "--last-frame", "11", "--reorder", "3",
                      "--manifest", str(tmp_path / "m.tsv")]) == 0
    check_window(out, frames, 0, 11, tmp_path / "m.tsv")
