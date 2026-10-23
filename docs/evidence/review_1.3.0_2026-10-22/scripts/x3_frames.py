#!/usr/bin/env python3
"""X3 per frame (reviewer): for every battery entry, the STOP frames of the control's and the candidate's raw
probe rows (robustness_battery.py --out X.json writes X.raw/<bag>/<variant>/probe.jsonl): control STOP frames
not STOP in the candidate (lost), candidate STOP frames not STOP in the control (new), decisions differing.
Positive control: --plant drops one STOP frame from the candidate's rows of the first entry that has one.
    x3_frames.py <control.raw> <cand.raw> [--plant]"""
import glob, json, os, sys
A, B = sys.argv[1], sys.argv[2]; plant = "--plant" in sys.argv
tot = {"entries": 0, "frames": 0, "lost": 0, "new": 0, "dec_diff": 0}; planted = False
for pa in sorted(glob.glob(os.path.join(A, "*", "*", "probe.jsonl"))):
    key = os.path.relpath(os.path.dirname(pa), A); pb = os.path.join(B, key, "probe.jsonl")
    ra = [json.loads(l) for l in open(pa)]; rb = [json.loads(l) for l in open(pb)]
    assert [r["i"] for r in ra] == [r["i"] for r in rb], key
    sa = {r["i"] for r in ra if r["decision"] == "STOP"}; sb = {r["i"] for r in rb if r["decision"] == "STOP"}
    if plant and not planted and sb:
        sb.discard(min(sb)); planted = True
    lost, new = sorted(sa - sb), sorted(sb - sa)
    dd = sum(x["decision"] != y["decision"] for x, y in zip(ra, rb))
    tot["entries"] += 1; tot["frames"] += len(ra); tot["lost"] += len(lost); tot["new"] += len(new); tot["dec_diff"] += dd
    if lost or new or dd:
        print(key, "lost", lost[:10], "new", new[:10], "decisions differ", dd)
print(json.dumps(tot))
