"""The node's input path (``resense_ros/fastcloud.py``, 28.09): a ``PointCloud2`` read from its
serialized bytes must give the detector exactly what rclpy's message gives it through
``resense.pointcloud.pointcloud2_to_arrays``. No ROS needed: the CDR bytes are made by
the small encoder below, and one sample is the literal output of rclpy's ``serialize_message``
(ROS 2 Humble, Fast DDS) for the message ``_golden_message`` describes. The original recordings
are compared frame by frame by ``scripts/check_fast_input.py`` (in the image, CI job ``docker``).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "resense_ros"))

from resense.pointcloud import pointcloud2_to_arrays  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

# the organizers' layout: x y z intensity float32, ring uint16, timestamp float64 (point_step 26)
ORGANIZERS = (("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4), ("timestamp", 18, 8))
NP_TYPES = {7: "f4", 8: "f8", 4: "u2", 2: "u1", 6: "u4"}


def _cloud(points: dict, layout=ORGANIZERS, step=26, bigendian=False, stamp=(1726650000, 123456789),
           frame_id="lidar_livox"):
    """A PointCloud2-shaped message (the attributes rclpy's message has) and its CDR bytes."""
    e = ">" if bigendian else "<"
    dt = np.dtype({"names": [n for n, _, _ in layout], "formats": [e + NP_TYPES[d] for _, _, d in layout],
                   "offsets": [o for _, o, _ in layout], "itemsize": step})
    n = len(next(iter(points.values())))
    arr = np.zeros(n, dt)
    for name, values in points.items():
        if name in dt.names:
            arr[name] = values
    fields = [SimpleNamespace(name=nm, offset=o, datatype=d, count=1) for nm, o, d in layout]
    msg = SimpleNamespace(header=SimpleNamespace(stamp=SimpleNamespace(sec=stamp[0], nanosec=stamp[1]),
                                                 frame_id=frame_id),
                          height=1, width=n, fields=fields, is_bigendian=bigendian, point_step=step,
                          row_step=step * n, data=arr.tobytes(), is_dense=False)
    return msg, _cdr(msg)


def _cdr(msg, garbage_padding=False, big_endian=False) -> bytes:
    """Plain CDR of a PointCloud2, little-endian unless ``big_endian`` (an encoder independent of
    the parser)."""
    out = bytearray(b"\x00\x00\x00\x00" if big_endian else b"\x00\x01\x00\x00")
    e = ">" if big_endian else "<"

    def align(a):
        while (len(out) - 4) % a:
            out.append(0xA5 if garbage_padding else 0)

    def u32(v, fmt="I"):
        align(4)
        out.extend(struct.pack(e + fmt, v))

    def string(s):
        b = s.encode() + b"\x00"
        u32(len(b))
        out.extend(b)

    u32(msg.header.stamp.sec, "i")
    u32(msg.header.stamp.nanosec)
    string(msg.header.frame_id)
    u32(msg.height)
    u32(msg.width)
    u32(len(msg.fields))
    for f in msg.fields:
        string(f.name)
        u32(f.offset)
        out.append(f.datatype)
        u32(f.count)
    out.append(int(msg.is_bigendian))
    u32(msg.point_step)
    u32(msg.row_step)
    u32(len(msg.data))
    out.extend(msg.data)
    out.append(int(msg.is_dense))
    return bytes(out)


def _scan(rng, n=5000):
    """Returns like the Hesai's: most in range, empty (0, 0, 0) slots, NaN, near and far points."""
    xyz = rng.uniform(-120, 120, size=(n, 3)).astype(np.float32)
    xyz[::10] = 0.0                                   # dual-return slots without an echo
    xyz[3::97] = np.nan
    xyz[5::53] *= 0.01                               # within min_range (window dirt)
    xyz[7::61] *= 3.0                                # beyond max_range
    return {"x": xyz[:, 0], "y": xyz[:, 1], "z": xyz[:, 2],
            "intensity": rng.uniform(0, 255, n).astype(np.float32), "ring": rng.integers(0, 128, n),
            "timestamp": np.linspace(0, 0.1, n)}


def _same(a, b):
    assert len(a) == len(b) == 5
    for u, v in zip(a[:3], b[:3]):
        assert u.dtype == v.dtype and u.shape == v.shape and u.tobytes() == v.tobytes()
    assert a[3:] == b[3:]


def test_parse_reads_rclpy_bytes():
    """The literal ``serialize_message`` output of rclpy (Humble, Fast DDS) for a 3-point cloud; its
    padding bytes are uninitialised memory, which the parser must skip, not read."""
    raw = bytes.fromhex(
        "000100009096ea6615cd5b070c00000068657361695f6c6964617200010000000300000005000000020000007800"
        "000000000000070000000100000002000000790000000400000007f0064a01000000020000007a0000000800000007"
        "550000010000000a000000696e74656e7369747900064a0c00000007000000010000000500000072696e670004000"
        "01000000004f1064a01000000000000001200000036000000360000000000c03f000000c00000803e0000404103000"
        "000000000000000000000000000000000000000f04100008040000080bf0000c6427f0000")
    msg = fastcloud.parse_pointcloud2(raw)
    assert (msg.header.stamp.sec, msg.header.stamp.nanosec, msg.header.frame_id) == (1726650000, 123456789,
                                                                                     "hesai_lidar")
    assert (msg.height, msg.width, msg.point_step, msg.row_step, msg.is_bigendian, msg.is_dense) == (1, 3, 18, 54,
                                                                                                    False, False)
    assert [(f.name, f.offset, f.datatype, f.count) for f in msg.fields] == [
        ("x", 0, 7, 1), ("y", 4, 7, 1), ("z", 8, 7, 1), ("intensity", 12, 7, 1), ("ring", 16, 4, 1)]
    pts = [struct.unpack_from("<ffffH", msg.data, 18 * i) for i in range(3)]
    assert pts == [(1.5, -2.0, 0.25, 12.0, 3), (0.0, 0.0, 0.0, 0.0, 0), (30.0, 4.0, -1.0, 99.0, 127)]
    xyz, inten, ring, n_finite, n_near = pointcloud2_to_arrays(msg, 0.5, 250.0)
    assert xyz.tolist() == [[1.5, -2.0, 0.25], [30.0, 4.0, -1.0]] and n_finite == 2 and n_near == 0
    assert inten.tolist() == [12.0, 99.0] and ring.tolist() == [3, 127]


@pytest.mark.parametrize("garbage", [False, True])
def test_parse_round_trip_and_zero_copy(garbage):
    msg, _ = _cloud(_scan(np.random.default_rng(1), 300), frame_id="")
    raw = _cdr(msg, garbage_padding=garbage)
    got = fastcloud.parse_pointcloud2(raw)
    assert got.header.frame_id == "" and got.width == 300 and bytes(got.data) == msg.data
    assert isinstance(got.data, memoryview) and got.data.obj is raw       # a view of the bytes, not a copy
    made = []
    fastcloud.parse_pointcloud2(raw, lambda s, ns, f: made.append((s, ns, f)) or "header")
    assert made == [(1726650000, 123456789, "")]


def test_malformed_bytes_are_rejected():
    msg, raw = _cloud(_scan(np.random.default_rng(2), 50))
    for bad in (b"", b"\x00\x02\x00\x00" + raw[4:], raw[:40], raw[:-200]):
        with pytest.raises(ValueError):
            fastcloud.parse_pointcloud2(bad)


@pytest.mark.parametrize("layout,step", [
    (ORGANIZERS, 26),                                                                 # the recordings
    ((("x", 0, 7), ("y", 4, 7), ("z", 8, 7), ("intensity", 12, 7), ("ring", 16, 4)), 18),   # the node tests
    ((("x", 0, 7), ("y", 4, 7), ("z", 8, 7)), 16),                                     # no intensity, no ring
    ((("x", 0, 8), ("y", 8, 8), ("z", 16, 8), ("intensity", 24, 7)), 28),              # float64 coordinates
])
@pytest.mark.parametrize("bigendian", [False, True])
def test_the_detector_gets_the_same_arrays_from_the_bytes(layout, step, bigendian):
    """The decode is unchanged (``pointcloud2_to_arrays``): what the node reads from the bytes gives
    the arrays rclpy's message gives, bit for bit, for any layout and data endianness."""
    names = {n for n, _, _ in layout}
    pts = {k: v for k, v in _scan(np.random.default_rng(3), 20000).items() if k in names}
    msg, raw = _cloud(pts, layout, step, bigendian=bigendian)
    parsed = fastcloud.parse_pointcloud2(raw)
    for rng_min, rng_max in ((2.5, 250.0), (0.5, 60.0)):
        _same(pointcloud2_to_arrays(fastcloud.packed(parsed), rng_min, rng_max),
              pointcloud2_to_arrays(msg, rng_min, rng_max))


def test_big_endian_encapsulation_is_read_too():
    """CDR_BE (encapsulation 00 00): every count, offset and string length big-endian."""
    msg, _ = _cloud(_scan(np.random.default_rng(5), 200))
    got = fastcloud.parse_pointcloud2(_cdr(msg, big_endian=True))
    assert (got.header.stamp.sec, got.header.stamp.nanosec, got.header.frame_id) == (1726650000, 123456789,
                                                                                     "lidar_livox")
    assert [(f.name, f.offset, f.datatype) for f in got.fields] == [(f.name, f.offset, f.datatype) for f in msg.fields]
    assert (got.width, got.point_step) == (200, 26) and bytes(got.data) == msg.data


def test_row_padding_is_removed_before_the_decode():
    """An organized cloud (3 rows of 1000 points) with 40 bytes of padding after every row decodes
    like the same points without padding; an unpadded or single-row cloud is left as it is."""
    msg, _ = _cloud(_scan(np.random.default_rng(6), 3000))
    rows = np.frombuffer(msg.data, np.uint8).reshape(3, 1000 * 26)
    padded = SimpleNamespace(**{**vars(msg), "height": 3, "width": 1000, "row_step": 1000 * 26 + 40,
                                "data": np.hstack([rows, np.full((3, 40), 0x7F, np.uint8)]).tobytes()})
    unpacked = fastcloud.packed(padded)
    assert unpacked.row_step == 26000 and bytes(unpacked.data) == msg.data
    _same(pointcloud2_to_arrays(unpacked, 2.5, 250.0), pointcloud2_to_arrays(msg, 2.5, 250.0))
    assert fastcloud.packed(msg) is msg
    organized = SimpleNamespace(**{**vars(msg), "height": 3, "width": 1000, "row_step": 26000})
    assert fastcloud.packed(organized) is organized
