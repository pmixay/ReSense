#!/usr/bin/env python3
"""Summarise a Docker chain run (listener jsonl + meta + docker stats)."""
import json
import re
import sys

import numpy as np

for label in sys.argv[1:]:
    base = f"out/docker/{label}"
    rows = [json.loads(line) for line in open(base + ".jsonl")]
    meta = json.load(open(base + ".meta"))
    st = [r for r in rows if r["k"] == "status" and r.get("snapshot") == "frame"]
    st_all = [r for r in rows if r["k"] == "status"]
    decs = [r["v"] for r in rows if r["k"] == "decision"]
    lat = np.array([r["v"] for r in rows if r["k"] == "latency"])
    frame_dec = [r["decision"] for r in st]
    first_stop = next((r for r in st_all if r["decision"] == "STOP"), None)
    first_frame = st[0] if st else None
    stats = []
    for line in open(base + ".stats"):
        m = re.match(r"(\S+) rs_node ([\d.]+)% ([\d.]+)(\w+)", line)
        if m:
            mem = float(m.group(3)) * (1 / 1024 if m.group(4).startswith("Ki") else 1024 if m.group(4).startswith("Gi") else 1)
            stats.append((float(m.group(2)), mem))
    cpu = np.array([s[0] for s in stats]) if stats else np.array([0.0])
    mem = np.array([s[1] for s in stats]) if stats else np.array([0.0])
    fresh = sum(1 for r in st if r["fresh"])
    reasons = {}
    for r in st:
        reasons[r["reason"]] = reasons.get(r["reason"], 0) + 1
    out = {
        "label": label, "play_args": meta["play_args"], "node_ready_s": round(meta["t_ready"] - meta["t_start"], 1),
        "play_wall_s": round(meta["t_end"] - meta["t_play"], 1),
        "frames_processed": len(st), "max_frames_counter": max((r["frames"] or 0) for r in st) if st else 0,
        "dropped": st[-1]["dropped"] if st else None, "skipped": st[-1]["skipped"] if st else None,
        "decision_msgs": {k: decs.count(k) for k in ("GO", "CAUTION", "STOP", "FAULT")},
        "frame_results": {k: frame_dec.count(k) for k in ("GO", "CAUTION", "STOP", "FAULT")},
        "fresh_frames": fresh, "freshness_reasons": reasons,
        "first_stop_after_first_result_s": round(first_stop["t"] - first_frame["t"], 2) if first_stop and first_frame else None,
        "first_stop_dist": first_stop["nearest"] if first_stop else None,
        "stop_dists": [min(r["nearest"] for r in st if r["decision"] == "STOP" and r["nearest"])] if any(r["decision"] == "STOP" and r["nearest"] for r in st) else None,
        "node_latency_ms": {"p50": round(float(np.median(lat)), 1), "p95": round(float(np.percentile(lat, 95)), 1),
                            "max": round(float(lat.max()), 1)} if lat.size else None,
        "decode_ms_p50": round(float(np.median([r["decode_ms"] for r in st if r["decode_ms"] is not None])), 1) if st else None,
        "detect_ms_p50": round(float(np.median([r["detect_ms"] for r in st if r["detect_ms"] is not None])), 1) if st else None,
        "age_s_p50": round(float(np.median([r["age"] for r in st if r["age"] is not None])), 3) if any(r["age"] is not None for r in st) else None,
        "age_s_max": round(float(max(r["age"] for r in st if r["age"] is not None)), 3) if any(r["age"] is not None for r in st) else None,
        "docker_cpu_pct_mean": round(float(cpu.mean()), 1), "docker_cpu_pct_max": round(float(cpu.max()), 1),
        "docker_mem_mb_max": round(float(mem.max()), 1),
        "topic": st[0]["topic"] if st else None,
    }
    json.dump(out, open(base + ".summary.json", "w"), indent=1)
    print(json.dumps(out))
