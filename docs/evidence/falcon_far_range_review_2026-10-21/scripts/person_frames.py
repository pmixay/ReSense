#!/usr/bin/env python3
"""Per-frame state of the main person (reviewed N2 anchors) in two or more replays: STOP detection on the person,
warning on the person, decision, clear and monitored range. Counts GO frames while the person is inside the
reported clear distance and monitored range ("GO past the person"), and the frames where a warning or STOP on the
person in run A became GO in run B.

    person_frames.py A.jsonl B.jsonl [--names a,b] [--json out.json]
"""
import argparse
import json
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, "/home/user/ReSense/docs/evidence/n2_falcon_2026-10-18")
import summarize_falcon as N2  # noqa: E402

_, BY = N2.references()


def state(rows):
    out = {}
    for r in rows:
        b = BY.get(r["i"], {}).get("main_approach")
        if b is None:
            continue
        c = np.asarray(b).mean(axis=0)
        R = np.asarray(r["mount_rotation"])

        def on(dl):
            for d in dl:
                p = np.asarray(d["c"]) @ R
                if abs(p[0] - c[0]) < 2.5 and abs(p[1] - c[1]) < 1.0:
                    return True
            return False
        out[r["i"]] = {"x": float(c[0]), "stop": on(r["dets"]), "warn": on(r["warns"]), "dec": r["decision"],
                       "clear": r["clear"], "mon": r["monitored"]}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--names", default="")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    names = a.names.split(",") if a.names else a.runs
    S = {n: state([json.loads(line) for line in open(p)]) for n, p in zip(names, a.runs)}
    res = {}
    for n, s in S.items():
        go_past = [i for i, v in s.items() if v["dec"] == "GO" and v["mon"] is not None and v["x"] <= min(v["clear"], v["mon"])]
        go_mon = [i for i, v in s.items() if v["dec"] == "GO" and v["mon"] is not None and v["x"] <= v["mon"]]
        first = next((i for i in sorted(s) if s[i]["stop"]), None)
        res[n] = {"frames_with_person": len(s), "person_stop": sum(v["stop"] for v in s.values()),
                  "person_warn_only": sum(v["warn"] and not v["stop"] for v in s.values()),
                  "decisions": dict(Counter(v["dec"] for v in s.values())),
                  "go_with_person_inside_clear_and_monitored": len(go_past),
                  "go_with_person_inside_monitored": len(go_mon),
                  "go_past_examples": [[i, round(s[i]["x"], 1), s[i]["clear"], s[i]["mon"]] for i in go_past[:12]],
                  "go_past_x_range": [round(min(s[i]["x"] for i in go_past), 1), round(max(s[i]["x"] for i in go_past), 1)] if go_past else None,
                  "first_person_stop": None if first is None else [first, round(s[first]["x"], 1)]}
    if len(names) >= 2:
        A, B = S[names[0]], S[names[1]]
        common = sorted(set(A) & set(B))
        res["transitions"] = {
            "A_person_warn_or_stop__B_GO": [[i, round(A[i]["x"], 1)] for i in common if (A[i]["warn"] or A[i]["stop"]) and B[i]["dec"] == "GO"],
            "A_person_stop__B_no_person_stop": [[i, round(A[i]["x"], 1)] for i in common if A[i]["stop"] and not B[i]["stop"]],
            "A_person_warn_or_stop__B_neither": [[i, round(A[i]["x"], 1)] for i in common if (A[i]["warn"] or A[i]["stop"]) and not (B[i]["warn"] or B[i]["stop"])],
            "B_person_warn_or_stop__A_neither": len([i for i in common if (B[i]["warn"] or B[i]["stop"]) and not (A[i]["warn"] or A[i]["stop"])]),
        }
    print(json.dumps(res, indent=1))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
