import glob
import json
import os
import sys
d = sys.argv[1] if len(sys.argv) > 1 else "out/range"
for f in sorted(glob.glob(os.path.join(d, "*.json"))):
    try:
        s = json.load(open(f))["summary"]
    except Exception as e:
        print(f, "ERR", e)
        continue
    print(f"{os.path.basename(f)[:-5]:18s} vis1 {s['first_visible_X']!s:>7} STOP1 {s['first_stop_X']!s:>7} held {s['held_from_X']!s:>7} "
          f"GO<60 {s['go_within_60m']:2d} dec {s['decisions_while_visible']} {s['bins']} n@{s['n_obj_at']}")
