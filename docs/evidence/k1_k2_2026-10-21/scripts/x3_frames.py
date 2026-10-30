#!/usr/bin/env python3
"""X3 per frame: for each of the 40 cases, control vs cand raw probe records (decision per frame and every STOP
detection), listing STOP frames lost / gained; a planted loss is found.

    x3_frames.py <control.raw> <cand.raw> <out.json>
"""
import copy
import json
import sys
from pathlib import Path

a, b = Path(sys.argv[1]), Path(sys.argv[2])
out, tot = {}, {"lost": 0, "gained": 0, "changed_frames": 0}


def load(p):
    return [json.loads(line) for line in open(p)]


def diff(ra, rb):
    assert [r["i"] for r in ra] == [r["i"] for r in rb]
    sa = {r["i"] for r in ra if r["decision"] == "STOP"}
    sb = {r["i"] for r in rb if r["decision"] == "STOP"}
    ch = [x["i"] for x, y in zip(ra, rb) if (x["decision"], x["dets"]) != (y["decision"], y["dets"])]
    return sorted(sa - sb), sorted(sb - sa), ch


first = None
for pa in sorted(a.glob("*/*/probe.jsonl")):
    case = f"{pa.parent.parent.name}/{pa.parent.name}"
    ra, rb = load(pa), load(b / pa.relative_to(a))
    lost, gained, ch = diff(ra, rb)
    out[case] = {"lost": lost, "gained": gained, "changed_frames": ch}
    tot["lost"] += len(lost)
    tot["gained"] += len(gained)
    tot["changed_frames"] += len(ch)
    if first is None and any(r["decision"] == "STOP" for r in ra):
        first = (case, ra)
case, ra = first
pl = copy.deepcopy(ra)
k = next(r["i"] for r in pl if r["decision"] == "STOP")
next(r for r in pl if r["i"] == k)["decision"] = "GO"
tot["planted"] = {"case": case, "frame": k, "found": k in diff(ra, pl)[0]}
tot["cases"] = len(out)
json.dump({"total": tot, "cases": out}, open(sys.argv[3], "w"), indent=1)
print(json.dumps(tot))
for c, r in out.items():
    if r["lost"] or r["gained"] or r["changed_frames"]:
        print(c, "lost", r["lost"], "gained", r["gained"], "changed", r["changed_frames"][:20], len(r["changed_frames"]))
