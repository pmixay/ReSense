#!/usr/bin/env python3
"""Reviewer script: in a traced candidate run, how often is the new surface branch reached, does it return a value, and
in how many frames does a low cluster get rejected while a surface value was computed in that frame (rejections by the
new branch can only happen then).

    python trace_count.py <traced json>
"""
import json
import sys

res = json.load(open(sys.argv[1]))["results"]
frames = reached = valued = rej_with_value = scenes_with = 0
for r in res:
    hit = False
    for tr in r["trace"]:
        frames += 1
        vals = [v for v in tr["surface_calls"] if v is not None]
        reached += bool(tr["surface_calls"])
        valued += bool(vals)
        if vals and any(c["rejected"] for c in tr["clusters"]):
            rej_with_value += 1
            hit = True
    scenes_with += hit
print(f"scenes {len(res)} frames {frames}: frames where the branch was reached {reached}; with a surface value {valued}; "
      f"frames with a surface value AND a rejected low cluster {rej_with_value}; scenes with such frames {scenes_with}")
