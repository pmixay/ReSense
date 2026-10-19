#!/usr/bin/env python3
"""Falcon full-recording comparison against the committed 1.1.0 run (falcon_full_v110.jsonl).

Per frame: decision, obstacle, nearest; STOP frames and STOP intervals (maximal runs). Reports
lost / added STOP frames per lane and every non-timing field difference count.
    falcon_compare.py --archive <falcon_full_runs.tar.xz> --run <work>/full --out falcon_full.json
"""
import argparse
import gzip
import json
import tarfile
from pathlib import Path

NON_TIMING = ("decision", "obstacle", "warning", "nearest", "clear", "level", "dlevel", "msgs", "monitored",
              "rail_lock", "dets", "warns", "n_points", "track_center", "curv", "mount", "mount_h", "ego")


def intervals(frames):
    out, start, prev = [], None, None
    for f in frames:
        if start is None:
            start = prev = f
        elif f == prev + 1:
            prev = f
        else:
            out.append((start, prev)); start = prev = f
    if start is not None:
        out.append((start, prev))
    return out


def strip_latency(r):
    msgs = [m for m in r.get("msgs", []) if not m.startswith("latency p95")]
    lat = len(msgs) != len(r.get("msgs", []))
    return msgs, lat


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    with tarfile.open(a.archive) as t:
        ref = [json.loads(l) for l in t.extractfile("falcon_full_v110.jsonl").read().decode().splitlines()]
    ref_stop = [r["i"] for r in ref if r["decision"] == "STOP"]
    result = {"reference": {"frames": len(ref), "stop_frames": len(ref_stop), "stop_intervals": len(intervals(ref_stop))}, "lanes": {}}
    for lane in ("clean_off", "clean_on"):
        with gzip.open(a.run / f"{lane}.jsonl.gz", "rt") as f:
            run = [json.loads(l) for l in f]
        assert [r["i"] for r in run] == [r["i"] for r in ref]
        stop = [r["i"] for r in run if r["decision"] == "STOP"]
        diff_fields, decision_diff, latency_only = {}, [], 0
        for x, y in zip(ref, run):
            if x["decision"] != y["decision"]:
                decision_diff.append(x["i"])
            for k in NON_TIMING:
                vx, vy = x.get(k), y.get(k)
                if k == "msgs":
                    (vx, lx), (vy, ly) = strip_latency(x), strip_latency(y)
                    latency_only += lx != ly
                if k in ("level",) and (strip_latency(x)[1] or strip_latency(y)[1]):
                    continue
                if vx != vy:
                    diff_fields[k] = diff_fields.get(k, 0) + 1
        result["lanes"][lane] = {
            "frames": len(run), "stop_frames": len(stop), "stop_intervals": len(intervals(stop)),
            "lost_stop_frames": sorted(set(ref_stop) - set(stop)), "added_stop_frames": sorted(set(stop) - set(ref_stop)),
            "decision_differences": decision_diff[:50], "n_decision_differences": len(decision_diff),
            "field_difference_counts": diff_fields, "rows_latency_message_differs": latency_only,
            "guard_frames": sum(1 for r in run if "dust_guard" in r)}
    lanes = {}
    for lane in ("clean_off", "clean_on"):
        with gzip.open(a.run / f"{lane}.jsonl.gz", "rt") as f:
            lanes[lane] = [json.loads(l) for l in f]
    onoff = {}
    for x, y in zip(lanes["clean_off"], lanes["clean_on"]):
        lat = strip_latency(x)[1] or strip_latency(y)[1]
        for k in NON_TIMING:
            vx, vy = (strip_latency(x)[0], strip_latency(y)[0]) if k == "msgs" else (x.get(k), y.get(k))
            if k == "level" and lat:
                continue
            if vx != vy:
                onoff[k] = onoff.get(k, 0) + 1
    result["switch_on_vs_off_non_timing_differences"] = onoff
    a.out.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("decision_differences",)} for k, v in result["lanes"].items()}, indent=1))
    print(result["reference"], "on-vs-off:", onoff)


if __name__ == "__main__":
    main()
