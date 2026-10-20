"""Match the STOP detections of a judge_runner.py run to the organizers' marker boxes of the same frame.

A detection matches a box when its near-face distance `d` is within max(3 m, 3 %) of the box's near face (sensor
forward = -y) and its centre's lateral `c[1]` within 1.5 m of the box's lateral centre (the run's vehicle frame is the
mount-calibrated sensor frame, close to the sensor axes on these bags). Prints per bag: STOP frames, STOP detections
matched to an object box / to a dust-size box (largest extent < 0.1 m) / to nothing, the unmatched ones listed, and
the decision in every frame that has a dust-size box.

    python stops_vs_markers.py <run.jsonl> <markers.jsonl> <out.json>
"""
import json
import sys

import numpy as np

run = [json.loads(line) for line in open(sys.argv[1])]
mk = {}
for line in open(sys.argv[2]):
    r = json.loads(line)
    mk[r["i"]] = []
    for m in r["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            mk[r["i"]].append({"id": m["id"], "near": float(-hi[1]), "lat": float((lo[0] + hi[0]) / 2),
                               "dust": bool((hi - lo).max() < 0.1)})
res = {"stop_frames": 0, "stop_dets": 0, "matched_object": 0, "matched_dust": 0, "unmatched": [], "dust_frames": []}
for r in run:
    boxes = mk.get(r["i"], [])
    if any(b["dust"] for b in boxes):
        res["dust_frames"].append({"frame": r["i"], "decision": r["decision"],
                                   "dust_boxes": [(b["id"], round(b["near"], 2), round(b["lat"], 2)) for b in boxes if b["dust"]],
                                   "dets": [(d["d"], d["lat"], d["kind"]) for d in r["dets"]],
                                   "warns": [(d["d"], d["lat"]) for d in r["warns"]]})
    if r["decision"] != "STOP":
        continue
    res["stop_frames"] += 1
    for d in r["dets"]:
        res["stop_dets"] += 1
        hit = [b for b in boxes if abs(d["d"] - b["near"]) <= max(3.0, 0.03 * b["near"]) and abs(d["c"][1] - b["lat"]) <= 1.5]
        if any(not b["dust"] for b in hit):
            res["matched_object"] += 1
        elif hit:
            res["matched_dust"] += 1
        else:
            near = min(boxes, key=lambda b: abs(b["near"] - d["d"]), default=None)
            res["unmatched"].append({"frame": r["i"], "d": d["d"], "c": d["c"], "size": d["size"], "n": d["n"], "kind": d["kind"],
                                     "nearest_box": None if near is None else (near["id"], round(near["near"], 2), round(near["lat"], 2))})
print(f"STOP frames {res['stop_frames']}, STOP detections {res['stop_dets']}: matched to an object box {res['matched_object']}, "
      f"to a dust box {res['matched_dust']}, to nothing {len(res['unmatched'])}")
for u in res["unmatched"]:
    print("  unmatched", u)
for f in res["dust_frames"]:
    print("  dust frame", f)
json.dump(res, open(sys.argv[3], "w"), indent=1)
