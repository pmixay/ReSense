"""Offline input: ROS 2 bags (via ``rosbags``, no ROS needed) and cached *.npy frames."""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path
from typing import Iterator, Optional

import numpy as np

from resense.config import SensorConfig
from resense.frame import Frame, frame_from_compact
from resense.pointcloud import pointcloud2_to_structured, structured_to_compact


def iter_bag_compact(bag_path: str, topic: Optional[str] = None, every: int = 1,
                     start: int = 0, limit: Optional[int] = None) -> Iterator[tuple]:
    """Yield (index, stamp_s, frame_id, compact_array) for PointCloud2 messages of a bag."""
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore

    ts = get_typestore(Stores.ROS2_HUMBLE)
    with Reader(Path(bag_path)) as reader:
        conns = [c for c in reader.connections if c.msgtype == "sensor_msgs/msg/PointCloud2"
                 and (topic is None or c.topic == topic)]
        if not conns:
            raise RuntimeError(f"no PointCloud2 topic in {bag_path}")
        i = 0
        n_out = 0
        for conn, t, raw in reader.messages(connections=conns):
            if i >= start and (i - start) % every == 0:
                msg = ts.deserialize_cdr(raw, conn.msgtype)
                arr = structured_to_compact(pointcloud2_to_structured(msg))
                yield i, t / 1e9, msg.header.frame_id, arr
                n_out += 1
                if limit is not None and n_out >= limit:
                    return
            i += 1


def iter_bag_frames(bag_path: str, sensor: SensorConfig, **kw) -> Iterator[tuple]:
    for i, stamp, frame_id, arr in iter_bag_compact(bag_path, **kw):
        yield i, frame_from_compact(arr, sensor, stamp=stamp, frame_id=frame_id)


def bag_info(bag_path: str) -> dict:
    import yaml
    meta = yaml.safe_load(open(os.path.join(bag_path, "metadata.yaml"), encoding="utf-8"))
    info = meta["rosbag2_bagfile_information"]
    return {
        "duration_s": info["duration"]["nanoseconds"] / 1e9,
        "message_count": info["message_count"],
        "topics": [(t["topic_metadata"]["name"], t["topic_metadata"]["type"], t["message_count"])
                   for t in info["topics_with_message_count"]],
    }


def npy_frame_index(path: str) -> Optional[int]:
    """Bag frame index encoded in a cached file name (``<bag>_0120.npy`` -> 120, as
    ``scripts/cache_frames.py`` writes them), or None when the name carries no number."""
    stem = os.path.splitext(os.path.basename(path))[0]
    m = re.search(r"(\d+)$", stem)
    return int(m.group(1)) if m else None


def iter_npy_frames(directory: str, sensor: SensorConfig, pattern: str = "*.npy", every: int = 1,
                    start: int = 0, limit: Optional[int] = None,
                    index_from_name: bool = False) -> Iterator[tuple]:
    """Yield (index, Frame) for the cached ``*.npy`` files of a directory in sorted order.

    ``index`` is the file's position in the full sorted list (so ``every`` / ``start`` /
    ``limit`` behave like they do for a bag), or, with ``index_from_name``, the number at the
    end of the file name when there is one (the bag frame index for ``scripts/cache_frames.py``
    output). The stamp is ``position * 0.1`` s: cached files carry no bag time.
    """
    files = sorted(glob.glob(os.path.join(directory, pattern)))
    n_out = 0
    for i, f in enumerate(files):
        if i < start or (i - start) % every != 0:
            continue
        arr = np.load(f)
        idx = i
        if index_from_name:
            named = npy_frame_index(f)
            idx = i if named is None else named
        yield idx, frame_from_compact(arr, sensor, stamp=float(i) * 0.1, frame_id=os.path.basename(f))
        n_out += 1
        if limit is not None and n_out >= limit:
            return


def load_npy_frame(path: str, sensor: SensorConfig) -> Frame:
    return frame_from_compact(np.load(path), sensor, frame_id=os.path.basename(path))
