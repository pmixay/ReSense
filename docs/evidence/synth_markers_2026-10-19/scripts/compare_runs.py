"""Compare two judge_runner.py runs (<a>.jsonl, <b>.jsonl) frame by frame, every field except wall-clock timing.

Timing fields (decode_ms, detect_ms, total_ms) are skipped. The health fields `msgs` and `level` are compared after
dropping the latency messages ("latency p95 ... over the ... budget"), which come from wall-clock time; a frame whose
`level` differs is counted as timing-only when both sides have no message left after that.

    python compare_runs.py <a.jsonl> <b.jsonl>
"""
import json
import sys
from collections import Counter

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def load(p):
    return [json.loads(line) for line in open(p)]


def no_latency(msgs):
    return [m for m in msgs if not m.startswith("latency ")]


a, b = load(sys.argv[1]), load(sys.argv[2])
print(f"frames {len(a)} vs {len(b)}; key sets equal: {set(a[0]) == set(b[0])}")
diff, timing_only = {}, []
for x, y in zip(a, b):
    for k in sorted((set(x) | set(y)) - TIMING):
        if k == "msgs":
            same = no_latency(x[k]) == no_latency(y[k])
        elif k == "level":
            same = x[k] == y[k] or (not no_latency(x["msgs"]) and not no_latency(y["msgs"]))
            if x[k] != y[k] and same:
                timing_only.append(x["i"])
        else:
            same = x.get(k) == y.get(k)
        if not same:
            diff.setdefault(k, []).append(x["i"])
print("decisions a:", dict(Counter(r["decision"] for r in a)))
print("decisions b:", dict(Counter(r["decision"] for r in b)))
print(f"frames whose health level differs only by latency messages: {len(timing_only)} {timing_only[:12]}")
if diff:
    for k, v in diff.items():
        print(f"DIFFERENT {k}: {len(v)} frames, first {v[:8]}")
else:
    print(f"IDENTICAL in every non-timing field on all {min(len(a), len(b))} frames")
