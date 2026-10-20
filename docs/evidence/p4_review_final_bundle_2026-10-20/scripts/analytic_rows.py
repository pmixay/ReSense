"""R3's 32 analytic ray-cast scenes (18 scans each, 576 rows) re-read from the raw rows.

    python analytic_rows.py <analytic-a-candidate.json> <analytic-a-reference.json>

Label: a case is "in the gauge" when its box centre is within 1.0 m of the scene's rail axis (the targets sit at 0.25 m,
or 2.25 m for the two outside controls; any threshold between 0.25 + 1.0 and 2.25 - 1.0 gives the same split). STOP rows
come from the raw detector result of each row (``result.obstacle``), matched rows from the row's own ``matched`` flag.
"""
import json
import statistics
import sys

A, R = (json.load(open(p))["cases"] for p in sys.argv[1:3])
rows = lost = added = ins = outs = no_box_stop = miss = 0
neg, empty, changed = [], [], []
for k, v in A.items():
    ref = R[k]
    ys = [(r["box"][0][2] + r["box"][0][3]) / 2 for r in v["rows"] if r["box"]]
    mc = [i for i, r in enumerate(v["rows"]) if r["matched"]]
    mr = [i for i, r in enumerate(ref["rows"]) if r["matched"]]
    rows += len(v["rows"])
    lost += len(set(mr) - set(mc))
    added += len(set(mc) - set(mr))
    if mc != mr:
        changed.append((k, sorted(set(mc) - set(mr)), sorted(set(mr) - set(mc))))
    for a, b in zip(v["rows"], ref["rows"]):
        da = {json.dumps(d, sort_keys=True) for d in a["result"]["detections"]}
        miss += sum(json.dumps(d, sort_keys=True) not in da for d in b["result"]["detections"])
        no_box_stop += (not a["box"]) and bool(a["result"]["obstacle"])
    if not ys:
        empty.append(k)
        continue
    if abs(statistics.median(ys) - 0.25) <= 1.0:
        ins += len(mc)
    else:
        neg.append(k)
        outs += sum(bool(r["result"]["obstacle"]) for r in v["rows"])
print(f"cases {len(A)} rows {rows} | matched STOP rows lost vs reference {lost}, added {added} | reference detections absent in candidate rows {miss}")
print(f"in-gauge matched STOP rows {ins} | outside-gauge controls {neg}: STOP rows {outs} | scene with no object {empty}: STOP rows with no object in the scene {no_box_stop}")
for c in changed:
    print("   changed:", c)
