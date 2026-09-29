"""Decimated point clouds for the 3D player: the ``RSC1`` binary format (webapp/API.md) and the
per-run store (``clouds.bin`` = concatenated RSC1 blobs, ``clouds.json`` = their index).

RSC1, little-endian: ``b"RSC1"``, uint32 n, int16[n*3] xyz in centimetres, uint8[n] intensity,
uint8[n] flags (bit0 corridor, bit1 inside a confirmed gauge object box, bit2 inside an advisory
box)."""
from __future__ import annotations

import math
import os
import struct
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

from resense_web.util import atomic_write_json, read_json

MAGIC = b"RSC1"
FORMAT = "RSC1"
MAX_CLOUDS = 3000
FLAG_CORRIDOR = 1
FLAG_OBJECT = 2
FLAG_WARNING = 4
BOX_MARGIN = 0.1          # m added around a detection box when flagging its points
_LIMIT_M = 327.67         # int16 centimetres


def cloud_stride(total_frames: int | None, max_clouds: int = MAX_CLOUDS) -> int:
    """Store every k-th processed frame so that a run keeps at most ``max_clouds`` clouds."""
    if not total_frames or total_frames <= max_clouds:
        return 1
    return int(math.ceil(total_frames / max_clouds))


def box_mask(xyz: np.ndarray, center: Sequence[float], size: Sequence[float],
             margin: float = BOX_MARGIN) -> np.ndarray:
    idx = box_indices(np.ascontiguousarray(xyz[:, 0]), xyz, center, size, margin)
    out = np.zeros(xyz.shape[0], dtype=bool)
    out[idx] = True
    return out


def box_indices(x: np.ndarray, xyz: np.ndarray, center: Sequence[float], size: Sequence[float],
                margin: float = BOX_MARGIN) -> np.ndarray:
    """Indices of the points inside an axis-aligned box ``center +- size / 2 + margin``: a cheap
    pass over the contiguous x column, then y / z on the few candidates (a 360 deg frame has ~1e6
    points and a frame can carry several boxes)."""
    c = np.asarray(center, dtype=np.float64)
    h = np.asarray(size, dtype=np.float64) * 0.5 + margin
    lo, hi = c - h, c + h
    cand = np.flatnonzero((x >= lo[0]) & (x <= hi[0]))
    if cand.size == 0:
        return cand
    sub = xyz[cand]
    ok = (sub[:, 1] >= lo[1]) & (sub[:, 1] <= hi[1]) & (sub[:, 2] >= lo[2]) & (sub[:, 2] <= hi[2])
    return cand[ok]


def cloud_flags(xyz: np.ndarray, corridor_idx: np.ndarray | None,
                detections: Iterable[dict] = (), warnings: Iterable[dict] = ()) -> np.ndarray:
    n = int(xyz.shape[0])
    flags = np.zeros(n, dtype=np.uint8)
    if corridor_idx is not None and len(corridor_idx):
        idx = np.asarray(corridor_idx, dtype=np.int64)
        idx = idx[(idx >= 0) & (idx < n)]
        flags[idx] |= FLAG_CORRIDOR
    boxes = [(d, FLAG_OBJECT) for d in detections] + [(d, FLAG_WARNING) for d in warnings]
    boxes = [(d, f) for d, f in boxes if d.get("center") is not None and d.get("size") is not None]
    if boxes:
        x = np.ascontiguousarray(xyz[:, 0])
        for det, flag in boxes:
            flags[box_indices(x, xyz, det["center"], det["size"])] |= flag
    return flags


def select_points(flags: np.ndarray, budget: int, rng: np.random.Generator,
                  valid: np.ndarray | None = None) -> np.ndarray:
    """Sorted indices: every flagged point, then a uniform sample of the rest up to ``budget``."""
    ok = np.ones(flags.shape[0], dtype=bool) if valid is None else valid
    keep = np.flatnonzero(ok & (flags != 0))
    rest = np.flatnonzero(ok & (flags == 0))
    room = max(0, int(budget) - keep.size)
    if rest.size > room:
        rest = rng.choice(rest, size=room, replace=False) if room else rest[:0]
    return np.sort(np.concatenate([keep, rest]))


