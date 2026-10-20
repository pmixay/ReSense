#!/usr/bin/env python3
"""Every STOP frame of a Falcon stream classified against the raw-reviewed person trajectory
(n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json, main_approach anchors, no detector input):
a STOP whose nearest distance is within 3 m of the trajectory's distance at that frame (linear between anchors,
frames 2500 on) is the person; the rest are listed.   falcon_person_match.py <atlas.json> <run.jsonl> ..."""
import json
import sys

import numpy as np

atlas = json.load(open(sys.argv[1]))["anchors"]
pts = sorted((a["frame"], a["discovery_center"][0]) for a in atlas if a["episode"] == "main_approach")
fa, xa = np.array([p[0] for p in pts]), np.array([p[1] for p in pts])
for path in sys.argv[2:]:
    run = [json.loads(l) for l in open(path)]
    person, other = [], []
    for r in run:
        if r["decision"] != "STOP":
            continue
        i = r["i"]
        ok = fa[0] <= i <= fa[-1] and r["nearest"] is not None and abs(r["nearest"] - float(np.interp(i, fa, xa))) <= 3.0
        (person if ok else other).append(r)
    first = min(person, key=lambda r: r["i"]) if person else None
    groups = {}
    for r in other:
        key = round(r["nearest"] or -1)
        groups.setdefault(key, []).append(r["i"])
    print(json.dumps({"run": path.split("/")[-1], "stop": len(person) + len(other), "person_match": len(person),
                      "first_person_stop": None if first is None else [first["i"], first["nearest"]],
                      "other": {str(k): [len(v), v[0], v[-1]] for k, v in sorted(groups.items())}}))
