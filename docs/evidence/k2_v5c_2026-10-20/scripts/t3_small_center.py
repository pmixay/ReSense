"""T3: set O small_center (hanging 0.3 m box on the sensor axis, 0.95-1.25 m above the rail head) under K2 vs K2 off,
from the gate's per-frame rows: per labelled frame in 30-80 m, each run's decision, the detection or warning matching
the object (distance within max(3 m, 3 %), vehicle Y within 1.5 m of the label's sensor-frame lateral; the rule of
stops_vs_markers.py), its zone and reason, and each run's axis at the object (track centre line) against the sensor
axis (the organizers' placement frame).

    python -I t3_small_center.py <labels/cloud_with_fake_obj.json> <gate work off> <gate work K2>
"""
import json
import os
import sys

import numpy as np

lab = json.load(open(sys.argv[1]))
runs = [[json.loads(line) for line in open(os.path.join(w, "cloud_with_fake_obj.jsonl"))] for w in sys.argv[2:4]]


def cy(t, x):
    y = t["center"] + np.tan(t["yaw"]) * x + 0.5 * t["curvature"] * x * x
    s, k = t.get("curv_step", 0.0), t.get("curv_knot", 0.0)
    if s and k > 0 and x > k:
        y += 0.5 * s * (x - k) ** 2
    return float(y)


print("frame  dist  lat_s | off: dec  match (zone reason)  axis | K2: dec  match (zone reason)  axis")
for k in sorted(k for k in lab if k != "_meta"):
    for o in lab[k]:
        if o.get("name") != "small_center" or not 30 <= o["distance"] <= 80:
            continue
        i = int(k)
        out = []
        for r in (runs[0][i], runs[1][i]):
            m = [(d["zone"], d["reason"], d["distance"]) for d in r["detections"] + r["warnings"]
                 if abs(d["distance"] - o["distance"]) <= max(3.0, 0.03 * o["distance"])
                 and abs(d["center"][1] - o["lateral_sensor"]) <= 1.5]
            dec = "STOP" if r["obstacle"] else ("CAUT" if r["warning"] else "GO")
            out.append(f"{dec:4s} {str(m[:1]):34s} {cy(r['track'], o['distance']):+.2f}")
        print(f"{i:5d} {o['distance']:5.1f} {o['lateral_sensor']:+.2f} | {out[0]} | {out[1]}")
