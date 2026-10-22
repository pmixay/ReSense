#!/usr/bin/env python3
"""Reviewer's Falcon scorer (written for the 1.3.0 review; independent of the lanes' scorers, it reuses only
the reviewed person anchors of n2_falcon_2026-10-18 as truth).

Per run (judge_runner records from falcon_multi.py / falcon_starts.py):
  person-STOP frame: decision STOP and a STOP detection whose vehicle-frame centre lies within 2.5 m along X and 1.0 m along Y of the main-approach (or early-uncertain)
  person anchor's centre;
  first person STOP (frame, anchor X); held STOP = first frame from which >= 90 % of the next 30 frames are
  person-STOP; STOP episodes (maximal runs of STOP frames) and false ones (no frame of the run is a person-STOP);
  GO-in-clear: decision GO while the person anchor's X <= min(clear, monitored).
Pairs (A = control, B = candidate): person-STOP frames of A that are not STOP in B (lost), person-STOP onsets of A
whose B onset is later (delayed), new STOP frames of B.
    falcon_score.py --pair A.jsonl B.jsonl [--repo R] [--json out]
"""
import argparse, json, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--pair", nargs=2, required=True)
ap.add_argument("--repo", default="/home/user/wt/int")
ap.add_argument("--json", default="")
a = ap.parse_args()
sys.path.insert(0, a.repo + "/docs/evidence/n2_falcon_2026-10-18")
import summarize_falcon as N2  # noqa: E402
_, BY = N2.references()


def anchor(i):
    b = BY.get(i, {})
    box = b.get("main_approach", b.get("early_uncertain"))
    return None if box is None else np.asarray(box).mean(axis=0)


def load(p):
    rows = [json.loads(l) for l in open(p)]
    return {r["i"]: r for r in rows}


def per_frame(rows):
    out = {}
    for i, r in rows.items():
        c = anchor(i)
        ps = False
        if c is not None and r["decision"] == "STOP":
            for d in r["dets"]:
                p = np.asarray(d["c"])      # vehicle frame; X / Y agree with the anchor frame on both paths (checked)
                if abs(p[0] - c[0]) < 2.5 and abs(p[1] - c[1]) < 1.0:
                    ps = True
        go_in = (c is not None and r["decision"] == "GO" and r.get("monitored") is not None
                 and c[0] <= min(r["clear"], r["monitored"]))
        out[i] = {"stop": r["decision"] == "STOP", "pstop": ps, "x": None if c is None else float(c[0]),
                  "go_in": go_in, "dec": r["decision"]}
    return out


def runs(S):
    S = sorted(S); res = []
    for i in S:
        if res and i == res[-1][1] + 1:
            res[-1][1] = i
        else:
            res.append([i, i])
    return res


def summary(F):
    idx = sorted(F)
    ps = [i for i in idx if F[i]["pstop"]]
    first = ps[0] if ps else None
    held = None
    for i in ps:
        win = [j for j in range(i, i + 30) if j in F]
        if win and sum(F[j]["pstop"] for j in win) >= 0.9 * len(win):
            held = i; break
    eps = runs([i for i in idx if F[i]["stop"]])
    false = [e for e in eps if not any(F[j]["pstop"] for j in range(e[0], e[1] + 1))]
    return {"frames": len(idx), "range": [idx[0], idx[-1]], "stop_frames": sum(F[i]["stop"] for i in idx),
            "person_stop_frames": len(ps),
            "first_person_stop": None if first is None else [first, round(F[first]["x"], 1)],
            "held_person_stop": None if held is None else [held, round(F[held]["x"], 1)],
            "stop_episodes": len(eps), "false_episodes": len(false), "false_episode_spans": false,
            "go_in_clear": [i for i in idx if F[i]["go_in"]],
            "decisions": {k: sum(F[i]["dec"] == k for i in idx) for k in ("GO", "CAUTION", "STOP")}}


A, B = (per_frame(load(p)) for p in a.pair)
common = sorted(set(A) & set(B))
A = {i: A[i] for i in common}; B = {i: B[i] for i in common}
sa, sb = summary(A), summary(B)
lost = [i for i in common if A[i]["pstop"] and not B[i]["stop"]]
onsets = [e[0] for e in runs([i for i in common if A[i]["pstop"]])]
delayed = [i for i in onsets if not B[i]["stop"]]
new = [i for i in common if B[i]["stop"] and not A[i]["stop"]]
new_nonperson = [i for i in new if not B[i]["pstop"]]
go_in_new = sorted(set(sb["go_in_clear"]) - set(sa["go_in_clear"]))
res = {"A": a.pair[0], "B": a.pair[1], "A_sum": sa, "B_sum": sb, "lost_person_stop_frames": lost,
       "delayed_person_onsets": delayed, "new_stop_frames": len(new), "new_stop_frames_not_on_person": new_nonperson,
       "go_in_clear_new_in_B": go_in_new}
for k in ("A_sum", "B_sum"):
    res[k]["go_in_clear_n"] = len(res[k]["go_in_clear"]); res[k]["go_in_clear"] = res[k]["go_in_clear"][:40]
print(json.dumps(res, indent=1))
if a.json:
    open(a.json, "w").write(json.dumps(res, indent=1))
