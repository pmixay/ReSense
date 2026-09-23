#!/usr/bin/env python3
"""Write a small ROS 2 bag of synthetic tunnel frames — the dataset-free input for the ROS smoke test.

    python scripts/make_smoke_bag.py /tmp/smoke_bag [--clear 15] [--obstacle 25] [--distance 60]
    python scripts/make_smoke_bag.py /tmp/smoke_bag2 --topic /sensing/lidar/hesai128/pointcloud \
        --frame-id lidar_livox --distance 45      # the organizers' other (topic, frame) pair

Frames 0..clear-1 are an empty synthetic round tunnel (resense.synthetic.synthetic_tunnel_frame);
the next ``obstacle`` frames contain a person (0.4 x 0.5 x 1.7 m) standing on the track at
``distance`` m. The bag mirrors the organizers' recordings so that every reader we have agrees
with it: topic ``/lidar_points``, ``frame_id hesai_lidar``, fields ``x y z intensity ring
timestamp`` (point_step 26) with empty ``(0,0,0)`` slots like the dual-return layout, 10 Hz,
sqlite3 storage (schema 3, "humble") and ``metadata.yaml`` version 5 — the exact layout read
from ``roundT_doubleT``. ``ros2 bag play`` (Humble), ``resense info`` and ``resense run --bag``
all read it. Used by ``scripts/smoke_test.sh`` inside the Docker image in CI.

Needs open3d (ray casting) and rosbags (CDR serialisation): ``pip install -e ".[dev]"``.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

import numpy as np
import yaml

from resense.config import SensorConfig
from resense.frame import axis_matrix
from resense.sensor import RING_ELEVATION_DEG

TOPIC = "/lidar_points"
FRAME_ID = "hesai_lidar"
MSGTYPE = "sensor_msgs/msg/PointCloud2"
# the QoS string rosbag2 Humble wrote into the organizers' bags (reliable, keep last 10, volatile)
QOS = ("- history: 1\n  depth: 10\n  reliability: 1\n  durability: 2\n  deadline:\n    sec: 9223372036\n"
       "    nsec: 854775807\n  lifespan:\n    sec: 9223372036\n    nsec: 854775807\n  liveliness: 1\n"
       "  liveliness_lease_duration:\n    sec: 9223372036\n    nsec: 854775807\n"
       "  avoid_ros_namespace_conventions: false")
POINT_DTYPE = np.dtype({"names": ["x", "y", "z", "intensity", "ring", "timestamp"],
                        "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"],
                        "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26})
PF_FLOAT32, PF_UINT16, PF_FLOAT64 = 7, 4, 8


def build_frames(n_clear: int, n_obstacle: int, distance: float, seed: int):
    """Yield (xyz_sensor, intensity, ring) per frame; a fresh noise draw per frame."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    R = axis_matrix(SensorConfig())            # p_vehicle = R @ p_sensor  =>  rows: p_sensor = p_vehicle @ R
    person = ObstacleSpec(kind="person", size=(0.4, 0.5, 1.7), distance=distance, lateral=0.0, reflectivity=60.0)
    for i in range(n_clear + n_obstacle):
        specs = [] if i < n_clear else [person]
        frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(seed + i), specs=specs)
        xyz_v = frame.xyz
        el = np.degrees(np.arctan2(xyz_v[:, 2], np.hypot(xyz_v[:, 0], xyz_v[:, 1])))
        ring = np.abs(el[:, None] - RING_ELEVATION_DEG[None, :]).argmin(axis=1).astype(np.uint16)
        yield (xyz_v @ R).astype(np.float32), frame.intensity.astype(np.float32), ring


