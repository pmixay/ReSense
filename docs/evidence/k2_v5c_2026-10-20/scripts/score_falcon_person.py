"""Proposal (not registered; post-hoc, for the captain): score the Falcon walking person by where it is, not by which
frames the reference STOPs in. The person's position per frame (distance, vehicle Y) is taken from the reference run
(K2 off): its STOP detections in the person frames of score_falcon_pos.py (base STOP frames minus the four attributed
false ones), and, in the other frames between the person's first and last such frame, its detection or warning
nearest the line through the neighbouring STOP positions (within 3 m in distance, 0.6 m in Y); before the first STOP,
back to 60 frames earlier, the same along the line fitted to the first 30 STOP positions (the person is in view and a
warning there); after the last STOP, the line fitted to the last 30 down to 2.5 m. The STOP anchor is the detection
nearest the previous anchor (continuity; a nearer second object in the frame is not the person). A position carries
the reference cluster's length: a 2-4 m merge's near face lies up to ~2.5 m before the person. A candidate frame is a person STOP frame when it is a STOP with a STOP detection from 1.5 m before that
position to 1.5 m beyond the reference cluster's far end whose lateral extent (vehicle Y +- width / 2, + 0.3 m) contains the position's Y: a 2-2.7 m
wide merge with structure (README section 1) still counts as the person. Prints: person frames, the first person STOP (frame, distance) of the reference and the candidate, person
STOP frames, and the candidate's STOP frames that are not on the person (the ones to explain).

    python -I score_falcon_person.py <reference.jsonl> <candidate.jsonl> ...
"""
import json
import sys

import numpy as np

FALSE = {159, 2312, 2313, 2314} | set(range(4394, 4402))
ref = [json.loads(line) for line in open(sys.argv[1])]
stops = {r["i"]: r for r in ref if r["decision"] == "STOP" and r["i"] not in FALSE and r["i"] > 2900}
anchors, prev = {}, None
for i in sorted(stops):
    dets = stops[i]["dets"]
    if not dets:
        continue
    # the person by continuity: the detection nearest the previous anchor (the first: the farthest, the approaching
    # person; a nearer object in the same frame is not it)
    d = (max(dets, key=lambda e: e["d"]) if prev is None
         else min(dets, key=lambda e: abs(e["d"] - prev["d"]) + abs(e["c"][1] - prev["c"][1])))
    if prev is not None and abs(d["d"] - prev["d"]) > 6.0:
        continue
    anchors[i], prev = d, d
ai = np.array(sorted(anchors))
ad = np.array([anchors[i]["d"] for i in ai])
ay = np.array([anchors[i]["c"][1] for i in ai])
pos = {int(i): (anchors[i]["d"], anchors[i]["c"][1], anchors[i]["size"][0]) for i in ai}
pd0, py0 = np.polyfit(ai[:30], ad[:30], 1), np.polyfit(ai[:30], ay[:30], 1)
pd1, py1 = np.polyfit(ai[-30:], ad[-30:], 1), np.polyfit(ai[-30:], ay[-30:], 1)
for i in range(int(ai[0]) - 60, min(int(ai[-1]) + 40, len(ref))):
    if i in pos:
        continue
    if i < ai[0]:
        d0, y0 = float(np.polyval(pd0, i)), float(np.polyval(py0, i))
    elif i > ai[-1]:
        d0, y0 = float(np.polyval(pd1, i)), float(np.polyval(py1, i))
        if d0 < 2.5:
            break
        pos[i] = (d0, y0, 0.5)          # beyond the reference's last STOP: the line itself
        continue
    else:
        d0, y0 = float(np.interp(i, ai, ad)), float(np.interp(i, ai, ay))
    c = [(abs(d["d"] - d0), d) for d in ref[i]["dets"] + ref[i]["warns"] if abs(d["d"] - d0) <= 3 and abs(d["c"][1] - y0) <= 0.6]
    pos[i] = ((lambda d: (d["d"], d["c"][1], d["size"][0]))(min(c, key=lambda t: t[0])[1]) if c else (d0, y0, 0.5))


def score(rows):
    on = sorted(i for i, (d0, y0, ln) in pos.items() if rows[i]["decision"] == "STOP"
                and any(d0 - 1.5 <= d["d"] <= d0 + ln + 1.5 and abs(d["c"][1] - y0) <= d["size"][1] / 2 + 0.3
                        for d in rows[i]["dets"]))
    off = sorted(r["i"] for r in rows if r["decision"] == "STOP" and r["i"] not in on)
    first = (on[0], round(pos[on[0]][0], 2)) if on else None
    return first, on, off


print(f"person frames: {len(pos)} ({min(pos)}-{max(pos)}), of them reference STOP anchors {len(anchors)}")
for p in sys.argv[1:]:
    rows = [json.loads(line) for line in open(p)]
    first, on, off = score(rows)
    print(f"{p}\n  first person STOP {first}; person STOP frames {len(on)}; STOP frames not on the person {len(off)}: "
          f"{off[:40]}")
