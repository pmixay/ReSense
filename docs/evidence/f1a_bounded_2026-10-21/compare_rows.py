#!/usr/bin/env python3
"""Paired per-row diff of two per-frame JSONL streams (Falcon run_cache rows, gate work JSONL, ride replay),
control vs candidate, every field outside wall-clock timing (PROTOCOL §4).

Timing fields ignored: keys ending in ``_ms`` / named ``timing_ms`` / ``latency*`` / ``wall_s``. Message lists:
strings mentioning ``latency`` are dropped before comparing (wall-clock health lines); a health ``level`` whose
message list holds nothing but latency lines is compared as "no non-latency message" (it follows the wall clock). A row's STOP status is
``decision == "STOP"`` if present, else ``obstacle``. Reports: rows, rows with any difference, STOP rows per side,
STOP rows lost / added, and the differing field paths (counted). ``--selftest`` injects a changed field and a lost
STOP into a copy of the candidate in memory and requires both to be found, and the control against itself clean.

    python compare_rows.py <control.jsonl> <candidate.jsonl> [--selftest] [--json out.json] [--show N]
"""
import argparse
import copy
import json
import re
import sys
from collections import Counter

SKIP = re.compile(r"(_ms$|^timing_ms$|^latency|^wall_s$|^previous_latency)")


def clean(x):
    if isinstance(x, dict):
        y = {k: clean(v) for k, v in x.items() if not SKIP.search(k)}
        if "level" in y and isinstance(x.get("messages"), list) and not y.get("messages"):
            y["level"] = "<no non-latency message>"   # the level then follows the wall-clock latency budget only
        return y
    if isinstance(x, list):
        return [clean(v) for v in x if not (isinstance(v, str) and "latency" in v)]
    if isinstance(x, str) and "latency" in x:
        return "<latency text>"
    return x


def diff(a, b, path=""):
    if type(a) is not type(b):
        return [path or "/"]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out += diff(a[k], b[k], f"{path}/{k}")
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return [f"{path}[len]"]
        out = []
        for i, (u, v) in enumerate(zip(a, b)):
            out += diff(u, v, f"{path}[]")
        return out
    return [] if a == b else [path or "/"]


def is_stop(r):
    return r.get("decision") == "STOP" if "decision" in r else bool(r.get("obstacle"))


def load(p):
    with open(p) as f:
        return [json.loads(line) for line in f if line.strip()]


def compare(A, B):
    assert len(A) == len(B), f"row counts differ: {len(A)} vs {len(B)}"
    fields, changed, lost, added = Counter(), [], [], []
    for i, (a, b) in enumerate(zip(A, B)):
        d = diff(clean(a), clean(b))
        if d:
            changed.append(i)
            fields.update(set(d))
        if is_stop(a) and not is_stop(b):
            lost.append(i)
        if is_stop(b) and not is_stop(a):
            added.append(i)
    return dict(rows=len(A), rows_changed=len(changed), stop_ctrl=sum(map(is_stop, A)), stop_cand=sum(map(is_stop, B)),
                stop_lost=lost, stop_added=added, changed_rows=changed, fields=dict(fields.most_common()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control")
    ap.add_argument("candidate")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json")
    ap.add_argument("--show", type=int, default=20)
    a = ap.parse_args()
    A, B = load(a.control), load(a.candidate)
    if a.selftest:
        s0 = compare(A, A)
        assert s0["rows_changed"] == 0 and not s0["stop_lost"], s0
        bad = copy.deepcopy(B)
        k = next(i for i, r in enumerate(bad) if is_stop(r)) if any(map(is_stop, bad)) else None
        j = len(bad) // 2
        bad[j]["__injected__"] = 1
        if k is not None:
            if "decision" in bad[k]:
                bad[k]["decision"] = "CAUTION"
            else:
                bad[k]["obstacle"] = False
        s1 = compare(B, bad)
        assert j in s1["changed_rows"], "injected field change not found"
        assert k is None or s1["stop_lost"] == [k], "injected STOP loss not found"
        print("selftest PASS (self-comparison clean; injected field change"
              + (" and STOP loss" if k is not None else "") + " found)")
    s = compare(A, B)
    print(json.dumps({k: v for k, v in s.items() if k not in ("changed_rows",)})[:4000])
    print("changed rows (first %d):" % a.show, s["changed_rows"][:a.show])
    if a.json:
        json.dump(s, open(a.json, "w"), indent=1)
    return 1 if s["stop_lost"] else 0


if __name__ == "__main__":
    sys.exit(main())
