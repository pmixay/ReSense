#!/usr/bin/env python3
"""Open the cut bag with the pure-Python rosbag2 reader ``rosbags`` and deserialize every message.

    rosbags_check.py BAG_DIR --first-frame A --record l16.jsonl.xz [--out report.json]

This is a reader of the rosbag2 format (``metadata.yaml`` version 5 and the sqlite3 storage) that is independent
of both the cutting script and sqlite3 itself, and it deserializes each CDR message with the ROS 2 Humble message
definitions: the message count, topic, type, start time and duration it reports must equal ``metadata.yaml``, every
message must deserialize to a ``sensor_msgs/msg/PointCloud2`` with ``frame_id`` ``seyond``, 48-byte points and
``width * 48`` bytes of data, receive times must increase, and the header stamp must equal the record's. It is
**not** ``ros2 bag play``: a successful check here does not show that the ROS 2 player opens the bag.
"""
from __future__ import annotations

import argparse
import json
import lzma
import os

import yaml

from rosbags.rosbag2 import Reader
from rosbags.typesys import Stores, get_typestore


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bag")
    ap.add_argument("--first-frame", type=int, required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    with (lzma.open(a.record, "rt") if a.record.endswith(".xz") else open(a.record)) as fh:
        record = [json.loads(line) for line in fh]
    with open(os.path.join(a.bag, "metadata.yaml"), encoding="utf-8") as fh:
        md = yaml.safe_load(fh)["rosbag2_bagfile_information"]
    types = get_typestore(Stores.ROS2_HUMBLE)
    problems: list[str] = []
    prev = None
    n = 0
    with Reader(a.bag) as reader:
        summary = {"message_count": reader.message_count, "duration_ns": reader.duration,
                   "start_time_ns": reader.start_time, "end_time_ns": reader.end_time,
                   "topics": {name: {"msgtype": t.msgtype, "msgcount": t.msgcount}
                              for name, t in reader.topics.items()},
                   "serialization_formats": sorted({c.ext.serialization_format for c in reader.connections}),
                   "metadata_yaml": md}
        for conn, ts, raw in reader.messages():
            msg = types.deserialize_cdr(raw, conn.msgtype)
            frame = a.first_frame + n
            n += 1
            if conn.topic != "/iv_points" or conn.msgtype != "sensor_msgs/msg/PointCloud2":
                problems.append(f"frame {frame}: topic {conn.topic} type {conn.msgtype}")
            if msg.header.frame_id != "seyond" or msg.point_step != 48 or len(msg.data) != msg.width * 48 \
                    or msg.height != 1:
                problems.append(f"frame {frame}: frame_id {msg.header.frame_id!r} point_step {msg.point_step} "
                                f"width {msg.width} data {len(msg.data)}")
            if prev is not None and ts <= prev:
                problems.append(f"frame {frame}: receive time does not increase")
            prev = ts
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            if abs(stamp - record[frame]["stamp"]) > 1e-4 or abs(ts / 1e9 - record[frame]["bag_t"]) > 1e-4:
                problems.append(f"frame {frame}: stamp or receive time differs from the record")
    summary.update(messages_deserialized=n, problems=problems,
                   metadata_consistent=(n == md["message_count"] == summary["message_count"]
                                        and summary["topics"]["/iv_points"]["msgcount"] == n
                                        and summary["start_time_ns"] == md["starting_time"]["nanoseconds_since_epoch"]
                                        and summary["duration_ns"] - md["duration"]["nanoseconds"] in (0, 1)))
    print(json.dumps(summary, indent=1))
    if a.out:
        json.dump(summary, open(a.out, "w"), indent=1)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
