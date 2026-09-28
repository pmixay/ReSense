"""The node's input path for large clouds (28.09): a ``PointCloud2`` read straight from its CDR
bytes, then decoded with one record gather.

Why. rclpy's conversion of a received ``PointCloud2`` into a Python message costs about 21 ms for a
24 MB 360-degree cloud of the organizers' recordings (4-vCPU sandbox, 28.09): the executor pays it
for every message it takes, before the node's callback runs, and again for every queued frame of
a start-up burst that the catch-up then skips. The node subscribes with ``raw=True`` instead and
:func:`parse_pointcloud2` reads the fields it needs from the serialized bytes; ``data`` stays a
zero-copy view of them. :func:`decode` then does what ``resense.pointcloud.pointcloud2_to_arrays``
does, but gathers the kept records once by index instead of masking every field (14 ms instead of
20 ms per 360-degree cloud, 5 instead of 8 ms per 120-degree cloud).

Both return exactly what the reference path returns (``deserialize_message`` and
``pointcloud2_to_arrays``): ``tests/test_fastcloud.py`` checks it on synthetic layouts and
``scripts/check_fast_input.py`` on every frame of the original recordings, byte for byte. Any
layout the fast path does not cover (big-endian data, other field types, a malformed buffer)
falls back to the reference path, so the detector always sees the same input.
"""
from __future__ import annotations

import struct
from types import SimpleNamespace

import numpy as np

from resense.pointcloud import pointcloud2_dtype, pointcloud2_to_arrays, pointcloud2_to_structured

CDR_BE, CDR_LE = 0, 1          # the second byte of the encapsulation header (OMG CDR, plain)


def _plain_header(sec: int, nanosec: int, frame_id: str):
    return SimpleNamespace(stamp=SimpleNamespace(sec=sec, nanosec=nanosec), frame_id=frame_id)


class _Reader:
    """Plain CDR: primitives aligned to their size, counted from the end of the 4-byte
    encapsulation header; strings are a uint32 length (with the terminating NUL) and the bytes."""

    def __init__(self, buf: memoryview):
        if len(buf) < 4 or buf[0] != 0 or buf[1] not in (CDR_BE, CDR_LE):
            raise ValueError("not a plain CDR encapsulation")
        self.buf, self.pos = buf, 4
        self.e = "<" if buf[1] == CDR_LE else ">"

    def _align(self, n: int) -> None:
        self.pos += (-(self.pos - 4)) % n

    def u32(self) -> int:
        self._align(4)
        v = struct.unpack_from(self.e + "I", self.buf, self.pos)[0]
        self.pos += 4
        return v

    def i32(self) -> int:
        self._align(4)
        v = struct.unpack_from(self.e + "i", self.buf, self.pos)[0]
        self.pos += 4
        return v

    def u8(self) -> int:
        v = self.buf[self.pos]
        self.pos += 1
        return v

    def string(self) -> str:
        n = self.u32()
        if n == 0:
            return ""
        if self.pos + n > len(self.buf) or self.buf[self.pos + n - 1] != 0:
            raise ValueError("malformed CDR string")
        s = bytes(self.buf[self.pos:self.pos + n - 1]).decode("utf-8")
        self.pos += n
        return s

    def octets(self) -> memoryview:
        n = self.u32()
        if self.pos + n > len(self.buf):
            raise ValueError("CDR sequence longer than the buffer")
        v = self.buf[self.pos:self.pos + n]
        self.pos += n
        return v


def parse_pointcloud2(raw, make_header=_plain_header) -> SimpleNamespace:
    """A ``sensor_msgs/PointCloud2`` from its serialized bytes (a raw subscription, rosbag2).

    Returns an object with the message's attribute names (``header.stamp.sec``, ``fields[i].name``,
    ``width``, ``data`` ...); ``data`` is a memoryview into ``raw`` (no copy). ``make_header(sec,
    nanosec, frame_id)`` builds ``header`` (the node passes one that makes a real ``std_msgs``
    Header, so it can be copied into the published messages). Raises ``ValueError`` on anything
    that is not a well-formed plain-CDR ``PointCloud2``."""
    try:
        r = _Reader(memoryview(raw).cast("B"))
        sec, nanosec = r.i32(), r.u32()
        header = make_header(sec, nanosec, r.string())
        height, width = r.u32(), r.u32()
        fields = []
        for _ in range(r.u32()):
            name = r.string()
            offset = r.u32()
            datatype = r.u8()
            count = r.u32()
            fields.append(SimpleNamespace(name=name, offset=offset, datatype=datatype, count=count))
        is_bigendian = bool(r.u8())
        point_step, row_step = r.u32(), r.u32()
        data = r.octets()
        is_dense = bool(r.u8())
    except (struct.error, IndexError, UnicodeDecodeError) as e:
        raise ValueError(f"malformed PointCloud2 CDR: {e}") from e
    if len(data) < width * height * point_step:
        raise ValueError("PointCloud2 data shorter than width * height * point_step")
    return SimpleNamespace(header=header, height=height, width=width, fields=fields,
                           is_bigendian=is_bigendian, point_step=point_step, row_step=row_step,
                           data=data, is_dense=is_dense)


def _fast_layout(msg) -> bool:
    """The layout :func:`decode` gathers directly: little-endian, x / y / z float32, intensity
    float32 and ring uint16 when present, one element each."""
    if msg.is_bigendian:
        return False
    want = {"x": 7, "y": 7, "z": 7, "intensity": 7, "ring": 4}
    seen = set()
    for f in msg.fields:
        if f.name in want:
            if int(f.datatype) != want[f.name] or int(f.count) != 1:
                return False
            seen.add(f.name)
    return {"x", "y", "z"} <= seen


def decode(msg, min_range: float, max_range: float):
    """``pointcloud2_to_arrays`` with one gather of the kept records: the same ``(xyz, intensity,
    ring, n_finite, n_near)``, bit for bit (the same float32 operations in the same order)."""
    if not _fast_layout(msg):
        return pointcloud2_to_arrays(msg, min_range, max_range)
    pointcloud2_dtype(msg)                       # the same validation of the field table
    arr = pointcloud2_to_structured(msg)
    x, y, z = arr["x"], arr["y"], arr["z"]
    r2 = np.multiply(x, x, dtype=np.float32)     # = x.astype(float32) ** 2
    t = np.multiply(y, y)
    r2 += t
    np.multiply(z, z, out=t)
    r2 += t
    finite = np.isfinite(r2) & (r2 > 0.0025)     # (0, 0, 0): no return in that slot
    near = finite & (r2 < min_range * min_range)
    ok = finite & ~near & (r2 <= max_range * max_range)
    rec = arr.take(np.flatnonzero(ok))           # the kept records, contiguous
    n = rec.shape[0]
    xyz = np.empty((n, 3), dtype=np.float32)
    xyz[:, 0], xyz[:, 1], xyz[:, 2] = rec["x"], rec["y"], rec["z"]
    names = arr.dtype.names
    inten = rec["intensity"].astype(np.float32) if "intensity" in names else np.zeros(n, np.float32)
    ring = rec["ring"].astype(np.uint16) if "ring" in names else np.zeros(n, np.uint16)
    return xyz, inten, ring, int(np.count_nonzero(finite)), int(np.count_nonzero(near))
