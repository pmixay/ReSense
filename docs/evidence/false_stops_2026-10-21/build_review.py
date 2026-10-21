#!/usr/bin/env python3
"""Merge the snapshot review (every PNG of png/ looked at by the author, 37 of 37) into snapshot_review.json and write
ambiguous_for_human.md: the episodes a human should confirm (the script's own flags plus the review's).

    python docs/evidence/false_stops_2026-10-21/build_review.py docs/evidence/false_stops_2026-10-21
"""
import json
import os
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
led = json.load(open(os.path.join(OUT, "ledger.json")))

# id -> (verdict on the class from the PNG, what the pass-by picture shows, human confirmation wanted: why or "")
R = {}
def put(ids, verdict, shows, human=""):
    for i in ids.split():
        R[i] = (verdict, shows, human)

S = "squareT_platform_squareT_switch:"
put(f"{S}312 {S}316", "agree (boundary)", "platform edge / kerb at |dy| 1.42 m, h 0.3 m, along the track on the right: exactly at the 1.4 m limit",
    "platform kerb at the limit: in-envelope or side?")
put(f"{S}437 {S}490 {S}522 {S}527", "agree", "the first wall of the diverging track (switch) on the right, 2.0-2.9 m from the axis, 83 m at onset",
    "")
put(f"{S}500 {S}580 {S}640 {S}692", "agree", "straight tunnel at 19-28 m, the position is on the right wall (|dy| 2.2 m): the far axis (curvature 2.5e-4) had put it 3 m sideways",
    "wall, no object: confirm there is nothing on the wall")
put(f"{S}612", "agree", "wall / platform side at dy 1.9 m in the straight tunnel", "")
put("new_data:23", "agree", "right wall of the straight tunnel (|dy| 2.3 m) at the position: far axis 1.7 m off", "wall, no object: confirm")
put("new_data:1378 new_data:1393", "agree", "row of columns (vertical stripes) of a multi-track station at dy 1.7 m; the onset box is tall and thin (1.9 x 0.3 m)", "")
put("new_data:1847 new_data:5065", "agree", "the same column row (dy 1.7 m); a tall thin object at onset, 136-155 m", "")
put("new_data:2668", "agree (boundary)", "low ledge at dy 1.43 m, h 0.2-0.3 m, 42 m at onset (a low object)", "low kerb at the 1.4 m limit")
put("new_data:2729", "agree", "a large dense block in the gauge ahead (30 000 returns in the window): another train or station equipment in front of the train", "real in-envelope structure? what is it")
put("new_data:3060", "agree", "wide-station wall rows at dy 2.0 m", "")
put("new_data:5699", "agree", "left gallery wall with openings at dy -1.9 m", "")
put("new_data:5716 new_data:5901 new_data:6859 new_data:10486", "agree (boundary)", "low kerb / ledge near the 1.4 m limit (h 0.2-0.5 m)", "low kerb at the limit")
put("new_data:7338 new_data:7347", "agree", "left wall / trough at dy -1.7 m", "")
put("new_data:7859 new_data:7868", "agree", "right wall in a gentle curve (dy 2.0 m): the 5.5-6.0 m long onset clusters (K2's mid-range edge episodes) are the wall", "")
put("new_data:7943 new_data:9263 new_data:9271 new_data:9284", "agree (rests on odometry)",
    "tunnel straight at the pass-by, the carried position is 7-9 m beside it, in the rock: nothing can be seen there; the class rests on the transport "
    "(the onset axis curved 7-9 m away, the real tunnel does not)", "side by position: nothing seen; confirm by the far frames")
put("new_data:9125", "agree", "column / wall row at dy -1.8 m, h 0.9 m", "")
put("new_data:9786", "agree (nothing there)", "at the carried position only bed and rails: the 0.1 x 0.45 x 0.24 m onset cluster is not there at 19 m", "bed fitting or a phantom?")
put("new_data:9800", "agree", "left wall at dy -1.84 m, h 2.0 m", "")
put("new_data:10644 new_data:10648", "agree (boundary)", "long low continuous ledge on the track side (dy 1.4-1.8 m, h 0.3-0.9 m); the onset boxes are 5.7 x 2.1 x 0.2 and 7.9 x 1.9 x 0.6 m", "long low ledge: object or fabric?")

rows, human = [], []
for e in led["episodes"]:
    pb = e["passby"]
    v, shows, why = R[e["id"]]
    rows.append({"id": e["id"], "class": pb["class"], "script_ambiguous": pb["ambiguous_why"], "review_verdict": v,
                 "picture_shows": shows, "human_confirm": why})
    if why or pb["ambiguous"]:
        human.append((e, pb, v, shows, why))
json.dump({"reviewed": len(rows), "agree": sum(r["review_verdict"].startswith("agree") for r in rows),
           "disagree": sum(not r["review_verdict"].startswith("agree") for r in rows),
           "note": "verdicts by the author from png/<id>.png (BEV and side, onset and pass-by); not a human confirmation",
           "rows": rows}, open(os.path.join(OUT, "snapshot_review.json"), "w"), indent=1)
with open(os.path.join(OUT, "ambiguous_for_human.md"), "w", encoding="utf-8") as fh:
    fh.write("# Episodes whose class a human should confirm\n\n"
             "The script flags an episode when the evaluated frames disagree, the structure is the tunnel surface itself, the points are few, "
             "the structure sits at a limit (|dy| 1.4 m, h 3.0 m), or the class rests on the carried position alone. "
             "The review adds the episodes whose picture leaves the question open. One picture per row: `png/<id>.png`.\n\n"
             "| episode | onset | class | what the picture shows | script flags | the question |\n|---|---|---|---|---|---|\n")
    for e, pb, v, shows, why in human:
        fh.write(f"| {e['id']} | {e['distance']:.0f} m, lat {e['lateral']:+.1f} | {pb['class']} | {shows} | "
                 f"{', '.join(pb['ambiguous_why']) or '-'} | {why or 'script flag only'} |\n")
print(len(rows), "rows;", len(human), "for a human")
