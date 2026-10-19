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

# F1_SET="section.key=value;section.key=value": config overrides for the replica range_test builds
# (range_test.py has no override option; its cached baseline track model, <cache>_baseline.json, is the
# base detector's and is reused, so the object is placed exactly as for the base run)
_sets = [s for s in os.environ.get("F1_SET", "").split(";") if s]
if _sets:
    import yaml
    _over = {k: yaml.safe_load(v) for k, v in (s.split("=", 1) for s in _sets)}

    class _Replica(range_test.NodeReplica):
        def __init__(self, *a, **k):
            k.setdefault("overrides", _over)
            super().__init__(*a, **k)

    range_test.NodeReplica = _Replica
sink: list = []
lowref.patch_detector(sink)
sys.argv = [os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts/range_test.py")] + sys.argv[1:]
range_test.main()
out = sys.argv[3]
json.dump(sink, open(out + ".lowref.json", "w"))
