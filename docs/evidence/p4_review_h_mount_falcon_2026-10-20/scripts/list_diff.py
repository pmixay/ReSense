"""Every differing row of two per-frame record sets, listed (``cmp_frames.py`` only counts and shows ten).

    list_diff.py gate  <work A> <work B>       # gate work dirs (eval_real rows; *.jsonl per piece)
    list_diff.py node  <a.jsonl[.xz]> <b.jsonl[.xz]>   # judge_runner records (Falcon, X3 raw)

A row differs in its *decision* when (decision | obstacle, warning), the detections or the warnings differ; any
other difference outside wall-clock timing (and, for gate rows, the latency-driven health level / message as
``cmp_frames.py`` normalises it) is counted as *other*. Prints one line per differing row and a summary.
"""
import glob
import json
import lzma
import os
import sys

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    with (lzma.open(p, "rt") if p.endswith(".xz") else open(p)) as f:
        return [json.loads(line) for line in f]


def gate_norm(d):
    d = dict(d)
    d.pop("timing_ms", None)
    h = dict(d.get("health") or {})
    h.pop("latency_p95_ms", None)
    h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]
    h.pop("level", None)
    h.pop("decision_level", None)
    d["health"] = h
    return d


def gate_word(d):
    h = d.get("health") or {}
    if d["obstacle"]:
        return "STOP"
    if h.get("level") == "error":
        return "FAULT"
    return "CAUTION" if d["warning"] or h.get("decision_level", h.get("level")) == "warn" else "GO"


def brief(ds):
    return [(round(x.get("distance", x.get("d", 0)), 1), round(x.get("lateral", x.get("lat", 0)), 2),
             x.get("kind"), x.get("reason")) for x in ds]


def main():
    mode, A, B = sys.argv[1:4]
    if mode == "gate":
        pairs = [(os.path.basename(f), f, os.path.join(B, os.path.basename(f)))
                 for f in sorted(glob.glob(os.path.join(A, "*.jsonl")))]
    else:
        pairs = [(os.path.basename(A), A, B)]
    rows = dec = other = 0
    for name, fa, fb in pairs:
        a, b = load(fa), load(fb)
        if len(a) != len(b):
            print(f"ROW COUNT {name} {len(a)} {len(b)}")
            dec += 1
            continue
        for i, (x, y) in enumerate(zip(a, b)):
            rows += 1
            if mode == "gate":
                kx = (x["obstacle"], x["warning"], x["detections"], x["warnings"])
                ky = (y["obstacle"], y["warning"], y["detections"], y["warnings"])
                same_other = gate_norm(x) == gate_norm(y)
                wx, wy, fid = gate_word(x), gate_word(y), x.get("frame_id")
                dx, dy, wxs, wys = x["detections"], y["detections"], x["warnings"], y["warnings"]
            else:
                kx, ky = (x["decision"], x["dets"], x["warns"]), (y["decision"], y["dets"], y["warns"])
                same_other = ({k: v for k, v in x.items() if k not in TIMING}
                              == {k: v for k, v in y.items() if k not in TIMING})
                wx, wy, fid = x["decision"], y["decision"], x["i"]
                dx, dy, wxs, wys = x["dets"], y["dets"], x["warns"], y["warns"]
            if kx != ky:
                dec += 1
                print(f"DECISION {name} row {i} {fid}: {wx} -> {wy}; dets {brief(dx)} -> {brief(dy)}; "
                      f"warns {brief(wxs)} -> {brief(wys)}")
            elif not same_other:
                other += 1
                print(f"OTHER {name} row {i} {fid}: decision {wx}, same detections and warnings")
    print(f"SUMMARY rows {rows}; differ in decision/detections/warnings {dec}; differ only in other non-timing fields {other}")


if __name__ == "__main__":
    main()
