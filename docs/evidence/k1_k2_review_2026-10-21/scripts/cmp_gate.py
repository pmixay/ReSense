#!/usr/bin/env python3
"""Per-frame comparison of two regression-gate work directories (control vs candidate): for every recording file,
alignment (same length and stamps, fails closed), STOP frames (``obstacle``) lost and new, CAUTION-only changes,
contiguous STOP runs added; for every new STOP frame the candidate's STOP detections (distance, lateral, centre).
    cmp_gate.py <work_control> <work_cand> <out.json>"""
import glob, json, os, sys

A, B, OUT = sys.argv[1:4]
res = {}
for fa in sorted(glob.glob(os.path.join(A, "*.jsonl"))):
    name = os.path.basename(fa)[:-6]
    fb = os.path.join(B, name + ".jsonl")
    ra = [json.loads(l) for l in open(fa)]
    rb = [json.loads(l) for l in open(fb)]
    assert len(ra) == len(rb), (name, len(ra), len(rb))
    for i, (x, y) in enumerate(zip(ra, rb)):
        assert x["stamp"] == y["stamp"], (name, i)
    sa = {i for i, r in enumerate(ra) if r["obstacle"]}
    sb = {i for i, r in enumerate(rb) if r["obstacle"]}

    def runs(s):
        s = sorted(s); out = []
        for i in s:
            if out and i == out[-1][1] + 1:
                out[-1][1] = i
            else:
                out.append([i, i])
        return out
    new = sorted(sb - sa)
    det = {i: [(round(d["distance"], 1), round(d["lateral"], 2), [round(v, 1) for v in d["center"]], d.get("reason", ""),
                d.get("kind", "")) for d in rb[i]["detections"]] for i in new}
    ctl_warn = {i: [(round(d["distance"], 1), round(d["lateral"], 2), d.get("reason", "")) for d in ra[i]["warnings"]]
                for i in new}
    nd = sum(1 for x, y in zip(ra, rb) if (x["detections"], x["warnings"]) != (y["detections"], y["warnings"]))
    res[name] = dict(frames=len(ra), stop_control=len(sa), stop_cand=len(sb), lost=sorted(sa - sb), new=new,
                     runs_control=len(runs(sa)), runs_cand=len(runs(sb)), new_dets=det, control_warnings_there=ctl_warn,
                     frames_with_det_or_warn_difference=nd,
                     caution_new=sum(1 for x, y in zip(ra, rb) if not x["warning"] and y["warning"]),
                     caution_gone=sum(1 for x, y in zip(ra, rb) if x["warning"] and not y["warning"]))
    r = res[name]
    print(f"{name:40s} frames {r['frames']:5d} STOP {r['stop_control']:4d}->{r['stop_cand']:4d} lost {len(r['lost'])} new {len(new)} "
          f"runs {r['runs_control']}->{r['runs_cand']} diff-frames {nd} caution +{r['caution_new']}/-{r['caution_gone']} {new[:12]}")
json.dump(res, open(OUT, "w"), indent=1)
