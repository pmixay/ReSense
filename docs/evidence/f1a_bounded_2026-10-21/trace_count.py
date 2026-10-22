#!/usr/bin/env python3
"""Read-only branch counter: runs another script (runpy, same argv after '--') with lowobj.rail_head_top and
resense.detector.rail_reference_check wrapped, and writes how often the bounded branch was reached (rail_head_top
called), returned a head top, and how many clusters the check rejected that the same call with the switch off would
keep (= rejections by the new branch), with frame-order samples. The wrapped functions' results are returned
unchanged; the caller compares the traced output with a plain run.

    python trace_count.py <counts.json> -- <script.py> <args...>
"""
import dataclasses, json, runpy, sys
counts_path = sys.argv[1]
assert sys.argv[2] == "--"
script, rest = sys.argv[3], sys.argv[4:]
from resense import lowobj
import resense.detector as detm
C = dict(check_calls=0, head_calls=0, head_values=0, new_branch_rejections=0, samples=[])
orig_head, orig_check = lowobj.rail_head_top, detm.rail_reference_check

def head(*a, **k):
    r = orig_head(*a, **k)
    C["head_calls"] += 1
    C["head_values"] += r is not None
    return r

def check(clusters, X, dy, h, cfg, sp, free=None):
    C["check_calls"] += 1
    out = orig_check(clusters, X, dy, h, cfg, sp, free)
    if cfg.rail_head_bounded and out:
        lowobj.rail_head_top = orig_head          # the off-run must not be counted
        off = orig_check(clusters, X, dy, h, dataclasses.replace(cfg, rail_head_bounded=False), sp, free)
        lowobj.rail_head_top = head
        new = [c for c in out if not any(c is o for o in off)]
        C["new_branch_rejections"] += len(new)
        for c in new:
            if len(C["samples"]) < 200:
                C["samples"].append(dict(call=C["check_calls"], d=round(float(c.distance), 2),
                                         lat=round(float(c.lateral), 3), cap=round(float(c.height_max), 3)))
    return out

lowobj.rail_head_top = head
detm.rail_reference_check = check
sys.argv = [script, *rest]
try:
    runpy.run_path(script, run_name="__main__")
finally:
    json.dump(C, open(counts_path, "w"), indent=1)
    print("trace_count:", {k: v for k, v in C.items() if k != "samples"}, file=sys.stderr)
