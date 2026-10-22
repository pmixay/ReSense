#!/usr/bin/env python3
"""Sampled K2 range jobs, per frame (reviewer): for each job, the frames where the placed object is STOP-matched ("hit")
in tag A and tag B, lost (A hit, B not) and gained, first STOP X, held-from X. --plant drops the first frame hit in both
tags from B in the first job that has one (positive control). The rows record X only, not the lateral placement: the same
placement is by construction (tag ctlatfin reads a byte-identical copy of fin's object-free baseline files).
    range_cmp.py <range_dir> <tagA> <tagB> [--plant]"""
import json, os, sys
d, A, B = sys.argv[1:4]; plant = "--plant" in sys.argv; planted = False
for f in sorted(os.listdir(os.path.join(d, A))):
    if not f.endswith(".json"):
        continue
    ja, jb = (json.load(open(os.path.join(d, t, f))) for t in (A, B))
    ra, rb = {r["k"]: r for r in ja["rows"]}, {r["k"]: r for r in jb["rows"]}
    ha, hb = {k for k, r in ra.items() if r["hit"]}, {k for k, r in rb.items() if r["hit"]}
    if plant and not planted and ha & hb:
        hb.discard(min(ha & hb)); planted = True
    sa, sb = ja["summary"], jb["summary"]
    print(f"{f[:-5]:10s} {A}: stop {sa['stop_frames']:3d} first {sa['first_stop_X']} held {sa['held_from_X']} | "
          f"{B}: stop {sb['stop_frames']:3d} first {sb['first_stop_X']} held {sb['held_from_X']} | lost {sorted(ha - hb)} "
          f"gained {len(hb - ha)}")
