#!/usr/bin/env python3
"""List every object the detector confirmed on a recording (alarms *and* advisory tracks) as
events with geometry and a cause class, for review and as labels of an unlabelled ride.

    python scripts/mine_objects.py out/eval/v06 --bag new_data --out labels/new_data_objects.json

Input: the per-frame JSONL of ``scripts/eval_real.py`` (``<bag>.jsonl`` or ``<bag>_<k>.jsonl``
pieces). A track id is one event per piece. Per event: frames, first/last frame id, distance
range, median lateral offset / size / lowest point above the rail head / points, zone history
(frames as alarm vs advisory), demotion reasons, detection kind ('low' = bed bump). The cause
class is a rule on the median geometry, in this order:

``bed_fixture``  a low (bed-level) detection: track equipment between the rails
``person_like``  1.3-2.1 m tall, 0.25-1.0 m wide, <= 1.2 m long, standing (lowest point < 0.6 m)
``hanging``      lowest point > 1.5 m above the rail head
``edge``         median |lateral| >= 0.9 m: a structure at / beyond the envelope edge
``far_small``    beyond 90 m with <= 15 points
``tall_structure`` taller than 2.2 m
``other``
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os

import numpy as np


def classify(e: dict) -> str:
    L, W, H = e["size"]
    if e["kind"] == "low":
        return "bed_fixture"
    if 1.3 <= H <= 2.1 and 0.25 <= W <= 1.0 and L <= 1.2 and e["height_min"] < 0.6:
        return "person_like"
    if e["height_min"] > 1.5:
        return "hanging"
    if abs(e["lateral"]) >= 0.9:
        return "edge"
    if e["distance"][0] > 90 and e["n_points"] <= 15:
        return "far_small"
    if H > 2.2:
        return "tall_structure"
    return "other"


def mine(paths):
    events = []
    for pi, p in enumerate(paths):
        tracks = collections.OrderedDict()
        for line in open(p, encoding="utf-8"):
            d = json.loads(line)
            for zone, lst in (("gauge", d.get("detections", [])), ("warning", d.get("warnings", []))):
                for det in lst:
                    key = det["id"]
                    t = tracks.setdefault(key, {"piece": os.path.basename(p), "id": key, "frames": [], "zone": [],
                                                "dist": [], "lat": [], "size": [], "hmin": [], "n": [],
                                                "reason": collections.Counter(), "kind": collections.Counter()})
                    t["frames"].append(d.get("frame_id") or d.get("frame"))
                    t["zone"].append(zone)
                    t["dist"].append(det["distance"])
                    t["lat"].append(det["lateral"])
                    t["size"].append(det["size"])
                    t["hmin"].append(det.get("height_min", 0.0))
                    t["n"].append(det.get("n_points", 0))
                    t["reason"][det.get("reason", "")] += 1
                    t["kind"][det.get("kind", "")] += 1
        for t in tracks.values():
            e = {"piece": t["piece"], "id": t["id"], "n_frames": len(t["frames"]),
                 "first_frame": t["frames"][0], "last_frame": t["frames"][-1],
                 "alarm_frames": sum(z == "gauge" for z in t["zone"]),
                 "distance": [round(min(t["dist"]), 1), round(max(t["dist"]), 1)],
                 "lateral": round(float(np.median(t["lat"])), 2),
                 "size": [round(float(v), 2) for v in np.median(np.array(t["size"]), axis=0)],
                 "height_min": round(float(np.median(t["hmin"])), 2),
                 "n_points": int(np.median(t["n"])),
                 "reasons": {k: v for k, v in t["reason"].items() if k},
                 "kind": t["kind"].most_common(1)[0][0]}
            e["class"] = classify(e)
            events.append(e)
    return events


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="directory with the eval_real.py JSONL files")
    ap.add_argument("--bag", default="new_data")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    paths = sorted(glob.glob(os.path.join(a.run, f"{a.bag}.jsonl")) + glob.glob(os.path.join(a.run, f"{a.bag}_*.jsonl")))
    events = mine(paths)
    by = collections.defaultdict(lambda: [0, 0, 0])
    for e in events:
        by[e["class"]][0] += 1
        by[e["class"]][1] += e["alarm_frames"]
        by[e["class"]][2] += int(e["alarm_frames"] > 0)
    print(f"{len(events)} confirmed tracks in {len(paths)} piece(s)")
    print(f"{'class':16s} {'tracks':>7s} {'alarm events':>12s} {'alarm frames':>12s}")
    for k, (n, af, ae) in sorted(by.items(), key=lambda kv: -kv[1][0]):
        print(f"{k:16s} {n:7d} {ae:12d} {af:12d}")
    if a.out:
        json.dump({"_meta": {"run": a.run, "bag": a.bag, "n_events": len(events),
                             "classes": "bed_fixture, person_like, hanging, edge, far_small, tall_structure, other "
                                        "(rules in scripts/mine_objects.py)"},
                   "events": events}, open(a.out, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
