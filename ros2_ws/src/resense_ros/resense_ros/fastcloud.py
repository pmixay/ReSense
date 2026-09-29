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

:func:`decode` (29.09) is ``pointcloud2_to_arrays`` with the same arithmetic in fewer passes: the
organizers' layout (little-endian float32 x / y / z at offsets 0 / 4 / 8 of a 26-byte point) is
read with one 12-byte-per-point copy instead of three unaligned strided reads, and the kept points
are gathered by index once. 20.3 → 16.6 ms median (p95 29.2 → 23.7) on the 921 600-slot 360-degree
cloud, 7.4 → 4.8 ms on the 120-degree one (4-vCPU sandbox); the arrays are identical byte for byte
on every frame of both original recordings. Any other layout goes through ``pointcloud2_to_arrays``.
"""
from __future__ import annotations

import struct
from types import SimpleNamespace

import numpy as np

from resense.pointcloud import pointcloud2_to_arrays

FLOAT32, UINT16 = 7, 4           # sensor_msgs/PointField datatypes


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


def has_field(msg, name: str) -> bool:
    """Whether the cloud declares the point field ``name``. Both decoders fill a missing ``ring``
    with zeros (channel 0 for every point); the detector needs ``None`` there to tell an unknown
    channel from a known single channel (``cluster.weak_min_rings``, ``tracking.far_min_ring_count``)."""
    return any(getattr(f, "name", None) == name for f in (getattr(msg, "fields", None) or ()))


def _xyz_leading(msg) -> bool:
    """x, y, z are native little-endian float32 at offsets 0, 4, 8: one 12-byte block per point."""
    if msg.is_bigendian or np.little_endian is False or int(msg.point_step) < 12:
        return False
    want = {"x": 0, "y": 4, "z": 8}
    got = {f.name: f for f in msg.fields if f.name in want}
    return len(got) == 3 and all(got[k].offset == off and got[k].datatype == FLOAT32
                                 and int(getattr(got[k], "count", 1) or 1) == 1 for k, off in want.items())


def decode(msg, min_range: float, max_range: float):
    """``resense.pointcloud.pointcloud2_to_arrays(msg, min_range, max_range)``, faster: the same
    ``(xyz (N, 3) float32, intensity float32, ring uint16, n_finite, n_near)`` byte for byte.

    The range test is computed as there (float32 ``x**2 + y*y + z*z`` in that order, the same
    thresholds); only the reading differs: x / y / z are copied out as one 12-byte block per point
    and the kept points are gathered by index once. Layouts other than float32 x / y / z leading
    the point use the reference decode."""
    if not _xyz_leading(msg):
        return pointcloud2_to_arrays(msg, min_range, max_range)
    from resense.pointcloud import pointcloud2_to_structured
    arr = pointcloud2_to_structured(msg)           # a view of the bytes: intensity / ring as there
    n, step = arr.shape[0], int(msg.point_step)
    block = np.dtype({"names": ["xyz"], "formats": ["V12"], "offsets": [0], "itemsize": step})
    xyz = arr.view(block)["xyz"].copy().view(np.float32).reshape(n, 3)
    x, y, z = xyz[:, 0], xyz[:, 1], xyz[:, 2]
    r2 = x.astype(np.float32) ** 2
    r2 += y * y
    r2 += z * z
    finite = np.isfinite(r2) & (r2 > 0.0025)                 # (0, 0, 0): no return in that slot
    near = finite & (r2 < min_range * min_range)
    ok = finite & ~near & (r2 <= max_range * max_range)
    idx = np.flatnonzero(ok)
    names = arr.dtype.names
    inten = (arr["intensity"].take(idx).astype(np.float32) if "intensity" in names
             else np.zeros(idx.size, np.float32))
    ring = arr["ring"].take(idx).astype(np.uint16) if "ring" in names else np.zeros(idx.size, np.uint16)
    return xyz.take(idx, axis=0), inten, ring, int(np.count_nonzero(finite)), int(np.count_nonzero(near))


def packed(msg):
    """Validate the declared row layout and remove organized-cloud padding before decoding.

    The payload must contain exactly ``height * row_step`` bytes, including the final row's
    padding. A missing or zero ``row_step`` retains the packed-stride fallback for generic
    message objects. Complete unpadded and single-row messages are returned without a copy;
    organized padded rows are copied together with ``row_step`` set to their packed length.
    ``resense.pointcloud`` ignores row strides, so a malformed layout must fail here instead
    of letting padding bytes masquerade as points in an otherwise long-enough payload.
    """
    height, width, step = int(msg.height), int(msg.width), int(msg.point_step)
    if min(height, width, step) < 0:
        raise ValueError("PointCloud2 height, width and point_step must be nonnegative")
    if height and width and not step:
        raise ValueError("PointCloud2 point_step must be positive for a nonempty cloud")
    row = int(getattr(msg, "row_step", width * step) or width * step)
    if row < width * step:
        raise ValueError("PointCloud2 row_step is shorter than width * point_step")
    try:
        payload = memoryview(msg.data)
    except TypeError:
        payload = memoryview(bytes(msg.data))  # the reference decode also accepts a list of octets
    if payload.nbytes != height * row:
        raise ValueError(f"PointCloud2 data length {payload.nbytes} differs from height * row_step "
                         f"({height * row})")
    if height <= 1 or row == width * step:
        return msg
    buf = np.frombuffer(payload.cast("B"), np.uint8)
    data = buf.reshape(height, row)[:, :width * step].tobytes()
    return SimpleNamespace(header=msg.header, height=height, width=width, fields=msg.fields,
                           is_bigendian=msg.is_bigendian, point_step=step, row_step=width * step,
                           data=data, is_dense=getattr(msg, "is_dense", False))
