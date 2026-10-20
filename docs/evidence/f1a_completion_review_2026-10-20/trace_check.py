#!/usr/bin/env python3
"""Reviewer script: (1) traced run == plain run on every scene/frame ('matched' flag, matched kinds, any_gauge list);
(2) how often was the new surface branch reached / did it return a value / did it reject, across all scenes.

    python trace_check.py <out dir>
"""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
tot = dict(scenes=0, frames=0, differ=0, calls=0, surface_values=0, clusters_checked=0, rejected=0, scenes_with_call=0)
for fam in ("empty", "centre", "beside", "rail", "rail_ranges"):
    plain = json.load(open(D / f"synth_{fam}_cand.json"))["results"]
    traced = json.load(open(D / f"synth_{fam}_cand_trace.json"))["results"]
    assert len(plain) == len(traced)
    for a, b in zip(plain, traced):
        tot["scenes"] += 1
        called = False
        for ra, rb, tr in zip(a["rows"], b["rows"], b["trace"]):
            tot["frames"] += 1
            if (ra["matched"], ra["matched_kind"], ra["any_gauge"]) != (rb["matched"], rb["matched_kind"], rb["any_gauge"]):
                tot["differ"] += 1
            tot["clusters_checked"] += len(tr["clusters"])
            tot["rejected"] += sum(c["rejected"] for c in tr["clusters"])
            tot["calls"] += len(tr["surface_calls"])
            tot["surface_values"] += sum(v is not None for v in tr["surface_calls"])
            called |= bool(tr["surface_calls"])
        tot["scenes_with_call"] += called
print(json.dumps(tot, indent=1))
