"""X3: the battery report's per-case metrics and its 260 comparisons against the raw rows.

    python x3_entries.py <x3 report json> <raw dir>
"""
import collections
import hashlib
import json
import sys

d = json.load(open(sys.argv[1]))
raw = sys.argv[2]
mism = rows = stops = sha_bad = 0
for key, e in d["entries"].items():
    s, v = key.split("/")
    p = f"{raw}/{s}/{v}/probe.jsonl"
    R = [json.loads(line) for line in open(p)]
    rows += len(R)
    m = e["metrics"]
    dec = collections.Counter(r["decision"] for r in R)
    st = dec.get("STOP", 0)
    stops += st
    ep = sum(1 for i, r in enumerate(R) if r["decision"] == "STOP" and (i == 0 or R[i - 1]["decision"] != "STOP"))
    first = next((i for i, r in enumerate(R) if r["decision"] == "STOP"), None)
    # hz5 cases keep the original frame number: first_stop_frame is the row index times the decimation (2)
    step = 2 if v == "hz5" else 1
    ok = (m["frames"], m["stop_frames"], m["stop_episodes"]) == (len(R), st, ep) \
        and {k: n for k, n in m["decisions"].items() if n} == dict(dec) \
        and (m["first_stop_frame"] == (None if first is None else first * step))
    if not ok:
        mism += 1
        print("MISMATCH", key)
    sha_bad += hashlib.sha256(open(p, "rb").read()).hexdigest() != e["raw_sha256"]
comp = d["comparison"]["cases"]
print(f"entries {len(d['entries'])} rows {rows} STOP rows {stops}; metrics differing from the raw recount {mism}; raw sha256 mismatches {sha_bad}")
print(f"comparisons {sum(len(x) for x in comp.values())} passed {sum(c['passed'] for x in comp.values() for c in x)} in {len(comp)} cases; status {d['status']}; errors {len(d['errors'])}")
print("harness", d["harness_commit"][:7], "evaluated", d["evaluation"]["commit"][:7], d["evaluation"]["version"])
