#!/usr/bin/env python3
"""Gated rows (and key info rows) of several gate JSONs side by side; a row is listed when any run differs from the
first. Verdict marks per run vs the first: '<' worse, '>' better.   gate_table.py tag=gate.json ..."""
import json, os, sys
sys.path.insert(0, "/home/user/ReSense-k2/scripts")
import regression_gate as rg
runs = [(a.split("=", 1)[0], json.load(open(a.split("=", 1)[1]))) for a in sys.argv[1:]]
ms = [(t, rg.metrics(r)) for t, r in runs]
base = ms[0][1]
keys = list(base)
print("| metric | gated | " + " | ".join(t for t, _ in ms) + " |")
print("|---|---|" + "---|" * len(ms))
nworse = {t: 0 for t, _ in ms}
for k in keys:
    v0, d, g = base[k]
    vals = [m.get(k, (None,))[0] for _, m in ms]
    if all(v == v0 for v in vals) or d == rg.INFO or k.startswith("latency"):
        continue
    cells = []
    for (t, m), v in zip(ms, vals):
        vd = rg.verdict(v0, v, d) if t != ms[0][0] else ""
        mark = " **worse**" if vd == "worse" and g else (" worse" if vd == "worse" else (" better" if vd == "better" else ""))
        if vd == "worse" and g:
            nworse[t] += 1
        cells.append(f"{v}{mark}")
    if g or k.split(".")[0] in ("five_empty", "ride") or "alarm" in k or "stop" in k:
        print(f"| {k} | {'yes' if g else ''} | " + " | ".join(cells) + " |")
print("gated rows worse:", nworse)