def pack_rsc1(xyz: np.ndarray, intensity: np.ndarray, flags: np.ndarray) -> bytes:
    n = int(xyz.shape[0])
    q = np.clip(np.round(np.asarray(xyz, dtype=np.float64) * 100.0), -32768, 32767).astype("<i2")
    inten = np.clip(np.round(np.nan_to_num(np.asarray(intensity, dtype=np.float64))), 0, 255).astype(np.uint8)
    return b"".join((MAGIC, struct.pack("<I", n), q.tobytes(), inten.tobytes(),
                     np.asarray(flags, dtype=np.uint8).tobytes()))


def unpack_rsc1(buf: bytes) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(xyz in metres (n,3) float32, intensity uint8, flags uint8)."""
    if len(buf) < 8 or buf[:4] != MAGIC:
        raise ValueError("not an RSC1 cloud")
    (n,) = struct.unpack_from("<I", buf, 4)
    if len(buf) != 8 + n * 8:
        raise ValueError("truncated RSC1 cloud")
    xyz = np.frombuffer(buf, dtype="<i2", count=n * 3, offset=8).reshape(n, 3).astype(np.float32) / 100.0
    inten = np.frombuffer(buf, dtype=np.uint8, count=n, offset=8 + n * 6)
    flags = np.frombuffer(buf, dtype=np.uint8, count=n, offset=8 + n * 7)
    return xyz, inten, flags


def pack_frame_cloud(xyz: np.ndarray, intensity: np.ndarray, corridor_idx: np.ndarray | None,
                     detections: Iterable[dict], warnings: Iterable[dict], budget: int,
                     seed: int | Sequence[int] = 0) -> tuple[bytes, int]:
    """One RSC1 blob of a processed frame; returns (blob, number of points)."""
    xyz = np.asarray(xyz, dtype=np.float32)
    flags = cloud_flags(xyz, corridor_idx, detections, warnings)
    sel = select_points(flags, budget, np.random.default_rng(seed))
    pts = xyz[sel]
    # the detector's cloud is finite and range-filtered: checking the selection is enough
    ok = (np.abs(pts) < _LIMIT_M).all(axis=1)          # False for NaN too
    if not ok.all():
        sel, pts = sel[ok], pts[ok]
    return pack_rsc1(pts, np.asarray(intensity)[sel], flags[sel]), int(sel.size)


class CloudWriter:
    """Appends RSC1 blobs to ``clouds.bin`` and writes the ``clouds.json`` index on close."""

    def __init__(self, run_dir: Path, budget: int, stride: int = 1, max_clouds: int = MAX_CLOUDS):
        self.run_dir = Path(run_dir)
        self.budget = int(budget)
        self.stride = max(1, int(stride))
        self.max_clouds = int(max_clouds)
        self.frames: list[int] = []
        self.offsets: list[int] = []
        self.sizes: list[int] = []
        self._pos = 0
        self._fh = open(self.run_dir / "clouds.bin", "wb")

    def wants(self, pos: int) -> bool:
        return pos % self.stride == 0 and len(self.frames) < self.max_clouds

    def add(self, pos: int, blob: bytes) -> None:
        self._fh.write(blob)
        self.frames.append(int(pos))
        self.offsets.append(self._pos)
        self.sizes.append(len(blob))
        self._pos += len(blob)

    def close(self) -> dict:
        self._fh.close()
        index = {"format": FORMAT, "points": self.budget, "stride": self.stride, "frames": self.frames,
                 "offsets": self.offsets, "sizes": self.sizes}
        atomic_write_json(self.run_dir / "clouds.json", index)
        return index

    def abort(self) -> None:
        try:
            self._fh.close()
        except OSError:
            pass


def load_index(run_dir: Path) -> dict | None:
    idx = read_json(Path(run_dir) / "clouds.json")
    if not isinstance(idx, dict) or "frames" not in idx:
        return None
    return idx


def read_cloud(run_dir: Path, index: dict, pos: int) -> bytes | None:
    """The RSC1 blob stored for processed position ``pos`` (None when it has no cloud)."""
    frames = index.get("frames") or []
    i = int(np.searchsorted(frames, pos))
    if i >= len(frames) or frames[i] != pos:
        return None
    off, size = int(index["offsets"][i]), int(index["sizes"][i])
    try:
        fd = os.open(Path(run_dir) / "clouds.bin", os.O_RDONLY)
    except OSError:
        return None
    try:
        blob = os.pread(fd, size, off)
    finally:
        os.close(fd)
    return blob if len(blob) == size else None
