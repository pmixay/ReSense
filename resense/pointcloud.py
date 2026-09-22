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
# quantised cache (8 bytes per point instead of 18): coordinates in centimetres as int16
# (+-327 m, the sensor returns nothing beyond ~210 m), intensity 0..255 and ring 0..127 as
# uint8. The 5 mm quantisation error is a quarter of the sensor's range noise (Pandar128
# manual: +-2 cm), and every reader goes through :func:`compact_to_xyz`.
COMPACT16_DTYPE = np.dtype(
    [("x", "i2"), ("y", "i2"), ("z", "i2"), ("intensity", "u1"), ("ring", "u1")]
)
COMPACT16_SCALE = 0.01   # m per unit
# in a *deduplicated* quantised cache the high bit of ``ring`` marks a point that stood twice
# in the frame: in the dual-return layout of the Pandar128 a ray with a single echo repeats it in
# both return slots (49 % of the points of a frame). :func:`expand_compact16` restores them.
DUP_FLAG = 0x80


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
    """(N,3) float32 array of sensor-frame coordinates from a compact array (either dtype)."""
    xyz = np.stack([arr["x"], arr["y"], arr["z"]], axis=1).astype(np.float32)
    if arr.dtype["x"].kind == "i":
        xyz *= np.float32(COMPACT16_SCALE)
    return xyz


def compact16_dedup(arr: np.ndarray) -> np.ndarray:
    """Collapse exact duplicates of a :data:`COMPACT16_DTYPE` array: every pair of identical
    rows becomes one row with :data:`DUP_FLAG` set in ``ring`` (a group of ``c`` identical rows
    becomes ``c // 2`` flagged rows plus one plain row if ``c`` is odd). Lossless: the detector
    never uses the point order, and :func:`expand_compact16` restores the multiset exactly."""
    if arr.size == 0:
        return arr
    key = np.ascontiguousarray(arr).view(np.uint64)
    _, first, counts = np.unique(key, return_index=True, return_counts=True)
    order = np.argsort(first)
    first, counts = first[order], counts[order]
    rows = arr[first]
    pairs, odd = counts // 2, counts % 2
    flagged = np.repeat(rows, pairs)
    flagged["ring"] |= np.uint8(DUP_FLAG)
    return np.concatenate([flagged, rows[odd > 0]])


def expand_compact16(arr: np.ndarray) -> np.ndarray:
    """Undo :func:`compact16_dedup` (no-op for any array without the flag)."""
    if arr.dtype.names is None or "ring" not in arr.dtype.names or arr.dtype["ring"].itemsize != 1:
        return arr
    dup = (arr["ring"] & DUP_FLAG) != 0
    if not dup.any():
        return arr
    out = np.repeat(arr, np.where(dup, 2, 1))
    out["ring"] &= np.uint8(~DUP_FLAG & 0xFF)
    return out


def compact_to_compact16(arr: np.ndarray) -> np.ndarray:
    """Quantise a compact array to :data:`COMPACT16_DTYPE` (points beyond +-327 m dropped)."""
    xyz = compact_to_xyz(arr)
    q = np.round(xyz / COMPACT16_SCALE)
    ok = (np.abs(q) < 32767).all(axis=1)
    out = np.zeros(int(ok.sum()), dtype=COMPACT16_DTYPE)
    out["x"], out["y"], out["z"] = q[ok, 0], q[ok, 1], q[ok, 2]
    out["intensity"] = np.clip(np.round(arr["intensity"][ok]), 0, 255)
    out["ring"] = np.clip(arr["ring"][ok], 0, 255)
    return out
