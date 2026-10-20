"""Summary of gate_h_trace.py records: per recording piece, frames where H′ ran with a final mount, clusters it
looked at, clusters over the model / mount threshold, clusters it made advisory, and the largest disagreement.

    gate_h_summary.py <trace dir>
"""
import glob
import json
import os
import sys

tot = {"frames": 0, "ran": 0, "rows": 0, "over": 0, "dem": 0}
for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.h.ndjson"))):
    recs = [json.loads(line) for line in open(p)]
    ran = [r for r in recs if r.get("called") and r.get("ok")]
    rows = [(r["stem"], x) for r in ran for x in r["rows"]]
    over = [(s, x) for s, x in rows if x["diff"] > x["thr"]]
    dem = [(s, x) for s, x in rows if x["demoted"]]
    mx = max((x["diff"] - x["thr"] for _, x in rows), default=None)
    worst = max(rows, key=lambda sx: sx[1]["diff"] - sx[1]["thr"], default=None)
    print(f"{os.path.basename(p):45s} frames {len(recs):5d}  final mount {len(ran):5d}  clusters looked at {len(rows):5d}  "
          f"over threshold {len(over):3d}  made advisory {len(dem):3d}  max(diff - thr) "
          f"{'-' if mx is None else round(mx, 3)}{'' if worst is None else ' at ' + worst[0] + ' d ' + str(worst[1]['d'])}")
    for s, x in over:
        print(f"    OVER {s}: d {x['d']} lat {x['lat']} {x['kind']} diff {x['diff']} thr {x['thr']} "
              f"heights above the plane {x['hm_min']}..{x['hm_max']} demoted {x['demoted']}")
    for k, v in (("frames", len(recs)), ("ran", len(ran)), ("rows", len(rows)), ("over", len(over)), ("dem", len(dem))):
        tot[k] += v
print("TOTAL", tot)
