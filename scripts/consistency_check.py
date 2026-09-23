#!/usr/bin/env python3
"""Is a change's gain spread over the data, or carried by one recording?

The detector's parameters were tuned on the same 13 759 frames they are scored on (there is no
held-out obstacle data). This compares two ``scripts/eval_real.py`` runs subset by subset - the
five obstacle-free recordings and the eight files (about 2.5 minutes each) of the 20-minute
ride - and asks, leaving one subset out at a time, whether the change would still have been
chosen on the rest: fewer alarm events there, and the real obstacles in ``doubleT_obstacle``
still found. A gain that survives every leave-one-out and shows up in most subsets is not an
artefact of one stretch of track.

    python scripts/consistency_check.py RUNS/v061 RUNS/v062 [--json out.json]
"""
from __future__ import annotations

import argparse
import glob
import json
import os

EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]
LABELS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "labels", "doubleT_obstacle.json")


def events(path):
    """(frames, alarm frames, alarm events = distinct confirmed track ids, as scripts/eval_real.py)"""
    n = frames = 0
    ids = set()
    for line in open(path):
        d = json.loads(line)
        frames += 1
        if d["obstacle"]:
            n += 1
            ids.update(x["id"] for x in d["detections"])
    return frames, n, len(ids)


def obstacle_hits(run):
    """frames in which each labelled in-envelope object of doubleT_obstacle is detected"""
    lab = json.load(open(LABELS))
    hits = {}
    for line in open(os.path.join(run, "doubleT_obstacle.jsonl")):
        d = json.loads(line)
        for r in lab.get(f"{d['frame']:05d}", []):
            if not r.get("in_gauge") or r.get("n_points", 1) == 0:
                continue
            h = hits.setdefault(r["label"], [0, 0])
            h[1] += 1
            if any(abs(x["distance"] - r["distance"]) < 1.5 and abs(x["lateral"] - r["lateral"]) < 1.0
                   for x in d["detections"]):
                h[0] += 1
    return hits


def subsets(run):
    out = {}
    for b in EMPTY:
        out[b] = events(os.path.join(run, b + ".jsonl"))
    for p in sorted(glob.glob(os.path.join(run, "new_data_*.jsonl")), key=lambda s: int(s.rsplit("_", 1)[1][:-6])):
        out["ride part " + p.rsplit("_", 1)[1][:-6]] = events(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("base")
    ap.add_argument("cand")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    A, B = subsets(a.base), subsets(a.cand)
    ha, hb = obstacle_hits(a.base), obstacle_hits(a.cand)
    keep_obstacles = all(hb.get(k, [0])[0] >= 0.95 * v[0] for k, v in ha.items())
    rows, better, worse = [], 0, 0
    print(f"{'subset':38s} {'frames':>6s}  events {os.path.basename(a.base):>8s} -> {os.path.basename(a.cand):<8s}"
          f"  leave-this-out: rest {os.path.basename(a.base)} -> {os.path.basename(a.cand)}, chosen?")
    tot_a = sum(v[2] for v in A.values())
    tot_b = sum(v[2] for v in B.values())
    for k in A:
        fa, fb = A[k][2], B[k][2]
        better += fb < fa
        worse += fb > fa
        ra, rb = tot_a - fa, tot_b - fb
        chosen = rb < ra and keep_obstacles
        rows.append({"subset": k, "frames": A[k][0], "events_base": fa, "events_cand": fb,
                     "alarm_frames_base": A[k][1], "alarm_frames_cand": B[k][1],
                     "rest_base": ra, "rest_cand": rb, "chosen_without_it": chosen})
        print(f"{k:38s} {A[k][0]:6d}  {fa:8d} -> {fb:<8d}  {ra:5d} -> {rb:<5d} {'yes' if chosen else 'NO'}")
    print(f"{'all':38s} {sum(v[0] for v in A.values()):6d}  {tot_a:8d} -> {tot_b:<8d}")
    print(f"subsets with fewer events: {better}, more: {worse}, equal: {len(A) - better - worse}")
    print("real obstacles (frames found / in the envelope):",
          {k: f"{ha[k][0]}/{ha[k][1]} -> {hb.get(k, [0, 0])[0]}/{hb.get(k, [0, 0])[1]}" for k in ha})
    if a.json:
        json.dump({"base": a.base, "cand": a.cand, "rows": rows, "fewer": better, "more": worse,
                   "obstacles_base": ha, "obstacles_cand": hb,
                   "chosen_in_every_leave_one_out": all(r["chosen_without_it"] for r in rows)},
                  open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
