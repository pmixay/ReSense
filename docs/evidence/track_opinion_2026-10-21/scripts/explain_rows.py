#!/usr/bin/env python3
"""Every gate row that differs between two work dirs (cmp_frames.py's rule), with the cause traced from the rows:
for each, the detections of A that are a STOP and the advisory of the other run at the same place (distance and
lateral within 1 m), its reason. A row is attributed to the opinion when every STOP that one run has and the
other lacks is an advisory with reason 'doubt' there (and the decisions differ only in that).

    explain_rows.py <work A> <work B> [--out file]
"""
import glob
import json
import os
import sys
from collections import Counter

A, B = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../integration_2026-10-19/scripts"))


def rows(p):
    return [json.loads(line) for line in open(p)]


def key(d):
    return (round(d["distance"], 1), round(d["lateral"], 1))


def strip(r):
    r = dict(r)
    for k in ("timing_ms", "health"):
        r.pop(k, None)
    return r


out, causes = [], Counter()
for fa in sorted(glob.glob(os.path.join(A, "*.jsonl"))):
    name = os.path.basename(fa)
    ra, rb = rows(fa), rows(os.path.join(B, name))
    for i, (x, y) in enumerate(zip(ra, rb)):
        if strip(x) == strip(y):
            continue
        rec = {"file": name, "row": i, "frame_id": x.get("frame_id")}
        for side, s1, s2 in (("A_only_stop", x, y), ("B_only_stop", y, x)):
            only = []
            for d in s1["detections"]:
                if any(abs(d["distance"] - e["distance"]) <= 1 and abs(d["lateral"] - e["lateral"]) <= 1
                       for e in s2["detections"]):
                    continue
                adv = [e.get("reason") for e in s2["warnings"]
                       if abs(d["distance"] - e["distance"]) <= 1 and abs(d["lateral"] - e["lateral"]) <= 1]
                only.append({"d": round(d["distance"], 1), "lat": round(d["lateral"], 2), "id": d.get("id"),
                             "other_run_advisory_reason": adv})
            rec[side] = only
        allonly = rec["A_only_stop"] + rec["B_only_stop"]
        if allonly and all("doubt" in o["other_run_advisory_reason"] for o in allonly):
            cause = "opinion_withheld"
        elif not allonly:
            cause = "no_stop_change"
        else:
            cause = "other"
        rec["cause"] = cause
        causes[cause] += 1
        out.append(rec)
res = {"A": A, "B": B, "rows": len(out), "causes": dict(causes), "detail": out}
txt = json.dumps(res, indent=1)
if len(sys.argv) > 4 and sys.argv[3] == "--out":
    open(sys.argv[4], "w").write(txt)
print(json.dumps({k: res[k] for k in ("rows", "causes")}))
for r in out:
    if r["cause"] != "opinion_withheld":
        print(json.dumps(r)[:400])
