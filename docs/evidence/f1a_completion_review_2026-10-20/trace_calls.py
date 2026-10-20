#!/usr/bin/env python3
"""Reviewer script: list the synthetic scenes in which the new surface branch was reached (traced candidate run), with
per-frame clusters, surface values and whether the cluster was rejected, next to the matched flags of the plain
reference and candidate runs.

    python trace_calls.py <out dir>
"""
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
for fam in ("empty", "centre", "beside", "rail", "rail_ranges"):
    ref = json.load(open(D / f"synth_{fam}_ref.json"))["results"]
    cand = json.load(open(D / f"synth_{fam}_cand.json"))["results"]
    traced = json.load(open(D / f"synth_{fam}_cand_trace.json"))["results"]
    for a, c, t in zip(ref, cand, traced):
        if not any(tr["surface_calls"] for tr in t["trace"]):
            continue
        s = t["spec"]
        print(f"== {fam} raise {s['raise_']} d {s['dist']} side {s['side']} L {s['length']} W {s['width']} "
              f"delta {s['delta']} {s['bottom']}: matched ref {a['matched_frames']} cand {c['matched_frames']}")
        for k, tr in enumerate(t["trace"]):
            if tr["surface_calls"]:
                print(f"   f{k:02d} surface_calls {tr['surface_calls']} clusters "
                      f"{[(x['d'], x['lat'], x['width'], x['height_max'], 'REJ' if x['rejected'] else 'keep') for x in tr['clusters']]}"
                      f" matched ref {a['rows'][k]['matched']} cand {c['rows'][k]['matched']}")
