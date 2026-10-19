#!/usr/bin/env python3
"""Attribute each base STOP episode that a candidate lost or changed (replay.py --lowref outputs of the same
recording): the candidate's low clusters made weak by the F1 check (``weak`` in the candidate, at the same
distance / lateral (+-0.05 m) not weak in the base) within 3 m of the episode's detections along the track
(plus 2 m per frame before the onset: an approaching track was farther then; ~20 m/s) and 1 m across, from 10
frames before its onset to its end. ``attribute.py BASE.jsonl CAND.jsonl``"""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from episodes import episodes, load  # noqa: E402

base, cand = load(sys.argv[1]), load(sys.argv[2])
cstop = {r["frame"] for r in cand if r["x"]["decision"] == "STOP"}
out = []
for e in episodes(base):
    frames = list(range(e["onset"], e["last"] + 1))
    kept = [f for f in frames if f in cstop]
    if len(kept) == len(frames):
        continue
    pos = [(d["distance"], d["lateral"]) for f in frames for d in base[f]["detections"]]
    fired = []
    for f in range(max(0, e["onset"] - 10), e["last"] + 1):
        bw = [(c["d"], c["lat"]) for c in base[f]["x"].get("lowc", []) if not c["weak"]]
        for c in cand[f]["x"].get("lowc", []):
            ahead = 2.0 * max(0, e["onset"] - f)
            if not c["weak"] or not any(d - 3 <= c["d"] <= d + 3 + ahead and abs(c["lat"] - y) <= 1.0 for d, y in pos):
                continue
            if any(abs(c["d"] - d) < 0.05 and abs(c["lat"] - y) < 0.05 for d, y in bw):
                fired.append({"f": f, "d": c["d"], "lat": c["lat"], "top": c["top"], "ref": c["ref"],
                              "own_band": c["own_band"], "size": c["size"]})
    out.append({"onset": e["onset"], "n": e["n"], "kept": len(kept), "dets": e["dets"][:2],
                "low_any": e["low_any"], "f1_weak_clusters": fired})
for o in out:
    print(json.dumps({k: v for k, v in o.items() if k != "f1_weak_clusters"}))
    for w in o["f1_weak_clusters"]:
        print("     weak", json.dumps(w))
    if not o["f1_weak_clusters"]:
        print("     NO F1 weak cluster near this episode")
