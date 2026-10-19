"""Compare two regression-gate JSONs on every leaf except timing / provenance fields."""
import json, sys
SKIP = {"created", "code", "config", "native", "run", "latency_ms", "gate", "health", "schema"}
def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in SKIP or "latency" in k:
                continue
            walk(a.get(k), b.get(k), path + "/" + k, out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and any(isinstance(x, (dict, list)) for x in a):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, f"{path}[{i}]", out)
    elif a != b:
        out.append((path, a, b))
a, b = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
out = []
walk(a, b, "", out)
n = []
def count(o):
    if isinstance(o, dict):
        return sum(count(v) for k, v in o.items() if k not in SKIP)
    if isinstance(o, list):
        return sum(count(v) for v in o) if any(isinstance(x, (dict, list)) for x in o) else 1
    return 1
print(json.dumps({"leaves_compared": count(a), "differences": len(out)}))
for p, x, y in out[:60]:
    print(f"  {p}: {x!r} -> {y!r}")
