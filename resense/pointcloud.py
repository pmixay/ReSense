"""sensor_msgs/PointCloud2 decoding shared by the ROS 2 node and the offline tools.

Works with both ``rclpy`` messages and ``rosbags`` deserialized messages because
only duck-typed attributes are used (``fields``, ``point_step``, ``width``,
``height``, ``data``, ``is_bigendian``).
"""
from __future__ import annotations

import numpy as np

# sensor_msgs/PointField datatype -> numpy dtype
PF_DTYPES = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}

# compact representation used for cached frames (*.npy) and tests
COMPACT_DTYPE = np.dtype(
    [("x", "f4"), ("y", "f4"), ("z", "f4"), ("intensity", "f4"), ("ring", "u2")]
)


def pointcloud2_dtype(msg) -> np.dtype:
    """Build a numpy structured dtype that mirrors the PointCloud2 layout."""
    names, formats, offsets = [], [], []
    for f in msg.fields:
        base = PF_DTYPES[int(f.datatype)]
        if msg.is_bigendian:
            base = ">" + base
        if int(f.count) != 1:
            base = f"({int(f.count)},){base}"
        names.append(f.name)
        formats.append(base)
        offsets.append(int(f.offset))
    return np.dtype(
        {"names": names, "formats": formats, "offsets": offsets, "itemsize": int(msg.point_step)}
    )


def pointcloud2_to_structured(msg) -> np.ndarray:
    """Zero-copy view of the message payload as a structured array (one row per point)."""
    dt = pointcloud2_dtype(msg)
    n = int(msg.width) * int(msg.height)
    buf = msg.data
    if not isinstance(buf, (bytes, bytearray, memoryview, np.ndarray)):
        buf = bytes(buf)
    return np.frombuffer(buf, dtype=dt, count=n)


def structured_to_compact(arr: np.ndarray, min_range: float = 0.05) -> np.ndarray:
    """Drop NaN / zero-range points (Hesai emits (0,0,0) for missing returns) and keep
    x, y, z, intensity, ring in the compact dtype."""
    xyz = np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
    ok = np.isfinite(xyz).all(axis=1) & ((xyz * xyz).sum(axis=1) > min_range * min_range)
    out = np.zeros(int(ok.sum()), dtype=COMPACT_DTYPE)
    out["x"], out["y"], out["z"] = xyz[ok, 0], xyz[ok, 1], xyz[ok, 2]
    names = arr.dtype.names
    out["intensity"] = arr["intensity"][ok].astype(np.float32) if "intensity" in names else 0.0
    out["ring"] = arr["ring"][ok].astype(np.uint16) if "ring" in names else 0
    return out


def compact_to_xyz(arr: np.ndarray) -> np.ndarray:
    """(N,3) float32 array of sensor-frame coordinates from a compact array."""
    return np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
