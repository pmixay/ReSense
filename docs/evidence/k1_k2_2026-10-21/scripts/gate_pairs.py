#!/usr/bin/env python3
"""Paired per-frame diff of two regression-gate work directories (control vs candidate): per recording file, STOP
frames lost / gained, frames whose detections changed, and every gained STOP frame with its new detections (distance,
lateral, centre, size) and the control's detections / warnings of that frame; STOP episodes (runs of obstacle frames)
that are new (no control STOP within 3 frames).

    gate_pairs.py <work control> <work cand> <out.json>
"""
import glob
import json
import os
import sys

A, B, OUT = sys.argv[1:4]


def load(p):
    return [json.loads(line) for line in open(p)]


def det(d):
    return {"d": round(d["distance"], 2), "lat": round(d["lateral"], 2), "c": [round(v, 2) for v in d["center"]],
            "size": [round(v, 2) for v in d["size"]], "zone": d["zone"], "reason": d.get("reason", ""),
            "kind": d.get("kind", "")}


def episodes(stops):
    out, prev = [], None
    for i in sorted(stops):
        if prev is None or i != prev + 1:
            out.append([i, i])
        else:
            out[-1][1] = i
        prev = i
    return out


report = {}
for fa in sorted(glob.glob(os.path.join(A, "*.jsonl"))):
    name = os.path.basename(fa)
    ra, rb = load(fa), load(os.path.join(B, name))
    assert len(ra) == len(rb) and all(x["stamp"] == y["stamp"] for x, y in zip(ra, rb)), name
    sa = {i for i, r in enumerate(ra) if r["obstacle"]}
    sb = {i for i, r in enumerate(rb) if r["obstacle"]}
    ch = [i for i, (x, y) in enumerate(zip(ra, rb))
          if (x["obstacle"], [det(d) for d in x["detections"]]) != (y["obstacle"], [det(d) for d in y["detections"]])]
    new_eps = [e for e in episodes(sb) if not any(e[0] - 3 <= i <= e[1] + 3 for i in sa)]
    gained = []
    for i in sorted(sb - sa):
        old = {(round(d["distance"], 2), round(d["lateral"], 2)) for d in ra[i]["detections"]}
        gained.append({"frame": i, "new": [det(d) for d in rb[i]["detections"]
                                            if (round(d["distance"], 2), round(d["lateral"], 2)) not in old],
                       "control_dets": [det(d) for d in ra[i]["detections"]],
                       "control_warns": [det(d) for d in ra[i]["warnings"]]})
    report[name] = {"frames": len(ra), "stop": [len(sa), len(sb)], "lost": sorted(sa - sb), "gained": gained,
                    "changed_frames": ch, "new_episodes": new_eps,
                    "episodes": [len(episodes(sa)), len(episodes(sb))]}
json.dump(report, open(OUT, "w"), indent=1)
for n, r in report.items():
    if r["lost"] or r["gained"] or r["changed_frames"]:
        print(f"{n:42s} stop {r['stop']} episodes {r['episodes']} lost {r['lost']} gained {[g['frame'] for g in r['gained']]}"
              f" changed {len(r['changed_frames'])} new episodes {r['new_episodes']}")
