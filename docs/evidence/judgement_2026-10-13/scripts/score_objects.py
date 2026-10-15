#!/usr/bin/env python3
"""Jury scorer for recordings with labelled objects (cloud_with_fake_obj, doubleT_obstacle).

Ground truth rows: labels/<bag>.json (distances verified against the raw points by the jury, see REPORT).
Object intent `in_gauge` = must STOP; out-of-gauge objects must not STOP.
A STOP detection d matches an object row o when
   |d.distance - o.distance| <= max(2 m, 3 % o.distance) + L/2   (L = along-track size)
   and |d.center_Y - o.Y_centre| <= 1.0 m + W/2                 (vehicle frame; W = object width)
(o.Y_centre: centre of the labelled bbox, else the label lateral).
Per object: visible plausible rows, STOP-matched rows, decision in rows (GO/CAUTION/STOP/FAULT), first STOP
distance (farthest matched row in time order), 'held-from' distance = largest D such that the object is
STOP-matched in >= 90 % of its visible plausible rows nearer than D, and per-range-bin recall.
Unmatched STOP frames (STOP detections matching no labelled object row) are false alarms.
usage: score_objects.py <run.jsonl> <labels.json> <out.json> [--rows-only-plausible]
"""
import json
import sys
from collections import defaultdict


run = [json.loads(line) for line in open(sys.argv[1])]
lab = json.load(open(sys.argv[2]))
out_path = sys.argv[3]
BINS = [(0, 30), (30, 60), (60, 100), (100, 150), (150, 200), (200, 300)]


def obj_y(o):
    if "bbox" in o:
        return 0.5 * (o["bbox"][0][1] + o["bbox"][1][1])
    return o.get("lateral_sensor", o.get("lateral", 0.0))


def match(d, o):
    L, W = (o.get("size") or [0.5, 0.5, 0.5])[:2]
    tol_d = max(2.0, 0.03 * o["distance"]) + 0.5 * L
    return abs(d["d"] - o["distance"]) <= tol_d and abs(d["c"][1] - obj_y(o)) <= 1.0 + 0.5 * W


per = defaultdict(lambda: {"rows": [], "in_gauge": None})
unmatched_stop = []
for r in run:
    k = f"{r['i']:05d}"
    objs = [o for o in lab.get(k, []) if o.get("n_points", 1) != 0]
    used = set()
    for o in objs:
        name = o.get("label", o.get("name"))
        P = per[name]
        P["in_gauge"] = o["in_gauge"] if P["in_gauge"] is None else P["in_gauge"]
        hit = [j for j, d in enumerate(r["dets"]) if match(d, o)]
        warn = [d for d in r["warns"] if match(d, o)]
        used.update(hit)
        P["rows"].append({"i": r["i"], "d": o["distance"], "plaus": bool(o.get("plausible", True)),
                          "in_gauge_row": bool(o["in_gauge"]), "stop_hit": bool(hit), "warn_hit": bool(warn),
                          "decision": r["decision"], "n": o.get("n_points")})
    if r["decision"] == "STOP" and any(j not in used for j in range(len(r["dets"]))):
        free = [d for j, d in enumerate(r["dets"]) if j not in used]
        unmatched_stop.append({"i": r["i"], "d": [x["d"] for x in free], "lat": [x["lat"] for x in free],
                               "only_unmatched": len(used) == 0})


def held_from(rows):
    arr = sorted(rows, key=lambda t: t["d"])
    held, hits = None, 0
    for n, t in enumerate(arr, 1):
        hits += t["stop_hit"]
        if hits >= 0.9 * n:
            held = t["d"]
    return held


summary = {}
for name, P in per.items():
    rows = [t for t in P["rows"] if t["plaus"]]
    hits = [t for t in rows if t["stop_hit"]]
    s = {"in_gauge_intent": P["in_gauge"], "rows_all": len(P["rows"]), "rows_plausible": len(rows),
         "stop_rows": len(hits),
         "first_visible_d": round(max(t["d"] for t in rows), 1) if rows else None,
         "first_stop_d": round(hits[0]["d"], 1) if hits else None,
         "first_stop_frame": hits[0]["i"] if hits else None,
         "max_stop_d": round(max(t["d"] for t in hits), 1) if hits else None,
         "held_from_d": held_from(rows) if rows else None,
         "decisions": {k: sum(1 for t in rows if t["decision"] == k) for k in ("GO", "CAUTION", "STOP", "FAULT")},
         "caution_on_object": sum(1 for t in rows if t["warn_hit"] and not t["stop_hit"]),
         "bins": {}}
    for lo, hi in BINS:
        b = [t for t in rows if lo <= t["d"] < hi]
        if b:
            s["bins"][f"{lo}-{hi}"] = f"{sum(t['stop_hit'] for t in b)}/{len(b)}"
    summary[name] = s

# frames with STOP that match no object at all = false STOP frames; episodes
fs = sorted(x["i"] for x in unmatched_stop if x["only_unmatched"])
eps = []
for i in fs:
    if eps and i == eps[-1][1] + 1:
        eps[-1][1] = i
    else:
        eps.append([i, i])
res = {"objects": summary, "unmatched_stop_frames": len(fs), "unmatched_stop_episodes": eps,
       "unmatched_detail": unmatched_stop[:200],
       "decisions_total": {k: sum(1 for r in run if r["decision"] == k) for k in ("GO", "CAUTION", "STOP", "FAULT")}}
json.dump(res, open(out_path, "w"), indent=1)
print(f"{'object':20s} {'gauge':5s} {'rows':>4s} {'STOP':>4s} {'1st vis':>7s} {'1stSTOP':>7s} {'held':>6s}  bins | GO/CAU/STOP")
for name, s in summary.items():
    print(f"{name:20s} {str(s['in_gauge_intent']):5s} {s['rows_plausible']:4d} {s['stop_rows']:4d} {str(s['first_visible_d']):>7s} "
          f"{str(s['first_stop_d']):>7s} {str(s['held_from_d']):>6s}  {s['bins']} | "
          f"{s['decisions']['GO']}/{s['decisions']['CAUTION']}/{s['decisions']['STOP']}")
print("false STOP frames (no labelled object matched):", len(fs), "episodes:", eps)
print("decisions total:", res["decisions_total"])
