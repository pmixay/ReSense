#!/usr/bin/env python3
"""Reviewer's per-frame comparison of two replay.py --full outputs (own code).

Every record is compared field by field after removing wall-clock timing (``timing_ms``, health ``latency*`` fields,
health messages that mention latency, and a health ``level`` / ``decision_level`` difference whose only cause is such a
message). Reports: frames, frames differing, STOP rows (``x.decision`` if present, else ``obstacle``) on each side,
STOP rows lost / added, STOP episodes (runs of consecutive STOP rows), first differing frame, the differing keys.
--selftest: a file against itself must be equal; flipping one STOP row must be reported as lost.

    python rows_cmp.py A.jsonl B.jsonl [--selftest] [--list N]
"""
import argparse
import copy
import json


def load(p):
    return [json.loads(l) for l in open(p) if l.strip()]


def stop(r):
    x = r.get("x") or {}
    return x.get("decision") == "STOP" if "decision" in x else bool(r.get("obstacle"))


def clean(r):
    r = copy.deepcopy(r)
    r.pop("timing_ms", None)
    h = r.get("health") or {}
    for k in list(h):
        if "latency" in k:
            h.pop(k)
    msgs = h.get("messages") or []
    h["messages"] = [m for m in msgs if "latency" not in str(m)]
    if not h["messages"]:                   # a level raised only by the wall-clock latency budget is timing
        h.pop("level", None)
        h.pop("decision_level", None)
        x = r.get("x") or {}
        if x.get("decision") in ("CAUTION", "FAULT") and not r.get("warning") and not r.get("obstacle"):
            x["decision"] = "GO"
    return r


def diffkeys(a, b, pre=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in set(a) | set(b):
            out += diffkeys(a.get(k), b.get(k), pre + "." + str(k))
        return out
    return [] if a == b else [pre]


def episodes(s):
    return sum(1 for i, v in enumerate(s) if v and (i == 0 or not s[i - 1]))


def compare(A, B):
    assert len(A) == len(B), (len(A), len(B))
    sa, sb = [stop(r) for r in A], [stop(r) for r in B]
    diff = [i for i, (a, b) in enumerate(zip(A, B)) if clean(a) != clean(b)]
    keys = {}
    for i in diff:
        for k in diffkeys(clean(A[i]), clean(B[i])):
            keys[k.split("[")[0]] = keys.get(k.split("[")[0], 0) + 1
    return dict(frames=len(A), differing=len(diff), first_diff=diff[0] if diff else None,
                stop_a=sum(sa), stop_b=sum(sb), stop_lost=[i for i in range(len(A)) if sa[i] and not sb[i]],
                stop_added=[i for i in range(len(A)) if sb[i] and not sa[i]], episodes_a=episodes(sa),
                episodes_b=episodes(sb), keys=dict(sorted(keys.items(), key=lambda t: -t[1])[:12])), diff


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", type=int, default=0)
    a = ap.parse_args()
    A, B = load(a.a), load(a.b)
    if a.selftest:
        s, _ = compare(A, A)
        assert s["differing"] == 0 and not s["stop_lost"], s
        bad = copy.deepcopy(A)
        i = next((i for i, r in enumerate(bad) if stop(r)), None)
        if i is not None:
            if "decision" in (bad[i].get("x") or {}):
                bad[i]["x"]["decision"] = "GO"
            bad[i]["obstacle"] = False
            s, _ = compare(A, bad)
            assert s["stop_lost"] == [i] and s["differing"] == 1, s
            print("selftest PASS")
        else:
            print("selftest: self equal; no STOP row to flip")
    s, diff = compare(A, B)
    print(json.dumps(s))
    for i in diff[:a.list]:
        print(i, diffkeys(clean(A[i]), clean(B[i]))[:6])


if __name__ == "__main__":
    main()
