#!/usr/bin/env python3
"""Protocol step 5: the three exact sector counters on scan-ordered clouds (indicative timing).

    PYTHONPATH=. python docs/evidence/cycle_2026-09-29/health_compare_counts/bench_sector_counts.py
    NPY_DISABLE_CPU_FEATURES="AVX512F AVX512CD AVX512_SKX AVX512_CLX AVX512_CNL AVX512_ICL AVX512_SPR" \
        PYTHONPATH=. python .../bench_sector_counts.py        # a CPU without AVX-512

The clouds are the committed synthetic fixture's clear-tunnel frame tiled 1, 3 and 7 times (127 k,
381 k and 890 k points, scan order kept), converted as the detector does; the edges are the default
health configuration's. Prints one JSON line per size: medians of 15 calls after one warm call.
"""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig
from resense.frame import frame_from_compact
from resense.health import _sector_counts

ROOT = Path(__file__).resolve().parents[4]


def binary_search(values, edges):
    """The 28.09 implementation's fast path (per-value search), for comparison."""
    n_bins = edges.size - 1
    counts = np.zeros(n_bins, dtype=np.intp)
    for start in range(0, values.size, 65536):
        block = values[start:start + 65536]
        indices = np.searchsorted(edges, block, side="right") - 1
        indices[block == edges[-1:]] -= 1
        valid = (indices >= 0) & (indices < n_bins)
        counts += np.bincount(indices[valid], minlength=n_bins)
    return counts


def median_ms(fn, repeat=15):
    fn()
    times = []
    for _ in range(repeat):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return round(1e3 * float(np.median(times)), 3)


def main():
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs" / "default.yaml"))
    frame = frame_from_compact(np.load(ROOT / "tests/fixtures/synthetic_lidar_v1/frames/clear_tunnel/frame_000.npy"),
                               cfg.sensor)
    edges = np.arange(-30.0, 30.0 + 1e-6, cfg.health.sector_deg)
    for tiles in (1, 3, 7):
        xyz = np.concatenate([frame.xyz] * tiles)
        az = np.degrees(np.arctan2(xyz[:, 1], xyz[:, 0]))
        expected = np.histogram(az, bins=edges)[0]
        assert np.array_equal(expected, _sector_counts(az, edges))
        assert np.array_equal(expected, binary_search(az, edges))
        print(json.dumps({"numpy": np.__version__, "python": platform.python_version(), "points": int(az.size),
                          "histogram_ms": median_ms(lambda: np.histogram(az, bins=edges)),
                          "binary_search_ms": median_ms(lambda: binary_search(az, edges)),
                          "compare_counts_ms": median_ms(lambda: _sector_counts(az, edges))}))


if __name__ == "__main__":
    main()
