#!/usr/bin/env python3
"""Rebuild a ROS 2 bag from cached real frames (``scripts/cache_frames.py --int16 --stamps``).

For replaying the organizers' recordings through the real node (``ros2 bag play``) when the
original bags are not on disk: same topic, ``frame_id``, PointCloud2 layout (``point_step`` 26,
x y z intensity float32, ring uint16, timestamp float64, empty (0,0,0) slots) and the bag
receive times of the original; the coordinates carry the cache's 5 mm quantisation and the
header stamps are the unsynchronised year-2000 sensor clock of the originals, advanced by the
receive-time intervals.

    python scripts/cache_to_bag.py /data/cache/doubleT_obstacle /tmp/bags/doubleT_obstacle [--limit 120]
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.io import _natural_key  # noqa: E402
from resense.pointcloud import compact_to_xyz, expand_compact16  # noqa: E402

MSGTYPE = "sensor_msgs/msg/PointCloud2"
QOS = ("- history: 1\n  depth: 10\n  reliability: 1\n  durability: 2\n  deadline:\n    sec: 9223372036\n"
       "    nsec: 854775807\n  lifespan:\n    sec: 9223372036\n    nsec: 854775807\n  liveliness: 1\n"
       "  liveliness_lease_duration:\n    sec: 9223372036\n    nsec: 854775807\n"
       "  avoid_ros_namespace_conventions: false")
POINT_DTYPE = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                        "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"],
                        "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
SENSOR_T0 = 946_684_800.0            # the sensors' unsynchronised clock starts in 2000 (DATASET.md)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("cache", help="cache directory of one recording (<bag>_NNNN.npy + <bag>_stamps.json)")
    p.add_argument("out", help="bag directory to create")
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--topic", default=None, help="default: from <cache>/../<bag>_metadata.yaml")
    p.add_argument("--frame-id", default=None, help="default: from the stamps file")
    a = p.parse_args(argv)
    from rosbags.typesys import Stores, get_typestore
    ts = get_typestore(Stores.ROS2_HUMBLE)
    T = ts.types

    st = json.load(open(glob.glob(os.path.join(a.cache, "*_stamps.json"))[0], encoding="utf-8"))
    bag = st["bag"]
    frame_id = a.frame_id or st.get("frame_id") or "hesai_lidar"
    topic = a.topic
    if topic is None:
        meta = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.normpath(a.cache)), f"{bag}_metadata.yaml")))
        topic = meta["rosbag2_bagfile_information"]["topics_with_message_count"][0]["topic_metadata"]["name"]
    files = sorted(glob.glob(os.path.join(a.cache, f"{bag}_*.npy")), key=_natural_key)[a.start:]
    if a.limit:
        files = files[:a.limit]
    stamps = [float(st["stamps"][os.path.basename(f)[len(bag) + 1:-4]]) for f in files]
    rng = np.random.default_rng(0)
    fields = [T["sensor_msgs/msg/PointField"](name=n, offset=o, datatype=d, count=1)
              for n, o, d in (("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4),
                              ("timestamp", 18, 8))]

    name = os.path.basename(os.path.normpath(a.out))
    os.makedirs(a.out, exist_ok=True)
    db_name = f"{name}_0.db3"
    db = os.path.join(a.out, db_name)
    if os.path.exists(db):
        os.remove(db)
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE schema(schema_version INTEGER PRIMARY KEY,ros_distro TEXT NOT NULL);"
        "CREATE TABLE metadata(id INTEGER PRIMARY KEY,metadata_version INTEGER NOT NULL,metadata TEXT NOT NULL);"
        "CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,"
        "serialization_format TEXT NOT NULL,offered_qos_profiles TEXT NOT NULL);"
        "CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL,timestamp INTEGER NOT NULL,"
        " data BLOB NOT NULL);"
        "CREATE INDEX timestamp_idx ON messages (timestamp ASC);")
    con.execute("INSERT INTO schema VALUES (3, 'humble')")
    con.execute("INSERT INTO topics VALUES (1, ?, ?, 'cdr', ?)", (topic, MSGTYPE, QOS))
    for i, (f, t) in enumerate(zip(files, stamps)):
        arr = np.load(f)
        if arr.dtype["x"].kind == "i":
            arr = expand_compact16(arr)
        xyz = compact_to_xyz(arr)
        n = xyz.shape[0]
        pts = np.zeros(n + n // 10, dtype=POINT_DTYPE)           # empty dual-return slots, as recorded,
        k = np.delete(np.arange(pts.size), np.arange(10, pts.size, 11)[: n // 10])   # keeping the scan order
        pts["x"][k], pts["y"][k], pts["z"][k] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        pts["intensity"][k] = arr["intensity"]
        pts["ring"][k] = arr["ring"] & 0x7F
        sensor_t = SENSOR_T0 + (t - stamps[0])
        pts["timestamp"][:] = sensor_t
        header = T["std_msgs/msg/Header"](stamp=T["builtin_interfaces/msg/Time"](
            sec=int(sensor_t), nanosec=int(round((sensor_t - int(sensor_t)) * 1e9)) % 1_000_000_000), frame_id=frame_id)
        msg = T[MSGTYPE](header=header, height=1, width=pts.size, fields=fields, is_bigendian=False,
                         point_step=26, row_step=26 * pts.size, data=np.frombuffer(pts.tobytes(), dtype=np.uint8),
                         is_dense=False)
        con.execute("INSERT INTO messages VALUES (?, 1, ?, ?)",
                    (i + 1, int(round(t * 1e9)), sqlite3.Binary(ts.serialize_cdr(msg, MSGTYPE))))
    con.commit()
    con.close()
    t0, t1 = int(round(stamps[0] * 1e9)), int(round(stamps[-1] * 1e9))
    info = {"version": 5, "storage_identifier": "sqlite3", "duration": {"nanoseconds": t1 - t0},
            "starting_time": {"nanoseconds_since_epoch": t0}, "message_count": len(files),
            "topics_with_message_count": [{"topic_metadata": {"name": topic, "type": MSGTYPE,
                                                              "serialization_format": "cdr",
                                                              "offered_qos_profiles": QOS},
                                           "message_count": len(files)}],
            "compression_format": "", "compression_mode": "", "relative_file_paths": [db_name],
            "files": [{"path": db_name, "starting_time": {"nanoseconds_since_epoch": t0},
                       "duration": {"nanoseconds": t1 - t0}, "message_count": len(files)}]}
    with open(os.path.join(a.out, "metadata.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump({"rosbag2_bagfile_information": info}, fh, sort_keys=False, default_flow_style=False)
    print(f"wrote {a.out}: {len(files)} frames of {bag} ({(t1 - t0) / 1e9:.1f} s), topic {topic}, frame_id {frame_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
