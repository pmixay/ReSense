#!/usr/bin/env python3
"""Per-frame processing time (timing_ms.total, and the 'cluster' stage that holds rail_reference_check) p50 / p95 per
gate work directory, control vs candidate, grouped as ride / set O / six recordings.
    python timing.py <ctrl work> <cand work>"""
import glob, json, os, sys
import numpy as np

def load(work, key):
    groups = {"ride": [], "set O": [], "six recordings": []}
    for f in glob.glob(os.path.join(work, "*.jsonl")):
        b = os.path.basename(f)
        g = "ride" if b.startswith("new_data") else "set O" if b.startswith("cloud") else "six recordings"
        for line in open(f):
            t = json.loads(line).get("timing_ms") or {}
            if key in t:
                groups[g].append(t[key])
    return groups

for key in ("total", "cluster"):
    A, B = load(sys.argv[1], key), load(sys.argv[2], key)
    for g in A:
        a, b = np.array(A[g]), np.array(B[g])
        print(f"{key:8s} {g:15s} frames {a.size:6d}/{b.size:6d}  p50 {np.percentile(a,50):6.1f} -> {np.percentile(b,50):6.1f} ms"
              f"  p95 {np.percentile(a,95):6.1f} -> {np.percentile(b,95):6.1f} ms")
