#!/usr/bin/env python3
"""The judge's ``range_test.py`` (unchanged) with the read-only F1 low-cluster record (``lowref.py``):
writes the range test's own ``<out>.json`` plus ``<out>.lowref.json`` (per processed frame, every low
cluster's top against the frame's rail lines). Same arguments as range_test.py.

    measure_probe.py <cache> <icp.json> <out> --obj L,W,H --start s --d0 230 [--lat y] [--end e]
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("RESENSE_REPO", os.path.abspath(os.path.join(HERE, "../../../..")))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))

import json  # noqa: E402

import lowref  # noqa: E402
import range_test  # noqa: E402

sink: list = []
lowref.patch_detector(sink)
sys.argv = [os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts/range_test.py")] + sys.argv[1:]
range_test.main()
out = sys.argv[3]
json.dump(sink, open(out + ".lowref.json", "w"))
