#!/usr/bin/env python3
"""False alarms and real detections against the frame processing starts from.

Through ROS the first 2-4 s of a played bag are lost to the DDS start-up (EXPERIMENTS.md
section 3b), so the jury's runs start somewhere after the first frame of a recording; the
offline evaluation always started at frame 0. This runs a fresh detector over every cached
recording from several start frames and reports, per start: alarm frames, alarm events
(distinct confirmed track ids) and STOP episodes; for ``doubleT_obstacle`` the frames in which
the labelled person (inside the envelope) and the object on the rail (its own bed-level
detection) are reported.

    python scripts/start_offsets.py --cache /data/cache --starts 0,10,20,30,40 [--json out.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
LABELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels", "doubleT_obstacle.json")


def run(job):
    cache, bag, start, config = job
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.io import iter_npy_frames
    cfg = DetectorConfig.from_yaml(config)
    det = Detector(cfg)
    lab = json.load(open(LABELS)) if bag == "doubleT_obstacle" else {}
    frames = alarms = episodes = 0
    ids, prev = set(), False
    hits = {"person_crossing": [0, 0], "object_on_rail": [0, 0]}
    for i, fr in iter_npy_frames(os.path.join(cache, bag), cfg.sensor, start=start, index_from_name=True):
        r = det.process(fr)
        frames += 1
        alarms += r.obstacle
        episodes += r.obstacle and not prev
        prev = r.obstacle
        ids.update(d.id for d in r.detections)
        for lb in lab.get(f"{i:05d}", []):
            if lb["label"] not in hits or not lb.get("in_gauge") or not lb.get("n_points", 1):
                continue
            own = lb["label"] == "object_on_rail"
            h = hits[lb["label"]]
            h[1] += 1
            h[0] += any(abs(d.distance - lb["distance"]) < 1.5 and abs(d.lateral - lb["lateral"]) < (0.4 if own else 1.0)
                        and (not own or d.kind == "low") for d in r.detections)
    return {"bag": bag, "start": start, "frames": frames, "alarm_frames": int(alarms), "events": len(ids),
            "episodes": int(episodes), "hits": hits if lab else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", default="/data/cache")
    ap.add_argument("--starts", default="0,10,20,30,40")
    ap.add_argument("--config", default="configs/default.yaml")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    starts = [int(s) for s in a.starts.split(",")]
    jobs = [(a.cache, b, s, a.config) for b in EMPTY + ["doubleT_obstacle"] for s in starts]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(run, jobs))
    for bag in EMPTY + ["doubleT_obstacle"]:
        rows = [r for r in res if r["bag"] == bag]
        cells = "  ".join(f"{r['start']:>3}: {r['alarm_frames']:>3}/{r['events']}/{r['episodes']}" for r in rows)
        print(f"{bag:38s} start: alarm frames/events/episodes  {cells}")
        if rows[0]["hits"]:
            for k in rows[0]["hits"]:
                print(f"{'':38s} {k}: " + "  ".join(f"{r['start']:>3}: {r['hits'][k][0]}/{r['hits'][k][1]}" for r in rows))
    tot = {s: [sum(r[k] for r in res if r["start"] == s and r["bag"] in EMPTY) for k in ("alarm_frames", "events", "episodes")]
           for s in starts}
    print("five obstacle-free recordings, per start:", {s: "/".join(map(str, v)) for s, v in tot.items()})
    if a.json:
        json.dump({"starts": starts, "config": a.config, "runs": res}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
