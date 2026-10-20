"""Independent per-frame comparison of two Falcon record files: every field except wall-clock timing."""
import json, sys
TIMING = {"decode_ms", "detect_ms", "total_ms"}
def strip(r):
    return {k: v for k, v in r.items() if k not in TIMING}
a = [json.loads(l) for l in open(sys.argv[1])]; b = [json.loads(l) for l in open(sys.argv[2])]
assert len(a) == len(b)
diff = [i for i, (x, y) in enumerate(zip(a, b)) if strip(x) != strip(y)]
dec = [i for i, (x, y) in enumerate(zip(a, b)) if x["decision"] != y["decision"]]
keys = sorted({k for i in diff for k in strip(a[i]) if strip(a[i]).get(k) != strip(b[i]).get(k)})
print(f"{sys.argv[1].split('/')[-1]} vs {sys.argv[2].split('/')[-1]}: rows {len(a)}, differ {len(diff)} {diff[:10]}, decisions differ {len(dec)}, fields {keys}")
