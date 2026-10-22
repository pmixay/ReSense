#!/usr/bin/env python3
"""Per-frame comparison of two range tags (prebuild_range.py outputs): for every job, STOP-matching frames of A and B,
frames lost (A hit, B not) and gained, first STOP X, held-from X, visible frames.
    cmp_range.py <range_dir> <tagA> <tagB> [jobs-regex]"""
import json, os, re, sys
d, A, B = sys.argv[1:4]
rx = re.compile(sys.argv[4]) if len(sys.argv) > 4 else None
out = {}
print(f"{'job':18s} {'A vis/stop/first/held':>26s} {'B vis/stop/first/held':>26s} lost gained")
for f in sorted(os.listdir(os.path.join(d, A))):
    if not f.endswith(".json") or (rx and not rx.search(f)):
        continue
    pa, pb = os.path.join(d, A, f), os.path.join(d, B, f)
    if not os.path.exists(pb):
        continue
    ja, jb = json.load(open(pa)), json.load(open(pb))
    ra = {r["k"]: r for r in ja["rows"]} if "rows" in ja else None
    rb = {r["k"]: r for r in jb["rows"]} if "rows" in jb else None
    ha = {k for k, r in ra.items() if r.get("hit")}
    hb = {k for k, r in rb.items() if r.get("hit")}
    sa, sb = ja["summary"], jb["summary"]
    lost, gained = sorted(ha - hb), sorted(hb - ha)
    out[f[:-5]] = dict(A=dict(vis=sa["visible_frames"], stop=sa["stop_frames"], first=sa["first_stop_X"], held=sa["held_from_X"]),
                       B=dict(vis=sb["visible_frames"], stop=sb["stop_frames"], first=sb["first_stop_X"], held=sb["held_from_X"]),
                       lost=lost, gained=gained)
    fm = lambda s: f"{s['visible_frames']}/{s['stop_frames']}/{s['first_stop_X']}/{s['held_from_X']}"
    print(f"{f[:-5]:18s} {fm(sa):>26s} {fm(sb):>26s} {len(lost):4d} {len(gained):4d} {lost[:8] if lost else ''}")
json.dump(out, open(os.path.join(d, f"cmp_{A}_{B}.json"), "w"), indent=1)
