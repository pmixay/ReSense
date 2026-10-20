#!/usr/bin/env python3
"""Read-only snapshots at the actual F1a call; run the existing continuous replay."""
from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys

import numpy as np

ROOT = Path(os.environ["RESENSE_REPO"])
sys.path.insert(0, str(ROOT))
from resense.detector import Detector  # noqa: E402

original = Detector._rail_reference
out = Path(os.environ["F1_SNAPSHOTS"])
out.mkdir(parents=True, exist_ok=True)


def traced(self, clusters, xyz, dy, h):
    frame = getattr(self, "_b1_frame", 0)
    self._b1_frame = frame + 1
    # All calls are counted (F1a is enabled for the entire run).
    ranges = [(2650, 2680), (4140, 4170), (5690, 5730), (6840, 6880),
              (7340, 7380), (10450, 10520)]
    if any(a <= frame < b for a, b in ranges):
        lows = [c for c in clusters + self._low_height if c.kind == "low"]
        payload = {"X": xyz[:, 0], "dy": dy, "h": h}
        for i, c in enumerate(lows):
            payload[f"idx_{i}"] = c.points_idx
            payload[f"state_{i}"] = np.array([
                *c.bbox_min, *c.bbox_max, c.lateral, c.height_max,
                c.low_height_weak, c.zone == "gauge", bool(c.reason)])
        np.savez_compressed(out / f"frame_{frame:05d}.npz", **payload)
    return original(self, clusters, xyz, dy, h)


Detector._rail_reference = traced
runpy.run_path(str(ROOT / "docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py"), run_name="__main__")
