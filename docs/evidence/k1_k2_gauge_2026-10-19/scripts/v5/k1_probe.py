#!/usr/bin/env python3
"""K1-3 (squareT_platform STOP episodes) and K1-4 (doubleT_obstacle STOP frames) from probe.py outputs.
k1_probe.py <dir> <tag>"""
import json, sys
d, tag = sys.argv[1], sys.argv[2]
def load(b):
    return [json.loads(l) for l in open(f"{d}/{tag}_{b}.jsonl")]
sq = load("squareT_platform_squareT_switch")
stop = [r.get("decision") == "STOP" for r in sq]
eps = [i for i in range(len(stop)) if stop[i] and (i == 0 or not stop[i - 1])]
ob = load("doubleT_obstacle")
so = [i for i, r in enumerate(ob) if r.get("decision") == "STOP"]
print(json.dumps({"tag": tag, "K1-3 squareT_platform STOP episodes": len(eps), "onsets": [(sq[i]["i"], sq[i].get("nearest")) for i in eps],
                  "squareT STOP frames": sum(stop), "K1-4 doubleT_obstacle STOP frames": len(so), "first STOP frame": ob[so[0]]["i"] if so else None,
                  "frames": [len(sq), len(ob)]}))
