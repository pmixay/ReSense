"""Row-level comparison of two gate summary JSONs: every leaf except latency, run metadata, code/config identity."""
import json, sys
SKIP = {"created", "code", "config", "native", "run", "latency_ms", "schema"}
def leaves(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if p == "" and k in SKIP:
                continue
            if "latency" in k or k in ("timing_ms", "wall_s", "elapsed_s"):
                continue
            yield from leaves(v, f"{p}/{k}")
    elif isinstance(o, list) and o and all(isinstance(x, (dict, list)) for x in o):
        for i, v in enumerate(o):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, o
a = dict(leaves(json.load(open(sys.argv[1])))); b = dict(leaves(json.load(open(sys.argv[2]))))
keys = sorted(set(a) | set(b))
diff = [k for k in keys if a.get(k) != b.get(k)]
print(f"{sys.argv[1].split('/')[-1]} vs {sys.argv[2].split('/')[-1]}: {len(keys)} leaves, {len(diff)} differ")
for k in diff[:12]:
    print("  ", k, a.get(k), "->", b.get(k))
