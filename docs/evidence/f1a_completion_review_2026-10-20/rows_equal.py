#!/usr/bin/env python3
"""Reviewer script: are two synth_controls result files frame-for-frame identical in the detector outputs
(matched flag, matched kinds, all gauge-zone detections with distance/lateral/kind, model rail error)?

    python rows_equal.py <a.json> <b.json> [label]
Prints scenes, frames, number of differing frames and the first differences.
"""
import json
import sys

a = json.load(open(sys.argv[1]))["results"]
b = json.load(open(sys.argv[2]))["results"]
label = sys.argv[3] if len(sys.argv) > 3 else ""
assert len(a) == len(b)
frames = diff = 0
first = []
for i, (x, y) in enumerate(zip(a, b)):
    assert len(x["rows"]) == len(y["rows"])
    for k, (r, q) in enumerate(zip(x["rows"], y["rows"])):
        frames += 1
        key = lambda t: (t["matched"], t["matched_kind"], t["any_gauge"], t["rail_model_err"])  # noqa: E731
        if key(r) != key(q):
            diff += 1
            if len(first) < 5:
                first.append((i, k, key(r), key(q)))
print(f"{label}: scenes {len(a)} frames {frames} differing frames {diff}")
for f in first:
    print("   ", f)
