#!/usr/bin/env python3
"""B6-1 honesty for control / cand of every recording, both truths: the committed B6 poses (poses_<bag>.json) and
the validity-filtered ones (every ICP step with forward motion < -0.05 m turned into a segment break, PROTOCOL of
k1_k2_gauge_2026-10-19 §3). Track rows from gauge_stability.py track (the published model), monitored range from the
nominal probe.py run of the same tree.

    b6_honesty.py <b6 dir> <poses dir> <out.json> <recordings...>
"""
import json
import os
import subprocess
import sys

G = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../scripts/gauge_stability.py")
d, pdir, outp, bags = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
res = {}
for b in bags:
    p = json.load(open(os.path.join(pdir, f"poses_{b}.json")))
    rows = []
    for r in p["rows"]:
        r = dict(r)
        if r.get("T") is not None and r["T"][0][3] < -0.05:
            r["T"] = None
        rows.append(r)
    pv = os.path.join(d, f"posesV_{b}.json")
    json.dump(dict(p, rows=rows), open(pv, "w"))
    for tag in ("control", "cand1"):
        for truth, pp in (("B6", os.path.join(pdir, f"poses_{b}.json")), ("valid", pv)):
            o = os.path.join(d, f"honesty_{truth}_{tag}_{b}.json")
            subprocess.run([sys.executable, G, "honesty", os.path.join(d, f"track_{tag}_{b}.json"), pp,
                            os.path.join(d, f"run_{tag}_{b}.jsonl"), o], check=True, capture_output=True)
            res.setdefault(b, {}).setdefault(truth, {})[tag] = json.load(open(o))
json.dump(res, open(outp, "w"), indent=1)
for b, r in res.items():
    for truth, t in r.items():
        print(f"{b[:30]:30s} {truth:5s} inside>1.05m control {t['control']['inside_over_1.05m']} cand {t['cand1']['inside_over_1.05m']}"
              f"  (steps {t['control']['steps_inside']} / {t['cand1']['steps_inside']})")
