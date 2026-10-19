import json, sys
TIMING = {"decode_ms", "detect_ms", "total_ms"}
def norm(r):
    r = {k: v for k, v in r.items() if k not in TIMING}
    r["msgs"] = [m for m in r.get("msgs", []) if "latency" not in m]
    return r
a = [json.loads(l) for l in open(sys.argv[1])]
b = [json.loads(l) for l in open(sys.argv[2])]
diff = [i for i, (x, y) in enumerate(zip(a, b)) if norm(x) != norm(y)]
dec = [i for i, (x, y) in enumerate(zip(a, b)) if x["decision"] != y["decision"]]
lat = [i for i, (x, y) in enumerate(zip(a, b)) if norm(x) != norm(y) and {k: v for k, v in x.items() if k not in TIMING and k != "msgs"} == {k: v for k, v in y.items() if k not in TIMING and k != "msgs"}]
print(json.dumps({"rows": [len(a), len(b)], "non_timing_diff_rows": len(diff), "first": diff[:10],
                  "decision_diff_rows": len(dec), "decision_first": dec[:20]}))
