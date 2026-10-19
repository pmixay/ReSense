#!/usr/bin/env python3
"""Traced attribution of every base STOP episode a candidate lost or shortened (replay.py --tracks --lowref of
both runs; independent review 1, finding 4). For each lost episode: the base tracks that reported it, each
track's own matched clusters (base ``x.tracks``) from 30 frames before the onset to the end, and for each of those
hits whether the candidate's F1 check fired on the same cluster in the same frame (a candidate low cluster at the
same distance / lateral within 0.05 m with reason ``below_rail_ref``, or made weak where the base's was not).
``attribute_traced.py BASE.jsonl CAND.jsonl`` -> one JSON line per episode, ``fired_on_own_hits`` listed."""
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from episodes import episodes, load  # noqa: E402

base, cand = load(sys.argv[1]), load(sys.argv[2])
cstop = {r["frame"] for r in cand if r["x"]["decision"] == "STOP"}
n_lost = n_explained = 0
for e in episodes(base):
    frames = list(range(e["onset"], e["last"] + 1))
    kept = [f for f in frames if f in cstop]
    if len(kept) == len(frames):
        continue
    n_lost += 1
    ids = {d["id"] for f in frames for d in base[f]["detections"]}
    own, fired = [], []
    for f in range(max(0, e["onset"] - 30), e["last"] + 1):
        for tid, d, lat, kind, zone, reason, weak in base[f]["x"].get("tracks", []):
            if tid not in ids:
                continue
            own.append((f, tid, d, lat, kind))
            if kind != "low":
                continue
            for c in cand[f]["x"].get("lowc", []):
                if abs(c["d"] - d) < 0.05 and abs(c["lat"] - lat) < 0.05 and (c.get("reason") == "below_rail_ref" or c["weak"]):
                    fired.append({"f": f, "track": tid, "d": d, "lat": lat, "top": c["top"], "ref": c["ref"],
                                  "cand_reason": c.get("reason"), "cand_weak": c["weak"]})
    n_explained += bool(fired)
    print(json.dumps({"onset": e["onset"], "n": e["n"], "kept": len(kept), "tracks": sorted(ids),
                      "own_hits": len(own), "own_low_hits": sum(1 for o in own if o[4] == "low"),
                      "fired_on_own_hits": fired}))
print(json.dumps({"lost_or_shortened_episodes": n_lost, "explained_by_own_track_hits": n_explained}))
