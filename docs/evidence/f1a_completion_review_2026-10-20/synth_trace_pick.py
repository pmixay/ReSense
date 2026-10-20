#!/usr/bin/env python3
"""Reviewer script: traced runs (read-only wrappers, see synth_controls.py) of picked scenes on the checkout in
RESENSE_REPO; prints, per scene, per frame, the low clusters the F1a check saw and the surface calls.

    RESENSE_REPO=<checkout> python synth_trace_pick.py <out json> raise,dist,side,L,W,delta,bottom[,kind] [...]
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import synth_controls as sc  # noqa: E402

out = Path(sys.argv[1])
res = []
for a in sys.argv[2:]:
    parts = a.split(",")
    raise_, dist, side, length, width, delta, bottom = parts[:7]
    kind = parts[7] if len(parts) > 7 else "rail"
    spec = dict(raise_=float(raise_), dist=float(dist), kind=kind, side=int(side), length=float(length),
                width=float(width), delta=float(delta), bottom=bottom, trace=True)
    r = sc.run_scene(spec)
    res.append(r)
    print("SCENE", a, "matched frames", r["matched_frames"])
    for k, (row, tr) in enumerate(zip(r["rows"], r["trace"])):
        cl = [c for c in tr["clusters"] if abs(c["lat"]) > 0.4]
        print(f"  f{k:02d} matched={row['matched']} gauge={row['any_gauge']} lowclusters={len(tr['clusters'])} "
              f"rail-side={cl} surface_calls={tr['surface_calls']}")
out.write_text(json.dumps(res) + "\n")
