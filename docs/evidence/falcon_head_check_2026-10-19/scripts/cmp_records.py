"""Compare two per-frame jsonl record files field by field (everything except wall-clock timing).

    python cmp_records.py <a.jsonl> <b.jsonl> [first N frames]
"""
import json
import sys

SKIP = {"decode_ms", "detect_ms", "total_ms", "msgs", "bag_t"}   # timing; health message text is compared below


def load(path, n=None):
    out = []
    with open(path) as f:
        for k, line in enumerate(f):
            if n and k >= n:
                break
            out.append(json.loads(line))
    return out


limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
a, b = load(sys.argv[1], limit), load(sys.argv[2], limit)
print("frames compared:", min(len(a), len(b)), "(a=%d, b=%d)" % (len(a), len(b)))
diff_fields, first, msgs_diff = {}, {}, 0
for x, y in zip(a, b):
    for k in x:
        if k in SKIP:
            continue
        if x.get(k) != y.get(k):
            diff_fields[k] = diff_fields.get(k, 0) + 1
            first.setdefault(k, x["i"])
    if [m for m in x.get("msgs", []) if "latency" not in m] != [m for m in y.get("msgs", []) if "latency" not in m]:
        msgs_diff += 1
print("fields that differ (count of frames, first frame):", {k: (v, first[k]) for k, v in diff_fields.items()} or "NONE")
print("health messages differing (ignoring the wall-clock latency line):", msgs_diff)
pairs = {}
for x, y in zip(a, b):
    key = (x["decision"], y["decision"])
    pairs[key] = pairs.get(key, 0) + 1
print("decision pairs (a,b):", pairs)
