#!/usr/bin/env python3
"""Falcon rows ID and F-1 of PROTOCOL.md §3 from falcon_trace.py records (control, off, cand; 4,443 rows each).

* alignment: same length, same frame index, header stamp and bag time in every row (fails closed);
* ID: off vs control, every field except timing / latency-driven health (decode_ms, detect_ms, total_ms, and level /
  dlevel / msgs only where either side carries a latency message);
* F-1: person STOP frames R = control STOP frames with i > 2900 minus the attributed false set of score_falcon_pos.py;
  (a) lost = R - cand STOP, (b) first person STOP frame, (c) every new cand STOP frame needs a cand STOP detection
  within 1.5 m in distance and 1.0 m in vehicle Y (c[1]) of a control detection or warning of the same frame.
Controls: control vs itself gives 0 lost / 0 new; a planted loss (one R frame turned GO in a copy of cand) is found.

    score_falcon_f1.py <control.jsonl> <off.jsonl> <cand.jsonl> <out.json>
"""
import copy
import json
import sys

FALSE = {159, 2312, 2313, 2314} | set(range(4394, 4402))
TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    return [json.loads(line) for line in open(p)]


def aligned(a, b):
    assert len(a) == len(b) == 4443, (len(a), len(b))
    for x, y in zip(a, b):
        assert (x["i"], x["stamp"], x["bag_t"], x["frame_id"]) == (y["i"], y["stamp"], y["bag_t"], y["frame_id"]), x["i"]


def lat_msg(r):
    return any("latency" in m for m in r.get("msgs", []))


def strip(r):
    s = {k: v for k, v in r.items() if k not in TIMING}
    if lat_msg(r):
        for k in ("level", "dlevel", "msgs"):
            s.pop(k, None)
    return s


def identity(a, b):
    diff = []
    for x, y in zip(a, b):
        sx, sy = strip(x), strip(y)
        if lat_msg(x) or lat_msg(y):
            for k in ("level", "dlevel", "msgs"):
                sx.pop(k, None)
                sy.pop(k, None)
        if sx != sy:
            diff.append(x["i"])
    return diff


def f1(ctrl, cand):
    stop_c = {r["i"] for r in ctrl if r["decision"] == "STOP"}
    R = {i for i in stop_c if i > 2900} - FALSE
    stop_n = {r["i"] for r in cand if r["decision"] == "STOP"}
    lost = sorted(R - stop_n)
    new = sorted(stop_n - stop_c)
    unexplained = []
    for i in new:
        seen = ctrl[i]["dets"] + ctrl[i]["warns"]
        ok = any(abs(d["d"] - s["d"]) <= 1.5 and abs(d["c"][1] - s["c"][1]) <= 1.0
                 for d in cand[i]["dets"] for s in seen)
        if not ok:
            unexplained.append(i)
    first = lambda rows, s: next(((r["i"], r["nearest"]) for r in rows if r["i"] in s), None)  # noqa: E731
    # the cand's first person STOP: its first STOP frame after 2900 outside the false set
    first_cand = first(cand, {i for i in stop_n if i > 2900} - FALSE)
    return {"person_ref": len(R), "lost": lost, "n_lost": len(lost), "new_stop": new, "n_new": len(new),
            "new_unexplained": unexplained, "first_control": first(ctrl, R), "first_cand": first_cand,
            "stop_control": len(stop_c), "stop_cand": len(stop_n),
            "false_set_stop_control": sorted(FALSE & stop_c), "false_set_stop_cand": sorted(FALSE & stop_n),
            "caution_control": sum(r["decision"] == "CAUTION" for r in ctrl),
            "caution_cand": sum(r["decision"] == "CAUTION" for r in cand)}


def main():
    ctrl, off, cand = (load(p) for p in sys.argv[1:4])
    aligned(ctrl, off)
    aligned(ctrl, cand)
    out = {"id_off_vs_control_differing_rows": identity(ctrl, off)}
    self_ = f1(ctrl, ctrl)
    planted = copy.deepcopy(cand)
    R = sorted({r["i"] for r in ctrl if r["decision"] == "STOP" and r["i"] > 2900} - FALSE)
    k = R[len(R) // 2]
    planted[k]["decision"] = "GO"
    pl = f1(ctrl, planted)
    out["controls"] = {"self_lost": self_["n_lost"], "self_new": self_["n_new"], "planted_frame": k,
                       "planted_found": k in pl["lost"],
                       "identity_self": len(identity(ctrl, ctrl)),
                       "identity_planted_found": k in identity(cand, planted)}
    out["F1"] = f1(ctrl, cand)
    r = out["F1"]
    out["verdict"] = {"ID": not out["id_off_vs_control_differing_rows"], "F1a_no_loss": r["n_lost"] == 0,
                      "F1b_first_not_later": r["first_cand"] is not None and r["first_cand"][0] <= r["first_control"][0],
                      "F1c_new_explained": not r["new_unexplained"]}
    json.dump(out, open(sys.argv[4], "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items()}, indent=1)[:3000])


main()
