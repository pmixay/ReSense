#!/usr/bin/env python3
"""Reviewer script: traced approach scene on the checkout in RESENSE_REPO; prints per frame the matched flag, the
low clusters that the F1a check saw (lateral, width, capped top, rejected?) and the surface-call values.

    RESENSE_REPO=<checkout> python apr_trace.py <out json> raise side L W delta bottom
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth_controls as sc  # noqa: E402

out = Path(sys.argv[1])
raise_, side, length, width, delta = (float(v) for v in sys.argv[2:7])
bottom = sys.argv[7]
spec = dict(raise_=raise_, dist=58.0, kind="rail", side=int(side), length=length, width=width, delta=delta,
            bottom=bottom, nframes=45, approach_step=0.8, trace=True)
r = sc.run_scene(spec)
print("matched frames", r["matched_frames"], "of", len(r["rows"]))
for k, (row, tr) in enumerate(zip(r["rows"], r["trace"])):
    rail = [(c["d"], c["lat"], c["width"], c["height_max"], "REJ" if c["rejected"] else "keep")
            for c in tr["clusters"] if abs(abs(c["lat"]) - 0.795) < 0.25]
    if row["matched"] or tr["surface_calls"] or tr["clusters"]:
        print(f"f{k:02d} dist {row['dist']:5.1f} matched={row['matched']} rail clusters {rail} all low {len(tr['clusters'])} gauge {row['any_gauge']} surface {tr['surface_calls']}")
out.write_text(json.dumps(r) + "\n")
