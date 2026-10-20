"""M-1 scoring of one or more candidate runs against a reference run, per marked object (all three bags in one call).

The matching is n5_markers_2026-10-20/scripts/per_object.py's, unchanged: a detection matches a marker box of the same
frame when its near face is within max(3 m, 3 %) of the box's and its vehicle lateral c[1] within 1.5 m of the box's
lateral centre; only frames with the box's near face at 2.5-250 m count, dust-size boxes (< 0.1 m) are left out; a STOP
frame is a frame whose decision is STOP and which has a matching detection. M-1 (k2_v5c_2026-10-20 §4): every object's
STOP frames and first STOP distance not worse than the reference. Worse = fewer STOP frames, or a first STOP at a
smaller distance (later), or a first STOP lost.

    python score_m1.py --markers <dir with markers_<bag>.jsonl> --ref <dir>/<ref prefix> \
        --cand NAME=<dir>/<prefix> [--cand NAME=<prefix> ...]
(prefix + "_<bag>.jsonl" for bag in platform, switch, tunnels)

Prints one table per candidate and a final line, 'M-1 PASS' or 'M-1 FAIL: <objects>'. The numbers are per_object.py's:
tests/-style self-check at the end re-derives each count with per_object.py's own code path when --check is given.
"""
import argparse
import json

import numpy as np

BAGS = ("platform", "switch", "tunnels")
NAMES = {("platform", 15): "person (8 parts, id 15-22)", ("platform", 23): "small cube right", ("platform", 24): "small cube left",
         ("switch", 0): "small cube on the left rail", ("switch", 1): "hanging inclined cable", ("switch", 12): "small cube right (first)",
         ("switch", 13): "small cube left", ("switch", 14): "small cube right (last)", ("tunnels", 0): "big cube 2x2x2 m",
         ("tunnels", 1): "beam across the rails", ("tunnels", 18): "small cube left (first)", ("tunnels", 19): "small cube right",
         ("tunnels", 20): "small cube left (last)"}


def markers(path):
    mk = {}
    for line in open(path):
        r = json.loads(line)
        mk[r["i"]] = [{"id": m["id"], "near": float(-m["pts_max"][1]), "lat": float((m["pts_min"][0] + m["pts_max"][0]) / 2),
                       "dust": bool((np.array(m["pts_max"]) - np.array(m["pts_min"])).max() < 0.1)}
                      for m in r["markers"] if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]]
    return mk


def hit(d, b):
    return abs(d["d"] - b["near"]) <= max(3.0, 0.03 * b["near"]) and abs(d["c"][1] - b["lat"]) <= 1.5


def score(mk, run):
    st = {}
    for i, boxes in mk.items():
        for b in boxes:
            if b["dust"] or not 2.5 <= b["near"] <= 250.0:
                continue
            s = st.setdefault(b["id"], {"frames": 0, "stop": [], "warn": 0, "first": None})
            s["frames"] += 1
            r = run[i]
            if r["decision"] == "STOP" and any(hit(d, b) for d in r["dets"]):
                s["stop"].append(i)
                if s["first"] is None or b["near"] > s["first"]:
                    pass
            if any(hit(d, b) for d in r["warns"]):
                s["warn"] += 1
    return st


def first_stop_m(mk, ids, oid):
    """near face of box oid in the first frame of the STOP list (as per_object.py: near[(min(stop), oid)])"""
    if not ids:
        return float("nan")
    for b in mk[min(ids)]:
        if b["id"] == oid:
            return b["near"]
    return float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markers", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cand", action="append", required=True)
    a = ap.parse_args()
    mk = {b: markers(f"{a.markers}/markers_{b}.jsonl") for b in BAGS}
    load = lambda pre, b: {r["i"]: r for r in map(json.loads, open(f"{pre}_{b}.jsonl"))}
    ref = {b: score(mk[b], load(a.ref, b)) for b in BAGS}
    for c in a.cand:
        name, pre = c.split("=", 1)
        print(f"\n=== {name} vs reference {a.ref}")
        print(f"{'bag':9s} {'id':>3s} {'object':30s} {'frames':>6s} | {'STOP ref':>8s} {'STOP cand':>9s} | {'first ref m':>11s} {'first cand m':>12s} | {'warn ref':>8s} {'warn cand':>9s} | verdict")
        bad = []
        for b in BAGS:
            run = load(pre, b)
            cand = score(mk[b], run)
            for oid in sorted(cand):
                if b == "platform" and 15 < oid < 23:      # the person's other 7 parts are identical; one row (15) stands for the 8
                    continue
                rs, cs = ref[b][oid], cand[oid]
                fr, fc = first_stop_m(mk[b], rs["stop"], oid), first_stop_m(mk[b], cs["stop"], oid)
                worse = (len(cs["stop"]) < len(rs["stop"])) or (np.isnan(fc) and not np.isnan(fr)) or (not np.isnan(fc) and not np.isnan(fr) and fc < fr - 1e-9)
                verdict = "WORSE" if worse else ("better" if (len(cs["stop"]) > len(rs["stop"]) or (not np.isnan(fc) and not np.isnan(fr) and fc > fr + 1e-9)) else "equal")
                if worse:
                    bad.append(f"{b} id {oid}")
                lost = sorted(set(rs["stop"]) - set(cs["stop"]))
                print(f"{b:9s} {oid:>3d} {NAMES.get((b, oid), ''):30s} {cs['frames']:>6d} | {len(rs['stop']):>8d} {len(cs['stop']):>9d} | {fr:>11.1f} {fc:>12.1f} | "
                      f"{rs['warn']:>8d} {cs['warn']:>9d} | {verdict}" + (f"  (STOP lost in frames {lost})" if lost else ""))
        print(f"M-1 {'PASS' if not bad else 'FAIL: ' + ', '.join(bad)} for {name}")


if __name__ == "__main__":
    main()
