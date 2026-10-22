#!/usr/bin/env python3
"""Attack jobs (attack_range.sh): candidate vs control at the same placement. Per job: object-matching STOP frames
(hit), node-decision STOP frames anywhere, frames lost / new for both, first STOP X.
    cmp_attack.py <attack_dir>"""
import json, os, sys
d = sys.argv[1]
out = {}
print(f"{'job':18s} {'ctl hit/STOP/first':>20s} {'cand hit/STOP/first':>20s}  hit lost/new  STOPdec lost/new")
for f in sorted(os.listdir(os.path.join(d, "cand"))):
    if not f.endswith(".json") or not os.path.exists(os.path.join(d, "ctlatcand", f)):
        continue
    a = json.load(open(os.path.join(d, "ctlatcand", f)))["rows"]
    b = json.load(open(os.path.join(d, "cand", f)))["rows"]
    ha = {r["k"] for r in a if r.get("hit")}; hb = {r["k"] for r in b if r.get("hit")}
    sa = {r["k"] for r in a if r.get("decision") == "STOP"}; sb = {r["k"] for r in b if r.get("decision") == "STOP"}
    fa = min((r["X"] for r in a if r.get("hit")), default=None) if False else next((r["X"] for r in a if r.get("hit")), None)
    fb = next((r["X"] for r in b if r.get("hit")), None)
    out[f[:-5]] = dict(hit_lost=sorted(ha - hb), hit_new=sorted(hb - ha), stop_lost=sorted(sa - sb), stop_new=sorted(sb - sa),
                       ctl=(len(ha), len(sa), fa), cand=(len(hb), len(sb), fb))
    print(f"{f[:-5]:18s} {len(ha):5d}/{len(sa):4d}/{fa!s:>7s} {len(hb):5d}/{len(sb):4d}/{fb!s:>7s}  {len(ha-hb):3d}/{len(hb-ha):3d}  {len(sa-sb):3d}/{len(sb-sa):3d} {sorted(sb-sa)[:10]}")
json.dump(out, open(os.path.join(d, "cmp_attack.json"), "w"), indent=1)
