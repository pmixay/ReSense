"""X3 of a candidate against a reference X3 run measured without ``--reference``: the battery's own per-case comparison
(``robustness_battery.compare_metrics``, its tolerances) and, per case, the raw probe records compared frame by frame
(decision, detections and warnings; every other non-timing field counted separately).

    RESENSE_REPO=<tree with scripts/robustness_battery.py> python x3_compare.py <reference.json> <candidate.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.environ["RESENSE_REPO"], "scripts"))
from robustness_battery import compare_metrics  # noqa: E402

TIMING = {"decode_ms", "detect_ms", "total_ms"}
ref, cur = (json.load(open(p)) for p in sys.argv[1:3])
print(f"reference {sys.argv[1]}: status {ref['status']}, commit {ref['evaluation']['commit'][:10]}, {len(ref['entries'])} cases")
print(f"candidate {sys.argv[2]}: status {cur['status']}, commit {cur['evaluation']['commit'][:10]}, {len(cur['entries'])} cases")
assert set(ref["entries"]) == set(cur["entries"]), "case lists differ"
fails, total, same_cases = [], 0, 0
for case in ref["entries"]:
    rows = compare_metrics(ref["entries"][case]["metrics"], cur["entries"][case]["metrics"])
    total += len(rows)
    fails += [(case, r) for r in rows if not r["passed"]]
    a = [json.loads(line) for line in open(ref["entries"][case]["raw_path"])]
    b = [json.loads(line) for line in open(cur["entries"][case]["raw_path"])]
    dec = sum((x["decision"], x["dets"], x["warns"]) != (y["decision"], y["dets"], y["warns"]) for x, y in zip(a, b))
    other = sum({k: v for k, v in x.items() if k not in TIMING} != {k: v for k, v in y.items() if k not in TIMING}
                for x, y in zip(a, b))
    stop_a = {x["i"] for x in a if x["decision"] == "STOP"}
    stop_b = {x["i"] for x in b if x["decision"] == "STOP"}
    same_cases += len(a) == len(b) and dec == 0
    print(f"{case:50s} rows {len(a):5d}/{len(b):5d}  decision/dets/warns differ {dec:4d}  any non-timing {other:4d}  "
          f"STOP rows {len(stop_a)} -> {len(stop_b)} (+{len(stop_b - stop_a)} -{len(stop_a - stop_b)})")
print(f"\ncases with every row's decision, detections and warnings equal: {same_cases} of {len(ref['entries'])}")
print(f"battery comparison: {len(fails)} failed of {total}")
for case, r in fails:
    print(f"   {case:50s} {r['metric']:40s} ref {r['baseline']} -> {r['current']} (worse by {r['worse_by']}, tol {r['tolerance']})")
