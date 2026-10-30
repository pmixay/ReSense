#!/usr/bin/env python3
"""Rows ID and M-1 of PROTOCOL.md §3 for one marked bag: judge-runner records of control / off / cand.

* alignment: equal length, frame index, header stamp, bag time (fails closed);
* ID: off vs control, every field except timing (decode_ms, detect_ms, total_ms) and the health level / messages of
  rows where either side carries a latency message;
* M-1: per marked non-dust object (box near face 2.5-250 m), the frames where a STOP detection matches it
  (rule of n5_markers per_object.py: near face within max(3 m, 3 %), vehicle lateral c[1] within 1.5 m of the box's
  lateral centre); lost = control - cand; first STOP distance; every new cand STOP frame must have a STOP detection
  matching some marked box (dust boxes included) of that frame.
Controls: control vs itself 0 lost; a planted loss (one control STOP frame of an object set to GO) is found.

    score_markers.py <markers.jsonl> <control.jsonl> <off.jsonl> <cand.jsonl> <out.json>
"""
import copy
import json
import sys

import numpy as np

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    return [json.loads(line) for line in open(p)]


def boxes_of(markers):
    mk = {}
    for line in open(markers):
        r = json.loads(line)
        mk[r["i"]] = [{"id": m["id"], "near": float(-m["pts_max"][1]), "lat": float((m["pts_min"][0] + m["pts_max"][0]) / 2),
                       "dust": bool((np.array(m["pts_max"]) - np.array(m["pts_min"])).max() < 0.1)}
                      for m in r["markers"] if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]]
    return mk


def hit(d, b):
    return abs(d["d"] - b["near"]) <= max(3.0, 0.03 * b["near"]) and abs(d["c"][1] - b["lat"]) <= 1.5


def lat_msg(r):
    return any("latency" in m for m in r.get("msgs", []))


def identity(a, b):
    out = []
    for x, y in zip(a, b):
        sx = {k: v for k, v in x.items() if k not in TIMING}
        sy = {k: v for k, v in y.items() if k not in TIMING}
        if lat_msg(x) or lat_msg(y):
            for s in (sx, sy):
                for k in ("level", "dlevel", "msgs"):
                    s.pop(k, None)
        if sx != sy:
            out.append(x["i"])
    return out


def per_object(mk, run):
    st = {}
    for i, bs in mk.items():
        for b in bs:
            if b["dust"] or not 2.5 <= b["near"] <= 250.0:
                continue
            s = st.setdefault(b["id"], {"frames": 0, "stop": {}})
            s["frames"] += 1
            if run[i]["decision"] == "STOP" and any(hit(d, b) for d in run[i]["dets"]):
                s["stop"][i] = b["near"]
    return st


def m1(mk, ctrl, cand):
    a, b = per_object(mk, ctrl), per_object(mk, cand)
    objs, fail = {}, []
    for oid in sorted(a):
        sa, sb = a[oid]["stop"], b[oid]["stop"]
        lost = sorted(set(sa) - set(sb))
        fa = sa[min(sa)] if sa else None
        fb = sb[min(sb)] if sb else None
        later = fa is not None and (fb is None or min(sb) > min(sa))
        objs[oid] = {"frames": a[oid]["frames"], "stop": [len(sa), len(sb)], "first_m": [fa, fb], "lost": lost,
                     "gained": sorted(set(sb) - set(sa))}
        if lost or later:
            fail.append(oid)
    new = sorted({r["i"] for r in cand if r["decision"] == "STOP"} - {r["i"] for r in ctrl if r["decision"] == "STOP"})
    unmatched = [i for i in new if not any(hit(d, bx) for d in cand[i]["dets"] for bx in mk.get(i, []))]
    return {"objects": objs, "failing_objects": fail, "new_stop_frames": new, "new_unmatched": unmatched,
            "stop_frames": [sum(r["decision"] == "STOP" for r in ctrl), sum(r["decision"] == "STOP" for r in cand)]}


def main():
    mk = boxes_of(sys.argv[1])
    ctrl, off, cand = (load(p) for p in sys.argv[2:5])
    for x in (off, cand):
        assert len(x) == len(ctrl)
        for p, q in zip(ctrl, x):
            assert (p["i"], p["stamp"], p["bag_t"]) == (q["i"], q["stamp"], q["bag_t"]), p["i"]
    out = {"id_off_vs_control_differing_rows": identity(ctrl, off), "M1": m1(mk, ctrl, cand)}
    selfc = m1(mk, ctrl, ctrl)
    oid = next(o for o, s in out["M1"]["objects"].items() if s["stop"][0])
    k = min(per_object(mk, ctrl)[oid]["stop"])
    planted = copy.deepcopy(cand)
    planted[k]["decision"] = "GO"
    out["controls"] = {"self_failing": selfc["failing_objects"], "planted": [oid, k],
                       "planted_found": oid in m1(mk, ctrl, planted)["failing_objects"]}
    out["verdict"] = {"ID": not out["id_off_vs_control_differing_rows"],
                      "M1_no_loss": not out["M1"]["failing_objects"], "M1_new_matched": not out["M1"]["new_unmatched"]}
    json.dump(out, open(sys.argv[5], "w"), indent=1)
    m = out["M1"]
    for o, s in m["objects"].items():
        print(o, s["frames"], "stop", s["stop"], "first", s["first_m"], "lost", s["lost"], "gained", s["gained"])
    print("new", m["new_stop_frames"], "unmatched", m["new_unmatched"], "stops", m["stop_frames"])
    print(out["controls"], out["verdict"], "ID diff rows:", out["id_off_vs_control_differing_rows"][:10])


main()
