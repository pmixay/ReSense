#!/usr/bin/env python3
"""Inspect captured raw rail returns using an independent bin implementation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from resense.config import LowObjectConfig
from resense.lowobj import local_rail_reference


def line(X, dy, h, c, side, free):
    # Deliberately no _band_line / bincount / maximum.at: group raw points.
    lo, hi = c.bbox_min[0] - 5, c.bbox_max[0] + 5
    bins = {}
    for x, d, z in zip(X[free], dy[free], h[free]):
        if not lo <= x < hi or c.bbox_min[0] - 0.3 <= x <= c.bbox_max[0] + 0.3:
            continue
        if not side * 0.795 - 0.1 <= d <= side * 0.795 + 0.1 or not -0.3 < z < 0.3:
            continue
        b = int(np.floor((x - lo) / 0.5))
        bins.setdefault(b, []).append(float(z))
    return None if len(bins) < 2 else float(np.median([max(v) for v in bins.values()]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshots", type=Path)
    ap.add_argument("--frames", default="2666,2671,5709,5712,5714,7360,10484")
    a = ap.parse_args()
    for frame in map(int, a.frames.split(",")):
        p = a.snapshots / f"frame_{frame:05d}.npz"
        if not p.exists():
            continue
        with np.load(p) as data:
            X, dy, h = (data[k] for k in ("X", "dy", "h"))
            states = []
            free = np.ones(X.size, bool)
            for key in data.files:
                if not key.startswith("state_"):
                    continue
                i = key.removeprefix("state_")
                s, idx = data[key], data[f"idx_{i}"]
                free[idx] = False
                states.append(SimpleNamespace(bbox_min=s[:3], bbox_max=s[3:6], lateral=s[6],
                                              height_max=s[7], weak=bool(s[8]), gauge=bool(s[9]), reason=bool(s[10])))
            for c in states:
                if c.weak or not c.gauge or c.reason:
                    continue
                refs = []
                lines = []
                for mask in (np.ones(X.size, bool), free):
                    v = [line(X, dy, h, c, side, mask) for side in (-1, 1)]
                    t = np.clip((c.lateral + 0.795) / 1.59, 0, 1)
                    ref = v[0] + t * (v[1] - v[0]) if None not in v else next(
                        (z for side, z in zip((-1, 1), v) if z is not None and side * c.lateral > 0
                         and abs(c.lateral - side * 0.795) <= 0.3), None)
                    actual = local_rail_reference(c, X[mask], dy[mask], h[mask], LowObjectConfig(), 1.59)
                    assert actual == ref or (actual is not None and ref is not None and abs(actual - ref) < 1e-12)
                    refs.append(ref)
                    lines.append(v)
                if refs[0] is not None and c.height_max < refs[0] + 0.01:
                    print(json.dumps({"frame": frame, "x": float(c.bbox_min[0]), "lat": float(c.lateral),
                                      "top": float(c.height_max), "raw_lines": lines[0], "free_lines": lines[1],
                                      "refs": refs}))


if __name__ == "__main__":
    main()
