"""The node's input path for large clouds (28.09): a ``PointCloud2`` read straight from its CDR
bytes.

Why. rclpy's conversion of a received ``PointCloud2`` into a Python message costs 12.5 ms median
and 32 ms p95 per 24 MB 360-degree cloud of the organizers' recordings on a 4-vCPU sandbox (7 / 30
ms on a CI runner; 28.09): the executor pays it for every message it takes, before the node's
callback runs, and again for every queued frame of a start-up burst that the catch-up then skips.
The node subscribes with ``raw=True`` instead and :func:`parse_pointcloud2` reads the fields from
the serialized bytes (0.1 ms); ``data`` stays a zero-copy view of them, which keeps the bytes
object alive as long as the message is. The decode is unchanged
(``resense.pointcloud.pointcloud2_to_arrays``), so the detector gets the same arrays: checked by
``tests/test_fastcloud.py`` and, byte for byte on every frame of the original recordings, by
``scripts/check_fast_input.py``. Bytes the parser rejects go through rclpy's conversion.

:func:`packed` removes row padding (``row_step`` > ``width * point_step`` in an organized cloud),
which the decode does not expect; the organizers' clouds have one row and no padding.
"""
from __future__ import annotations

import struct
from types import SimpleNamespace

import numpy as np


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


def packed(msg):
    """``msg`` without row padding: an organized cloud (``height`` > 1) whose ``row_step`` is longer
    than ``width * point_step`` gets its rows copied together (a new object, ``row_step`` set to
    the packed length); anything else is returned as is. ``resense.pointcloud`` reads the payload
    as ``width * height`` consecutive points, which is right only without padding."""
    height, width, step = int(msg.height), int(msg.width), int(msg.point_step)
    row = int(getattr(msg, "row_step", width * step) or width * step)
    if height <= 1 or row <= width * step:
        return msg
    buf = np.frombuffer(memoryview(msg.data).cast("B"), np.uint8)
    if buf.size < height * row:
        return msg                   # truncated: let the decode report it
    data = buf[:height * row].reshape(height, row)[:, :width * step].tobytes()
    return SimpleNamespace(header=msg.header, height=height, width=width, fields=msg.fields,
                           is_bigendian=msg.is_bigendian, point_step=step, row_step=width * step,
                           data=data, is_dense=getattr(msg, "is_dense", False))
