#!/usr/bin/env python3
"""Summarize a judge_runner jsonl: decision counts, STOP / CAUTION episodes, health and calibration.

    summarize_run.py RUN.jsonl [--out RUN.summary.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys


def episodes(recs, decision):
    out, cur = [], None
    for r in recs:
        if r["decision"] == decision:
            if cur is None:
                cur = {"first": r["i"], "last": r["i"], "d": []}
            cur["last"] = r["i"]
            ds = [d["d"] for d in (r["dets"] if decision == "STOP" else r["warns"])]
            cur["d"].append(min(ds) if ds else r["nearest"])
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    for e in out:
        ds = [d for d in e["d"] if d is not None]
        e["n"] = e["last"] - e["first"] + 1
        e["d_first"] = ds[0] if ds else None
        e["d_min"] = min(ds) if ds else None
        e["d_max"] = max(ds) if ds else None
        del e["d"]
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("jsonl")
    p.add_argument("--out", default="")
    a = p.parse_args()
    recs = [json.loads(line) for line in open(a.jsonl)]
    n = len(recs)
    dec = collections.Counter(r["decision"] for r in recs)
    first_ok = next((r["i"] for r in recs if r["decision"] != "FAULT"), None)
    stop_eps = episodes(recs, "STOP")
    s = {
        "frames": n, "decisions": dict(dec),
        "caution_share": round(dec.get("CAUTION", 0) / n, 3) if n else None,
        "first_non_fault_frame": first_ok,
        "stop_episodes": stop_eps,
        "caution_episodes_n": len(episodes(recs, "CAUTION")),
        "level": dict(collections.Counter(str(r["level"]) for r in recs)),
        "dlevel": dict(collections.Counter(str(r["dlevel"]) for r in recs)),
        "mount": dict(collections.Counter(str(r["mount"]) for r in recs)),
        "mount_h_last": recs[-1]["mount_h"] if recs else None,
        "rail_lock": dict(collections.Counter(str(r["rail_lock"]) for r in recs)),
        "monitored_median": sorted(r["monitored"] or 0 for r in recs)[n // 2] if n else None,
        "msgs_top": collections.Counter(m for r in recs for m in r["msgs"]).most_common(8),
        "n_points_median": sorted(r["n_points"] for r in recs)[n // 2] if n else None,
        "total_ms_p50": sorted(r["decode_ms"] + r["detect_ms"] for r in recs)[n // 2] if n else None,
        "total_ms_p95": sorted(r["decode_ms"] + r["detect_ms"] for r in recs)[int(n * 0.95)] if n else None,
        "frame_ids": dict(collections.Counter(r["frame_id"] for r in recs)),
    }
    js = json.dumps(s, indent=1)
    if a.out:
        open(a.out, "w").write(js)
    print(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
