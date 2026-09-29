"""``results.jsonl`` of a run (one ``/frames`` dict per line) and its line-offset index
``results.idx`` (little-endian uint64, n + 1 byte offsets), so paging an 11 000-frame run reads
only the requested lines."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import numpy as np

from resense_web.util import atomic_write_bytes, dumps

RESULTS = "results.jsonl"
INDEX = "results.idx"
_CHUNK = 16 * 1024 * 1024


class ResultsWriter:
    def __init__(self, run_dir: Path):
        self.path = Path(run_dir) / RESULTS
        self._fh = open(self.path, "wb")
        self.offsets: list[int] = [0]

    def __len__(self) -> int:
        return len(self.offsets) - 1

    def write(self, d: dict) -> None:
        line = (dumps(d) + "\n").encode("utf-8")
        self._fh.write(line)
        self.offsets.append(self.offsets[-1] + len(line))

    def close(self) -> None:
        self._fh.close()
        atomic_write_bytes(self.path.with_name(INDEX), np.asarray(self.offsets, dtype="<u8").tobytes())

    def abort(self) -> None:
        try:
            self._fh.close()
        except OSError:
            pass


def build_index(path: Path) -> np.ndarray:
    """Byte offsets of every line start (+ the end) of a JSONL file, blank lines skipped."""
    starts = [0]
    base = 0
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(_CHUNK)
            if not chunk:
                break
            nl = np.flatnonzero(np.frombuffer(chunk, dtype=np.uint8) == 10)
            starts.extend((nl + base + 1).tolist())
            base += len(chunk)
    if starts[-1] != base:
        starts.append(base)
    offs = np.asarray(starts, dtype=np.int64)
    # drop empty lines (a line of just "\n" or "\r\n")
    keep = np.ones(offs.size, dtype=bool)
    lengths = np.diff(offs)
    keep[1:][lengths <= 1] = False
    return offs[keep].astype("<u8") if offs.size else np.zeros(1, "<u8")


def load_index(run_dir: Path) -> np.ndarray:
    """The line index of a run's results, rebuilt (and saved) when it is missing or stale."""
    run_dir = Path(run_dir)
    res = run_dir / RESULTS
    idx = run_dir / INDEX
    try:
        if idx.stat().st_mtime >= res.stat().st_mtime - 1e-6:
            arr = np.fromfile(idx, dtype="<u8")
            if arr.size and int(arr[-1]) == res.stat().st_size:
                return arr
    except OSError:
        pass
    arr = build_index(res)
    try:
        atomic_write_bytes(idx, arr.tobytes())
    except OSError:
        pass
    return arr


def count(run_dir: Path) -> int:
    return max(0, int(load_index(run_dir).size) - 1)


def read_lines(run_dir: Path, start: int, n: int) -> tuple[list[bytes], int]:
    """Raw JSON lines ``start .. start + n - 1`` (clipped) and the total line count."""
    offs = load_index(run_dir)
    total = max(0, int(offs.size) - 1)
    start = max(0, min(int(start), total))
    stop = max(start, min(start + int(n), total))
    if stop == start:
        return [], total
    a, b = int(offs[start]), int(offs[stop])
    fd = os.open(Path(run_dir) / RESULTS, os.O_RDONLY)
    try:
        data = os.pread(fd, b - a, a)
    finally:
        os.close(fd)
    lines = [ln.rstrip(b"\r") for ln in data.split(b"\n") if ln.strip()]
    return lines, total


def iter_results(run_dir: Path) -> Iterator[dict]:
    with open(Path(run_dir) / RESULTS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)
