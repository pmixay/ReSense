#!/usr/bin/env python3
"""K2-5: the ride's STOP episodes (obstacle true) from a regression-gate work dir (new_data_0..7.jsonl in order,
global frame index), those with onset within +-5 frames of the curve edge episodes 3753, 6867, 7859, 7868, and
any STOP in frames 4720-4729 (crossover posts). Also (secondary) STOP frames within +-10 of the named frames.   ride_episodes.py <gatework dir> [<gatework dir> ...]"""
import glob
import json
import os
import sys

NAMED = (3753, 6867, 7859, 7868)
for wd in sys.argv[1:]:
    rows = []
    for k in range(len(glob.glob(os.path.join(wd, "new_data_*.jsonl")))):
        rows += [json.loads(l) for l in open(os.path.join(wd, f"new_data_{k}.jsonl"))]
    stop = [bool(r["obstacle"]) for r in rows]
    onsets = [i for i in range(len(stop)) if stop[i] and (i == 0 or not stop[i - 1])]
    named = {n: [(i, rows[i]["nearest_distance"]) for i in onsets if abs(i - n) <= 5] for n in NAMED}
    # secondary definition (reported, not pre-registered): any STOP frame within +-10 frames of the named frame
    near10 = {n: [i for i in range(n - 10, n + 11) if 0 <= i < len(stop) and stop[i]] for n in NAMED}
    print(json.dumps({"work": wd, "frames": len(rows), "stop_frames": sum(stop), "episodes": len(onsets),
                      "named_onsets": {str(k): v for k, v in named.items()},
                      "named_remaining": sum(bool(v) for v in named.values()),
                      "stop_within_10": {str(k): v for k, v in near10.items()},
                      "named_remaining_within_10": sum(bool(v) for v in near10.values()),
                      "stop_in_4720_4729": [i for i in range(4720, 4730) if stop[i]]}))
