#!/usr/bin/env python3
"""GaugeDisplay on base vs candidate.

    display_summary.py <replay report dir base> <dir cand> <falcon_disp base.jsonl> <falcon_disp cand.jsonl>

Recordings: N1's replay_gauge.py reports (drawn range p50/p90, support range p50, visible-pair 3D vertex step p90
of the displayed edge at 40/80/120 m against N1's limits 0.05/0.08/0.15 m and the pair counts). Falcon (streamed,
wrapper falcon_wrap_display.py): drawn range p50/p90 and the displayed lateral step p90 at 40/80/120 m over
consecutive frames both valid with the solid range reaching the distance (lateral only: the wrapper keeps y)."""
import glob
import json
import os
import sys

import numpy as np

LIM = {"40": .05, "80": .08, "120": .15}
out = {}
for tag, d in (("base", sys.argv[1]), ("cand", sys.argv[2])):
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        r = json.load(open(f))
        if "jitter" not in r:
            continue
        j = r["jitter"]
        out.setdefault(r["recording"], {})[tag] = {
            "drawn_p50_p90": [r["drawn_range_m"]["p50"], r["drawn_range_m"]["p90"]],
            "support_p50": r["support_range_m"]["p50"],
            "vis3d_p90": {k: j[k]["display_3d_vertex_step_m"]["p90"] for k in LIM},
            "pairs": {k: j[k]["same_supported_adjacent_pairs"] for k in LIM},
            "within_N1_limits": {k: (j[k]["display_3d_vertex_step_m"]["p90"] is not None
                                     and j[k]["display_3d_vertex_step_m"]["p90"] <= v) for k, v in LIM.items()},
            "decisions": r["decisions"], "detector_results_unchanged": r["detector_results_unchanged"]}
for tag, p in (("base", sys.argv[3]), ("cand", sys.argv[4])):
    rows = [json.loads(l)["disp"] for l in open(p)]
    drawn = [r["drawn"] for r in rows if r["valid"]]
    steps = {}
    for jx, x in enumerate((40, 80, 120)):
        s = [abs(b["y"][jx] - a["y"][jx]) for a, b in zip(rows, rows[1:])
             if a["valid"] and b["valid"] and a["y"] and b["y"] and min(a["solid"], b["solid"]) >= x]
        steps[str(x)] = {"p90": round(float(np.percentile(s, 90)), 3) if s else None, "pairs": len(s)}
    out.setdefault("falcon", {})[tag] = {"drawn_p50_p90": [float(np.percentile(drawn, 50)), float(np.percentile(drawn, 90))],
                                         "lateral_step": steps, "valid_frames": len(drawn), "frames": len(rows)}
print(json.dumps(out, indent=1))
