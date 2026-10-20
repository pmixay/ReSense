"""Every X3 raw row whose decision / detections / warnings differ between two battery runs, per case, with both sides'
objects; each STOP row added or lost is matched against the case's labels with the battery's own matcher
(``robustness_battery.matches``: distance + lateral bbox, plausible non-zero labels), and the other non-timing fields
that differ in rows where the decision is equal are named.

    RESENSE_REPO=<tree> python x3_rows.py <reference x3.json> <candidate x3.json> [labels json]
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.environ["RESENSE_REPO"], "scripts"))
from robustness_battery import matches  # noqa: E402

TIMING = {"decode_ms", "detect_ms", "total_ms"}
ref, cur = (json.load(open(p)) for p in sys.argv[1:3])
labels = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}


def objs(ds):
    return [(d["d"], d["lat"], d["kind"], d["reason"], d["zone"]) for d in ds]


tot = {"cases_differ": 0, "dec_rows": 0, "stop_added": 0, "stop_added_matched": 0, "stop_lost": 0, "other_rows": 0}
other_keys = {}
for case in ref["entries"]:
    a = [json.loads(x) for x in open(ref["entries"][case]["raw_path"])]
    b = [json.loads(x) for x in open(cur["entries"][case]["raw_path"])]
    bag = case.split("/")[0]
    lab = labels if bag == "cloud_with_fake_obj" else {}
    rows = []
    for x, y in zip(a, b):
        same = (x["decision"], x["dets"], x["warns"]) == (y["decision"], y["dets"], y["warns"])
        if not same:
            rows.append((x, y))
        else:
            diff = [k for k in x if k not in TIMING and x[k] != y[k]]
            diff = [k for k in diff if k not in ("level", "dlevel", "msgs")]
            if diff:
                tot["other_rows"] += 1
                for k in diff:
                    other_keys[k] = other_keys.get(k, 0) + 1
    if not rows:
        continue
    tot["cases_differ"] += 1
    print(f"== {case}: {len(rows)} rows differ in decision/dets/warns")
    for x, y in rows:
        tot["dec_rows"] += 1
        added = y["decision"] == "STOP" and x["decision"] != "STOP"
        lost = x["decision"] == "STOP" and y["decision"] != "STOP"
        tot["stop_added"] += added
        tot["stop_lost"] += lost
        match = None
        if added:
            objs_l = [o for o in lab.get(f"{y['i']:05d}", []) if o.get("n_points", 1) and o.get("plausible", True)]
            match = [o.get("label", o.get("name")) for o in objs_l if any(matches(d, o) for d in y["dets"])]
            tot["stop_added_matched"] += bool(match)
        print(f"   row {y['i']}: {x['decision']} -> {y['decision']}  ref dets {objs(x['dets'])} warns {objs(x['warns'])} | "
              f"cur dets {objs(y['dets'])} warns {objs(y['warns'])}" + (f" | label match {match}" if added else ""))
print("TOTAL", json.dumps(tot), "other non-timing fields in rows with equal decision/dets/warns:", other_keys)
