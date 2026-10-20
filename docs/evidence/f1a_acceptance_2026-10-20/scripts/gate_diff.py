"""Every row of two regression_gate.py JSONs that differs, timing, latency, code identity and run settings left out.

    python -I gate_diff.py <gate a.json> <gate b.json>
"""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])


def flat(d, p=""):
    if isinstance(d, dict):
        for k, v in d.items():
            yield from flat(v, f"{p}.{k}" if p else k)
    else:
        yield p, d


fa, fb = dict(flat(a)), dict(flat(b))
skip = ("latency", "code.", "timing", "wall", "gate.", "env", "elapsed", "created", "host")
for k in sorted(set(fa) | set(fb)):
    if any(s in k for s in skip):
        continue
    if fa.get(k) != fb.get(k):
        print(f"{k:60s} {str(fa.get(k))[:40]:>20s}  {str(fb.get(k))[:40]:>20s}")
