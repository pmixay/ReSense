"""Per marked object: frames where a detection (any decision) / a STOP detection / a warning matches the object's
marker box in the same frame (rule of stops_vs_markers.py: near face within max(3 m, 3 %), vehicle lateral c[1]
within 1.5 m of the box's lateral centre). Only frames with the box's near face in 2.5-250 m.
    python per_object.py <markers.jsonl> <runA.jsonl> <runB.jsonl> [object_id ...]"""
import json, sys
import numpy as np
mk = {}
for line in open(sys.argv[1]):
    r = json.loads(line)
    mk[r["i"]] = [{"id": m["id"], "near": float(-m["pts_max"][1]), "lat": float((m["pts_min"][0] + m["pts_max"][0]) / 2),
                   "dust": bool((np.array(m["pts_max"]) - np.array(m["pts_min"])).max() < 0.1)}
                  for m in r["markers"] if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]]
runs = [[json.loads(l) for l in open(p)] for p in sys.argv[2:4]]
def hit(d, b):
    return abs(d["d"] - b["near"]) <= max(3.0, 0.03 * b["near"]) and abs(d["c"][1] - b["lat"]) <= 1.5
stats = {}
for i, boxes in mk.items():
    for b in boxes:
        if b["dust"] or not 2.5 <= b["near"] <= 250.0:
            continue
        s = stats.setdefault(b["id"], {"frames": 0, "A": {"det": [], "stop": [], "warn": []}, "B": {"det": [], "stop": [], "warn": []}})
        s["frames"] += 1
        for k, run in zip("AB", runs):
            r = run[i]
            if any(hit(d, b) for d in r["dets"]):
                s[k]["det"].append(i)
                if r["decision"] == "STOP":
                    s[k]["stop"].append(i)
            if any(hit(d, b) for d in r["warns"]):
                s[k]["warn"].append(i)
near = {(i, b["id"]): b["near"] for i, bs in mk.items() for b in bs}
print(f"{'id':>4} {'frames':>6} | {'A det':>5} {'A stop':>6} {'A warn':>6} {'A 1st stop m':>12} | {'B det':>5} {'B stop':>6} {'B warn':>6} {'B 1st stop m':>12}")
for oid, s in sorted(stats.items()):
    f = lambda k: near[(min(s[k]["stop"]), oid)] if s[k]["stop"] else float("nan")
    print(f"{oid:>4} {s['frames']:>6} | {len(s['A']['det']):>5} {len(s['A']['stop']):>6} {len(s['A']['warn']):>6} {f('A'):>12.1f} | "
          f"{len(s['B']['det']):>5} {len(s['B']['stop']):>6} {len(s['B']['warn']):>6} {f('B'):>12.1f}")
    lost = sorted(set(s["A"]["stop"]) - set(s["B"]["stop"])); gained = sorted(set(s["B"]["stop"]) - set(s["A"]["stop"]))
    if lost or gained:
        print(f"      STOP lost in B: {lost}\n      STOP gained in B: {gained}")
