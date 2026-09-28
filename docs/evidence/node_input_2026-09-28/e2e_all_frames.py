#!/usr/bin/env python3
"""End-to-end latency of the committed node captures, two ways (README.md in this folder).

    python3 docs/evidence/node_input_2026-09-28/e2e_all_frames.py

``freshness.source_age_s`` of a result is the time from the input's publication by the player to
the result (through DDS, the node's queue, decode and detection). ``current`` = the results that
were valid when made (``freshness.valid``), the ones a consumer may act on: the figure
``scripts/check_dry_run.py`` prints. ``all`` = every frame result the node published, the start-up
catch-up included (those results are published as FAULT, CAUTION or a held STOP, never GO).
Frames the node skipped while catching up are in neither. Percentiles as ``check_dry_run.py``
(linear interpolation, numpy's default).
"""
from __future__ import annotations

import glob
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from check_dry_run import load, percentile  # noqa: E402  (scripts/)

CAPTURES = (sorted(glob.glob(os.path.join(HERE, "ab", "*_status.jsonl.gz")))
            + sorted(glob.glob(os.path.join(HERE, "cold_local", "*_status.jsonl.gz")))
            + sorted(glob.glob(os.path.join(ROOT, "docs", "evidence", "p1_p2_supported_playback_2026-09-27",
                                            "cached_bags_run_36319767736", "*_status.jsonl.gz"))))


def age_ms(frame):
    a = (frame.get("freshness") or {}).get("source_age_s")
    return 1e3 * a if isinstance(a, (int, float)) and math.isfinite(a) else None


def stats(values):
    if not values:
        return "-"
    return f"{len(values):3d}: {percentile(values, 50):4.0f} / {percentile(values, 95):5.0f} / {max(values):5.0f}"


def main() -> int:
    print(f"{'capture':75s} {'current n: median / p95 / max ms':>34s}   {'all frames n: median / p95 / max ms':>36s}")
    for path in CAPTURES:
        frames, _ = load(path)
        current = [age_ms(f) for f in frames if (f.get("freshness") or {}).get("valid") is True and age_ms(f) is not None]
        every = [age_ms(f) for f in frames if age_ms(f) is not None]
        name = os.path.relpath(path, os.path.join(ROOT, "docs", "evidence"))
        print(f"{name:75s} {stats(current):>34s}   {stats(every):>36s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
