#!/usr/bin/env python3
"""Summarise per-frame decisions of an obstacle-free recording (every STOP is a false alarm).

STOP episode = maximal run of consecutive STOP frames. STOP event = episodes merged when separated by
< 1.0 s of recording (so a flickering alarm counts once). Distance travelled = integral of the
detector's own LiDAR ego-speed estimate (only for normalisation; flagged as such) over bag time.

  summarize_empty.py out/<name>.jsonl [...]  -> prints a table, writes out/<name>.empty.json
"""
import json
import sys

import numpy as np


def load(path):
    return [json.loads(line) for line in open(path)]


def runs(flags):
    out, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        if not f and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def summarize(path):
    R = load(path)
    n = len(R)
    t = np.array([r["bag_t"] for r in R])
    dur = float(t[-1] - t[0] + np.median(np.diff(t))) if n > 1 else 0.1
    dec = [r["decision"] for r in R]
    counts = {k: dec.count(k) for k in ("GO", "CAUTION", "STOP", "FAULT")}
    stop = [d == "STOP" for d in dec]
    eps = runs(stop)
    events = []
    for a, b in eps:
        if events and t[a] - t[events[-1][1]] < 1.0:
            events[-1] = (events[-1][0], b)
        else:
            events.append((a, b))
    ego = np.array([r["ego"] if r["ego"] is not None else np.nan for r in R], float)
    dt = np.diff(t, prepend=t[0])
    dt[dt > 1.0] = 0.0
    egof = np.where(np.isfinite(ego), ego, 0.0)
    km = float(np.sum(egof * dt) / 1000.0)
    ep_rows = []
    for a, b in eps:
        ds = [R[i]["nearest"] for i in range(a, b + 1) if R[i]["nearest"] is not None]
        lat = [R[i]["dets"][0]["lat"] for i in range(a, b + 1) if R[i]["dets"]]
        kinds = sorted({d["kind"] or "corridor" for i in range(a, b + 1) for d in R[i]["dets"]})
        ep_rows.append({"first": a, "last": b, "frames": b - a + 1, "t0": round(t[a] - t[0], 1),
                        "d_first": ds[0] if ds else None, "d_min": min(ds) if ds else None,
                        "d_max": max(ds) if ds else None, "lat": round(float(np.median(lat)), 2) if lat else None,
                        "kinds": kinds})
    caution_reasons = {"warning_obj": sum(1 for r in R if r["decision"] == "CAUTION" and r["warning"]),
                       "health_only": sum(1 for r in R if r["decision"] == "CAUTION" and not r["warning"])}
    msgs = {}
    for r in R:
        if r["dlevel"] == "warn" or r["level"] == "error":
            for m in r["msgs"]:
                key = m.split(":")[0].split("(")[0].strip()[:40]
                msgs[key] = msgs.get(key, 0) + 1
    out = {"file": path, "frames": n, "duration_s": round(dur, 1), "km_ego_est": round(km, 2),
           "counts": counts, "frac": {k: round(v / n, 4) for k, v in counts.items()},
           "stop_episodes": len(eps), "stop_events_1s": len(events), "episodes": ep_rows,
           "caution_split": caution_reasons, "health_msgs": dict(sorted(msgs.items(), key=lambda kv: -kv[1])[:12]),
           "clear_median": float(np.median([r["clear"] for r in R])),
           "clear_p10": float(np.percentile([r["clear"] for r in R], 10))}
    return out


if __name__ == "__main__":
    for p in sys.argv[1:]:
        s = summarize(p)
        json.dump(s, open(p.replace(".jsonl", ".empty.json"), "w"), indent=1)
        print(f"{p}: {s['frames']} fr, {s['duration_s']} s, ~{s['km_ego_est']} km(ego est) | {s['counts']} | "
              f"STOP episodes {s['stop_episodes']}, events {s['stop_events_1s']} | clear med {s['clear_median']:.0f} m"
              f" p10 {s['clear_p10']:.0f} | CAUTION split {s['caution_split']}")
        for e in s["episodes"]:
            print("   ", e)
        print("    health:", s["health_msgs"])
