#!/usr/bin/env python3
"""Fields that differ between two dev jsonl runs at given frames.   devdiff.py A.jsonl B.jsonl i [i ...]"""
import json, sys
A = [json.loads(l) for l in open(sys.argv[1])]
B = [json.loads(l) for l in open(sys.argv[2])]
def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from flat(v, f"{p}.{k}" if p else k)
    elif isinstance(d, list) and d and isinstance(d[0], dict):
        for i, v in enumerate(d):
            yield from flat(v, f"{p}[{i}]")
    else:
        yield p, d
for i in map(int, sys.argv[3:]):
    a, b = dict(flat(A[i])), dict(flat(B[i]))
    diffs = [(k, a.get(k), b.get(k)) for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k) and "timing" not in k and "latency" not in k]
    print(i, [(k, x, y) for k, x, y in diffs][:14])
