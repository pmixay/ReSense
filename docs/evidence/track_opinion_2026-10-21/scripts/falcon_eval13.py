#!/usr/bin/env python3
"""Falcon rows of PROTOCOL §3 (H3 person, G3 false STOP episodes) for falcon_multi.py records, and the
person label of the track-opinion rows.

    falcon_eval13.py eval <base.jsonl> <cand.jsonl> ... --case explicit_ros|baseline
    falcon_eval13.py label <off.rows.npz> <off.jsonl> --case ... --out <rows in collect layout>

Person association: the N2 reviewed raw-geometry anchors (``n2_falcon_2026-10-18/summarize_falcon.py``,
main_approach + early_uncertain, margins 1.0 / 0.6 / 1.2 m) and the far walker's raw labels
(``falcon_long_range_2026-10-19``, amendment A1), as ``falcon_long_range_2026-10-19/scripts/falcon_eval.py``.
``--case baseline`` = the manual (Pandar-axes default config) path, ``explicit_ros`` = the falcon_ros profile.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(os.environ.get("RESENSE_REPO", Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(REPO / "docs/evidence/n2_falcon_2026-10-18"))
sys.path.insert(0, str(REPO / "docs/evidence/falcon_long_range_2026-10-19/scripts"))
import summarize_falcon as N2  # noqa: E402
from assoc import target_at  # noqa: E402

FAR = json.loads((REPO / "docs/evidence/falcon_long_range_2026-10-19/far_walker_labels.json").read_text())


def load(p):
    rows = N2.load_rows(Path(p))
    for r in rows:
        r.setdefault("track_detail", {"axis_valid": 0.0})
        if r["track_detail"].get("axis_valid") is None:
            r["track_detail"]["axis_valid"] = 0.0
    return rows


def person_frames(rows, case, by_frame):
    s = N2.summarize(rows, case, by_frame)
    at = s["associated_targets"]
    return set(at["main_approach"]["stop"]) | set(at["early_uncertain"]["stop"]), at


def evaluate(rows, case, by_frame):
    person, at = person_frames(rows, case, by_frame)
    eps, cur = [], None
    for r in rows:
        if r["decision"] == "STOP":
            cur = (cur or []) + [r["i"]]
        elif cur is not None:
            eps.append(cur)
            cur = None
    if cur:
        eps.append(cur)
    false = [e for e in eps if not any(i in person for i in e)]
    m = at["main_approach"]
    return {"stop_frames": sum(r["decision"] == "STOP" for r in rows), "stop_episodes": len(eps),
            "false_stop_episodes": len(false), "false_episode_frames": [[e[0], e[-1]] for e in false],
            "person_stop_frames": len(person), "person_frames": sorted(person),
            "main_first_stop_frame": m["first_stop_frame"], "main_first_stop_raw_forward_m": m["first_stop_raw_forward_m"],
            "early_first_stop_frame": at["early_uncertain"]["first_stop_frame"],
            "caution_frames": sum(r["decision"] == "CAUTION" for r in rows)}


def cmd_eval(a):
    _, by_frame = N2.references()
    base = evaluate(load(a.base), a.case, by_frame)
    out = {"case": a.case, "base": {k: v for k, v in base.items() if k != "person_frames"}, "cand": {}}
    for p in a.cand:
        c = evaluate(load(p), a.case, by_frame)
        lost = sorted(set(base["person_frames"]) - set(c["person_frames"]))
        bm, cm = base["main_first_stop_raw_forward_m"], c["main_first_stop_raw_forward_m"]
        out["cand"][Path(p).stem] = {**{k: v for k, v in c.items() if k != "person_frames"},
                                     "lost_person_stop_frames": lost,
                                     "new_person_stop_frames": sorted(set(c["person_frames"]) - set(base["person_frames"])),
                                     "H3_pass": not lost and cm is not None and (bm is None or cm >= bm - 1e-6),
                                     "G3_pass": c["false_stop_episodes"] <= base["false_stop_episodes"]}
    txt = json.dumps(out, indent=1)
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)


def cmd_label(a):
    _, by_frame = N2.references()
    recs = {r["i"]: r for r in load(a.records)}
    z = np.load(a.rows)
    X, M = z["X"], z["M"]
    lab = np.zeros(len(M))
    for k, m in enumerate(M):
        i = int(m[0])
        rot = np.asarray(recs[i]["mount_rotation"])
        if a.case == "baseline":
            rot = rot @ N2.PANDAR
        raw = np.asarray(m[6:9]) @ rot
        for name, box in by_frame.get(i, {}).items():
            if N2.in_box(raw, box, np.array([1.0, 0.6, 1.2])):
                lab[k] = 1
        for ep in FAR["episodes"].values():
            t = target_at(ep["path"], i)
            if t is not None and abs(raw[0] - t[0]) <= 2.5 and abs(raw[1] - t[1]) <= 1.0:
                lab[k] = 1
    Mc = np.c_[M[:, 0], M[:, 1], M[:, 2], M[:, 3], M[:, 4], M[:, 5], lab]
    np.savez_compressed(a.out, X=X, piece=np.array(["falcon"] * len(M)), M=Mc, features=z["features"])
    print(f"{len(M)} rows, {int(lab.sum())} person, {int(M[:, 2].sum())} rule STOP rows "
          f"({int((M[:, 2] * lab).sum())} on the person) -> {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval")
    e.add_argument("base")
    e.add_argument("cand", nargs="+")
    e.add_argument("--case", required=True)
    e.add_argument("--out", default="")
    lb = sub.add_parser("label")
    lb.add_argument("rows")
    lb.add_argument("records")
    lb.add_argument("--case", required=True)
    lb.add_argument("--out", required=True)
    a = ap.parse_args()
    (cmd_eval if a.cmd == "eval" else cmd_label)(a)


if __name__ == "__main__":
    main()
