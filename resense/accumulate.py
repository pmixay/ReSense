"""Ego-motion compensated accumulation of far corridor candidates over several frames.

The buffer keeps the corridor candidates of the last ``n_frames - 1`` frames beyond
``min_range`` in *track coordinates* (X along the axis, dy from the axis, h above the rail
head), which follow the curve because the track model re-estimates yaw and curvature every
frame. Each new frame shifts every stored point towards the vehicle by ``v * dt``; the
detector re-embeds the union into the current vehicle frame with the current track model,
so the clusterer sees one denser cloud. Near candidates (< ``min_range``) are never stored:
there the single frame is dense enough and a moving person must not be smeared.
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Optional, Tuple

import numpy as np


class CandidateBuffer:
    def __init__(self, n_frames: int, max_points: int = 20000):
        self.n_keep = max(0, int(n_frames) - 1)     # older frames kept next to the current one
        self.max_points = int(max_points)
        self._frames: Deque[dict] = deque()

    def __len__(self) -> int:
        return len(self._frames)

    def clear(self) -> None:
        self._frames.clear()

    def shift(self, ds: float) -> None:
        """Move every stored point ``ds`` metres towards the vehicle (train travelled ``ds``)."""
        if ds == 0.0:
            return
        for f in self._frames:
            f["X"] -= np.float32(ds)

    def push(self, X: np.ndarray, dy: np.ndarray, h: np.ndarray, intensity: np.ndarray,
             in_gauge: np.ndarray) -> None:
        if self.n_keep == 0:
            return
        n = int(X.size)
        if n > self.max_points:
            step = int(np.ceil(n / self.max_points))
            sl = slice(0, None, step)
            X, dy, h, intensity, in_gauge = X[sl], dy[sl], h[sl], intensity[sl], in_gauge[sl]
        self._frames.append({
            "X": np.asarray(X, np.float32).copy(), "dy": np.asarray(dy, np.float32).copy(),
            "h": np.asarray(h, np.float32).copy(), "i": np.asarray(intensity, np.float32).copy(),
            "g": np.asarray(in_gauge, bool).copy(),
        })
        while len(self._frames) > self.n_keep:
            self._frames.popleft()

    def merged(self, min_range: float = 0.0) -> Optional[Tuple[np.ndarray, ...]]:
        """Concatenated (X, dy, h, intensity, in_gauge) of the stored frames beyond ``min_range``."""
        if not self._frames:
            return None
        parts = [[] for _ in range(5)]
        for f in self._frames:
            keep = f["X"] >= min_range
            for p, k in zip(parts, ("X", "dy", "h", "i", "g")):
                p.append(f[k][keep])
        out = tuple(np.concatenate(p) for p in parts)
        return out if out[0].size else None
