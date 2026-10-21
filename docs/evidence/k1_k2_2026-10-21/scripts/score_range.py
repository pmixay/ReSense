#!/usr/bin/env python3
"""Rows R-1 / K1 / K2-G of PROTOCOL.md §3 from prebuild_range.py outputs: per job, the control's STOP-hit frames vs a
candidate run's (frame index k), first STOP and held-from, with a planted-loss control.

    score_range.py <control dir> <cand dir> <out.json>
"""
import json
import sys
from pathlib import Path


def rows(p):
    return {r["k"]: r for r in json.loads(Path(p).read_text())["rows"]}


def main():
    a, b, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    res, bad = {}, []
    for f in sorted(a.glob("*.json")):
        g = b / f.name
        if not g.exists():
            res[f.stem] = {"missing": True}
            bad.append(f.stem)
            continue
        ra, rb = rows(f), rows(g)
        assert set(ra) == set(rb), f.name
        ha = {k for k, r in ra.items() if r.get("hit")}
        hb = {k for k, r in rb.items() if r.get("hit")}
        sa = json.loads(f.read_text())["summary"]
        sb = json.loads(g.read_text())["summary"]
        lost, gained = sorted(ha - hb), sorted(hb - ha)
        fa, fb = sa["first_stop_X"], sb["first_stop_X"]
        later = fa is not None and (fb is None or fb < fa - 1e-6)
        res[f.stem] = {"lost": lost, "gained": len(gained), "stop": [len(ha), len(hb)], "first": [fa, fb],
                       "held": [sa["held_from_X"], sb["held_from_X"]],
                       "visible": [sa["visible_frames"], sb["visible_frames"]], "first_later": later}
        if lost or later:
            bad.append(f.stem)
    # planted control: the same comparison with one control hit removed from the candidate side must list it as lost
    name = next(n for n, r in res.items() if r.get("stop", [0])[0])
    ra = rows(a / (name + ".json"))
    k = sorted(k for k, r in ra.items() if r.get("hit"))[0]
    planted = {kk: dict(r, hit=False) if kk == k else r for kk, r in ra.items()}
    found = k in {x for x, r in ra.items() if r.get("hit")} - {x for x, r in planted.items() if r.get("hit")}
    report = {"control": str(a), "cand": str(b), "jobs": res, "failing": bad,
              "planted_control": {"job": name, "frame": k, "found": found}}
    Path(out).write_text(json.dumps(report, indent=1))
    for n, r in res.items():
        print(f"{n:18s} {r}")
    print("FAILING:", bad)


main()
