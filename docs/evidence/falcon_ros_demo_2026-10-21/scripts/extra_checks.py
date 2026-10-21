#!/usr/bin/env python3
"""extra_checks.py TRIALDIR... : live decisions vs the whole-recording record (l16) and the offline cold replay,
person-track check of every live STOP up to frame 3033, identity of the decision sequences across trials.
Run from the repository root; raw/person_track.json is the output of person_track.py on l16.jsonl.xz."""
import json, lzma, sys
REC = "docs/evidence/l16_acceptance_2026-10-20/out/falcon/l16.jsonl.xz"
COLD = "docs/evidence/falcon_demo_bag_2026-10-20/out/coldstart.jsonl.xz"
rec = {r["i"]: r["decision"] for r in map(json.loads, lzma.open(REC, "rt"))}
cold = [json.loads(l) for l in lzma.open(COLD, "rt")]
person = json.load(open("docs/evidence/falcon_ros_demo_2026-10-21/raw/person_track.json"))
print("positive control: cold replay vs whole-recording record differ on", sum(c["decision"] != rec[c["frame"]] for c in cold), "frames (README: 32)")
base = None
for d in sys.argv[1:]:
    live = {}
    for l in open(f"{d}/events.jsonl"):
        e = json.loads(l)
        if e["topic"] == "status" and e.get("node") and e.get("stamp"):
            c = min(cold, key=lambda c: abs(c["stamp"] - e["stamp"])); live.setdefault(c["frame"], e)
    seq = [(f, live[f]["decision"], None if live[f]["nearest_distance"] is None else round(live[f]["nearest_distance"], 2)) for f in sorted(live)]
    same = "base" if base is None else (seq == base)
    base = base or seq
    stops = [f for f in live if live[f]["decision"] == "STOP" and f <= 3033]
    err = max(abs(live[f]["nearest_distance"] - (person["d0"] + person["d_per_frame"] * f)) for f in stops)
    print(d.rstrip("/").split("/")[-1], "frames", len(live), "| differ from whole-recording record:", sum(live[f]["decision"] != rec[f] for f in live),
          "| STOP", sum(live[f]["decision"] == "STOP" for f in live), "(record on same frames", sum(rec[f] == "STOP" for f in live), ")",
          "| STOP frames <=3033:", len(stops), "max |distance - person line| m:", round(err, 2), "| decision+distance sequence identical to first trial:", same)