def make_message(ts, xyz_s, intensity, ring, stamp_ns: int, sensor_time: float, rng):
    n = xyz_s.shape[0]
    n_empty = n // 10                          # dual-return slots without a return, like the real bags
    pts = np.zeros(n + n_empty, dtype=POINT_DTYPE)
    order = rng.permutation(n + n_empty)
    filled = order[:n]
    pts["x"][filled], pts["y"][filled], pts["z"][filled] = xyz_s[:, 0], xyz_s[:, 1], xyz_s[:, 2]
    pts["intensity"][filled] = intensity
    pts["ring"][filled] = ring
    pts["timestamp"][:] = sensor_time
    T = ts.types
    fields = [T["sensor_msgs/msg/PointField"](name=nm, offset=off, datatype=dt, count=1)
              for nm, off, dt in (("x", 0, PF_FLOAT32), ("y", 4, PF_FLOAT32), ("z", 8, PF_FLOAT32),
                                  ("intensity", 12, PF_FLOAT32), ("ring", 16, PF_UINT16),
                                  ("timestamp", 18, PF_FLOAT64))]
    header = T["std_msgs/msg/Header"](
        stamp=T["builtin_interfaces/msg/Time"](sec=int(stamp_ns // 1_000_000_000),
                                               nanosec=int(stamp_ns % 1_000_000_000)),
        frame_id=FRAME_ID)
    msg = T[MSGTYPE](header=header, height=1, width=pts.size, fields=fields, is_bigendian=False,
                     point_step=POINT_DTYPE.itemsize, row_step=POINT_DTYPE.itemsize * pts.size,
                     data=np.frombuffer(pts.tobytes(), dtype=np.uint8), is_dense=False)
    return ts.serialize_cdr(msg, MSGTYPE)


def write_bag(path: str, messages, t0_ns: int, period_ns: int) -> dict:
    """sqlite3 storage + metadata.yaml exactly as rosbag2 Humble writes them."""
    name = os.path.basename(os.path.normpath(path))
    os.makedirs(path, exist_ok=True)
    db_name = f"{name}_0.db3"
    db_path = os.path.join(path, db_name)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    con.executescript(
        "CREATE TABLE schema(schema_version INTEGER PRIMARY KEY,ros_distro TEXT NOT NULL);"
        "CREATE TABLE metadata(id INTEGER PRIMARY KEY,metadata_version INTEGER NOT NULL,metadata TEXT NOT NULL);"
        "CREATE TABLE topics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,"
        "serialization_format TEXT NOT NULL,offered_qos_profiles TEXT NOT NULL);"
        "CREATE TABLE messages(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL,timestamp INTEGER NOT NULL,"
        " data BLOB NOT NULL);"
        "CREATE INDEX timestamp_idx ON messages (timestamp ASC);")
    con.execute("INSERT INTO schema VALUES (3, 'humble')")
    con.execute("INSERT INTO topics VALUES (1, ?, ?, 'cdr', ?)", (TOPIC, MSGTYPE, QOS))
    count = 0
    last_ns = t0_ns
    for i, data in enumerate(messages):
        last_ns = t0_ns + i * period_ns
        con.execute("INSERT INTO messages VALUES (?, 1, ?, ?)", (i + 1, last_ns, sqlite3.Binary(data)))
        count += 1
    con.commit()
    con.close()
    duration = last_ns - t0_ns
    meta = {"rosbag2_bagfile_information": {
        "version": 5, "storage_identifier": "sqlite3",
        "duration": {"nanoseconds": int(duration)},
        "starting_time": {"nanoseconds_since_epoch": int(t0_ns)},
        "message_count": count,
        "topics_with_message_count": [{
            "topic_metadata": {"name": TOPIC, "type": MSGTYPE, "serialization_format": "cdr",
                               "offered_qos_profiles": QOS},
            "message_count": count}],
        "compression_format": "", "compression_mode": "",
        "relative_file_paths": [db_name],
        "files": [{"path": db_name, "starting_time": {"nanoseconds_since_epoch": int(t0_ns)},
                   "duration": {"nanoseconds": int(duration)}, "message_count": count}],
    }}
    with open(os.path.join(path, "metadata.yaml"), "w", encoding="utf-8") as fh:
        yaml.safe_dump(meta, fh, sort_keys=False, default_flow_style=False)
    return meta


def main(argv=None) -> int:
    global TOPIC, FRAME_ID
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out", help="bag directory to create (its basename names the .db3 file)")
    p.add_argument("--clear", type=int, default=15, help="leading frames of empty tunnel (default 15)")
    p.add_argument("--obstacle", type=int, default=25, help="frames with the person on the track (default 25)")
    p.add_argument("--distance", type=float, default=60.0, help="m, where the person stands (default 60)")
    p.add_argument("--seed", type=int, default=100)
    p.add_argument("--topic", default=TOPIC, help=f"topic name (default {TOPIC}; the organizers also use "
                                                  "/sensing/lidar/hesai128/pointcloud)")
    p.add_argument("--frame-id", default=FRAME_ID, help=f"header frame_id (default {FRAME_ID}; or lidar_livox)")
    a = p.parse_args(argv)
    TOPIC, FRAME_ID = a.topic, a.frame_id

    from rosbags.typesys import Stores, get_typestore
    ts = get_typestore(Stores.ROS2_HUMBLE)
    rng = np.random.default_rng(a.seed)
    t0_ns = 1_700_000_000 * 1_000_000_000          # an arbitrary but sane bag clock
    period_ns = 100_000_000                        # 10 Hz
    sensor_t0 = 946_684_800.0                      # the sensor's unsynchronised year-2000 epoch, as in the bags

    def gen():
        for i, (xyz_s, inten, ring) in enumerate(build_frames(a.clear, a.obstacle, a.distance, a.seed)):
            yield make_message(ts, xyz_s, inten, ring, t0_ns + i * period_ns, sensor_t0 + 0.1 * i, rng)

    meta = write_bag(a.out, gen(), t0_ns, period_ns)
    info = meta["rosbag2_bagfile_information"]
    print(f"wrote {a.out}: {info['message_count']} frames ({a.clear} clear + {a.obstacle} with a person at "
          f"{a.distance:.0f} m), {info['duration']['nanoseconds'] / 1e9:.1f} s, topic {TOPIC}, frame_id {FRAME_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
