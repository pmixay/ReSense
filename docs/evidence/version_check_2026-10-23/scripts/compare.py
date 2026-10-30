#!/usr/bin/env python3
"""Compare the per-frame JSONL of `resense run --bag` for v1.0.0, v1.2.0 and the 1.3.0 tree: STOP / CAUTION-only
frames, first STOP, STOP distance range, decision differences between versions, clear_distance differences
(the positive control: the comparator must see a change where one is known to exist)."""
import json, sys
out = sys.argv[1]
res = {}
for b in ["doubleT_obstacle", "roundT_doubleT"]:
    rows = {v: [json.loads(l) for l in open(f"{out}/{v}_{b}.jsonl")] for v in ["v1.0.0", "v1.2.0", "head"]}
    for v, r in rows.items():
        stop = [i for i, x in enumerate(r) if x["obstacle"]]
        d = [r[i]["nearest_distance"] for i in stop if r[i]["nearest_distance"] is not None]
        res[f"{b}/{v}"] = {"frames": len(r), "stop_frames": len(stop), "first_stop_frame": stop[0] if stop else None,
                           "stop_distance_m": [min(d), max(d)] if d else None,
                           "caution_only_frames": sum(1 for x in r if x["warning"] and not x["obstacle"])}
    for a, c in [("v1.0.0", "v1.2.0"), ("v1.2.0", "head")]:
        res[f"{b}/{a}->{c}"] = {
            "decision_diff_frames": sum((x["obstacle"], x["warning"]) != (y["obstacle"], y["warning"]) for x, y in zip(rows[a], rows[c])),
            "clear_distance_diff_frames": sum(x["clear_distance"] != y["clear_distance"] for x, y in zip(rows[a], rows[c]))}
json.dump(res, open(f"{out}/summary.json", "w"), indent=1)
print(json.dumps(res, indent=1))
