"""Summarize retained author sight diagnostics without changing measurements."""
from collections import Counter
import json
from pathlib import Path
import sys

p = Path(sys.argv[1])
rows = json.loads(p.read_text())
for lo, hi in [(0, 30), (30, 60), (60, 100), (100, 150), (150, 250)]:
    group = [r for r in rows if lo <= r["x"] < hi]
    print(lo, hi, len(group), Counter(r["answer"] for r in group))
    fails = [r for r in group if not r["answer"]]
    print("proof reasons", Counter(tuple((x["kind"], x.get("answer"), x.get("moved")) for x in r["proof"])
                                   for r in fails))
    for r in fails[:2]:
        print(json.dumps({k: v for k, v in r.items() if k not in ("xyz", "h", "dy")}))
