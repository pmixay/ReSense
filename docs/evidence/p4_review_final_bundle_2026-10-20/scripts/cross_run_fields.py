"""Two independent runs of the same source (different machine and native build): which fields differ, by how much.

    python cross_run_fields.py gate <dirA> <dirB>
    python cross_run_fields.py x3   <rawA> <rawB>
    python cross_run_fields.py jsonl <fileA> <fileB>

Wall-clock fields and health level/messages are skipped (levels are checked for a latency explanation). Everything else
is compared exactly; numeric differences are summarised by their maximum. ``decision-bearing`` rows are rows where any
of obstacle / warning / decision / nearest / clear / monitored / detections / warnings differs.
"""
import collections
import os
import sys

from common import flat, jsonl, level_explained, levels

SKIP_TOP = {"timing_ms", "decode_ms", "detect_ms", "total_ms", "level", "dlevel", "msgs"}
DEC = ("obstacle", "warning", "decision", "nearest", "nearest_distance", "clear", "clear_distance", "monitored",
       "dets", "detections", "warns", "warnings", "n_points")


def pairs(mode, a, b):
    if mode == "gate":
        for f in sorted(x for x in os.listdir(a) if x.endswith(".jsonl")):
            yield jsonl(f"{a}/{f}"), jsonl(f"{b}/{f}")
    elif mode == "x3":
        for s in sorted(os.listdir(a)):
            for v in sorted(os.listdir(f"{a}/{s}")):
                yield jsonl(f"{a}/{s}/{v}/probe.jsonl"), jsonl(f"{b}/{s}/{v}/probe.jsonl")
    else:
        yield jsonl(a), jsonl(b)


mode, a, b = sys.argv[1:4]
rows = dec_rows = lvl = lvl_unexpl = 0
cat = collections.Counter()
mx = collections.defaultdict(float)
for A, B in pairs(mode, a, b):
    assert len(A) == len(B)
    for x, y in zip(A, B):
        rows += 1
        if any(x.get(k) != y.get(k) for k in DEC if k in x or k in y):
            dec_rows += 1
        if levels(x) != levels(y):
            lvl += 1
            lvl_unexpl += not level_explained(x, y)

        def strip(r):
            r = {k: v for k, v in r.items() if k not in SKIP_TOP}
            if "health" in r:
                r["health"] = {k: v for k, v in r["health"].items() if k not in ("level", "decision_level", "messages", "latency_p95_ms")}
            return r
        fx, fy = dict(flat(strip(x))), dict(flat(strip(y)))
        for k in set(fx) | set(fy):
            if fx.get(k) != fy.get(k):
                cat[k] += 1
                u, v = fx.get(k), fy.get(k)
                if isinstance(u, (int, float)) and isinstance(v, (int, float)):
                    mx[k] = max(mx[k], abs(u - v))
print(f"rows {rows} | rows with a change in a decision-bearing field {dec_rows} | level differences {lvl} (not explained by a latency message: {lvl_unexpl})")
for k, n in cat.most_common():
    print(f"   {k:28s} rows {n:6d}  max |diff| {mx[k]:.3e}")
if not cat:
    print("   no other field differs")
