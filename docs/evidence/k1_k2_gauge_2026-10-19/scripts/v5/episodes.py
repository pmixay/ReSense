#!/usr/bin/env python3
"""STOP episodes of a recording in several gate work dirs, base first; marks episodes without a base STOP frame
within +-3 frames ("NEW") and base episodes gone in the run ("GONE"). For v5 runs: joint_used at onset and the
share of joint_used frames in the episode; for every run the STOP detection (distance, lateral, kind).
episodes.py <recording|new_data> <work base> <work run> [<work run> ...]"""
import glob, json, os, sys
name = sys.argv[1]
def load(wd):
    if name == "new_data":
        rows = []
        for k in range(len(glob.glob(os.path.join(wd, "new_data_*.jsonl")))):
            rows += [json.loads(l) for l in open(os.path.join(wd, f"new_data_{k}.jsonl"))]
        return rows
    return [json.loads(l) for l in open(os.path.join(wd, name + ".jsonl"))]
def eps(rows):
    out, s = [], None
    for i, r in enumerate(rows):
        if r["obstacle"] and s is None: s = i
        if not r["obstacle"] and s is not None: out.append((s, i - 1)); s = None
    if s is not None: out.append((s, len(rows) - 1))
    return out
runs = [(wd, load(wd)) for wd in sys.argv[2:]]
base_rows = runs[0][1]
bstop = [bool(r["obstacle"]) for r in base_rows]
for wd, rows in runs:
    E = eps(rows)
    print(f"== {wd}: frames {len(rows)} STOP frames {sum(r['obstacle'] for r in rows)} episodes {len(E)}")
    for s, e in E:
        new = not any(bstop[j] for j in range(max(0, s - 3), min(len(bstop), e + 4)))
        r = rows[s]
        det = [d for d in r.get("detections", [])]
        d0 = det[0] if det else {}
        ju = [rows[j]["track"].get("joint_used") for j in range(s, e + 1)]
        jtxt = "" if ju[0] is None else f" joint_used@onset {ju[0]} ({sum(bool(x) for x in ju)}/{len(ju)}), prev {rows[s-1]['track'].get('joint_used') if s else None}"
        print(f"  {s:6d}-{e:6d} ({r['frame_id']}) {'NEW ' if new else '    '} dist {r.get('nearest_distance')} lat {d0.get('lateral')} kind {d0.get('kind')} reason {d0.get('reason')} size {d0.get('size')} axis_valid {r['track']['axis_valid']} k {r['track']['curvature']:.2e} step {r['track'].get('curv_step', 0):.2e}{jtxt}")
    if wd != runs[0][0]:
        rs = [bool(r["obstacle"]) for r in rows]
        for s, e in eps(base_rows):
            if not any(rs[j] for j in range(max(0, s - 3), min(len(rs), e + 4))):
                print(f"  GONE base episode {s}-{e} dist {base_rows[s].get('nearest_distance')}")
