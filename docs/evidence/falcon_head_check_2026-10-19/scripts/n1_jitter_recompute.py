"""Recompute N1's visible-edge jitter from its stored rows with an own formula (adjacent valid frames whose
solid range reaches the station; 3D change of the drawn axis), next to the raw detector axis on the same pairs.

    python n1_jitter_recompute.py docs/evidence/n1_n4_2026-10-18/final_core_f5ff15f/rows
"""
import gzip
import json
import sys

import numpy as np

CLAIMED = {"cloud_with_fake_obj": (0.01817, 0.02975, 0.04029), "doubleT_obstacle": (0.00391, 0.01244, 0.02187),
           "roundT_doubleT": (0.03253, 0.03055, 0.02846), "doubleT_platform": (0.01955, 0.01364, 0.02013)}
for rec, claimed in CLAIMED.items():
    rows = [json.loads(line) for line in gzip.open(f"{sys.argv[1]}/{rec}.jsonl.gz", "rt")]
    out = []
    for k, x in enumerate((40, 80, 120)):           # rows store the axis at 40 / 80 / 120 m
        drawn, raw = [], []
        for a, b in zip(rows[:-1], rows[1:]):
            ga, gb = a["gauge"], b["gauge"]
            if not (ga.get("valid") and gb.get("valid")) or min(ga["solid_range_m"], gb["solid_range_m"]) < x:
                continue
            drawn.append(np.hypot(b["display_y"][k] - a["display_y"][k], b["display_z"][k] - a["display_z"][k]))
            raw.append(np.hypot(b["raw_y"][k] - a["raw_y"][k], b["raw_z"][k] - a["raw_z"][k]))
        out.append((np.percentile(drawn, 90), np.percentile(raw, 90), len(drawn)))
    print(f"{rec:20s} n={len(rows):4d} | drawn p90 40/80/120 m: " + "/".join(f"{o[0]:.4f}" for o in out)
          + " | N1 reported: " + "/".join(f"{c:.4f}" for c in claimed)
          + " | raw axis, same pairs: " + "/".join(f"{o[1]:.3f}" for o in out)
          + " | visible pairs: " + "/".join(str(o[2]) for o in out) + f" of {len(rows) - 1}")
