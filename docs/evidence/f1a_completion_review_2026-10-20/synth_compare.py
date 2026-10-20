#!/usr/bin/env python3
"""Reviewer script: tabulate synth_controls results of several sources, scene by scene.

    python synth_compare.py <out dir> <family> <tag1> <tag2> ...      (tags: ref, parent, cand)
Prints one row per scene: matched frames of 12 per source, flags where sources differ, and the number of frames in
which the sources' per-frame 'matched' flag differs.
"""
import json
import sys
from pathlib import Path

out, fam, tags = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
data = {t: json.load(open(out / f"synth_{fam}_{t}.json"))["results"] for t in tags}
n = len(data[tags[0]])
assert all(len(data[t]) == n for t in tags)
diff_scenes = 0
print(f"family {fam}: {n} scenes; columns = matched frames for " + ", ".join(tags))
for i in range(n):
    s = data[tags[0]][i]["spec"]
    for t in tags:
        assert data[t][i]["spec"] == s or {k: v for k, v in data[t][i]["spec"].items() if k != "trace"} == \
            {k: v for k, v in s.items() if k != "trace"}
    counts = [data[t][i]["matched_frames"] for t in tags]
    flag = "" if len(set(counts)) == 1 else "  <-- DIFFERENT"
    diff_scenes += bool(flag)
    perframe = sum(any(data[tags[0]][i]["rows"][k]["matched"] != data[t][i]["rows"][k]["matched"] for t in tags[1:])
                   for k in range(len(data[tags[0]][i]["rows"])))
    print(f"{s['kind']:7s} raise {s['raise_']:4.2f} d {s['dist']:4.0f} side {s['side']:+d} L {s['length']:3.1f} "
          f"W {s['width']:3.1f} delta {s['delta']:+5.2f} {s['bottom']:4s}: " + " ".join(f"{c:2d}" for c in counts)
          + f"   frames differing {perframe}" + flag)
print("scenes with different counts:", diff_scenes)
