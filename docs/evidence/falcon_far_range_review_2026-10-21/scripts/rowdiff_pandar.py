"""Per-frame row comparison of two gate-style JSONL runs: every field except timing (keys containing ms/time/wall/latency;
health messages that mention latency). Prints the count of differing rows and the first differing fields."""
import json, sys
def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items() if not any(t in k for t in ("ms", "time", "wall", "latency"))}
    if isinstance(o, list):
        return [clean(x) for x in o if not (isinstance(x, str) and "latency" in x)]
    return o
A = [json.loads(l) for l in open(sys.argv[1])]; B = [json.loads(l) for l in open(sys.argv[2])]
diff = [i for i, (a, b) in enumerate(zip(A, B)) if clean(a) != clean(b)]
fields = sorted({k for i in diff for k in clean(A[i]) if clean(A[i]).get(k) != clean(B[i]).get(k)})
print(sys.argv[1].split('/')[-2:], len(A), len(B), "differing rows:", len(diff), "fields:", fields[:12],
      "STOP frames A/B:", sum(bool(r.get("obstacle")) for r in A), sum(bool(r.get("obstacle")) for r in B))
