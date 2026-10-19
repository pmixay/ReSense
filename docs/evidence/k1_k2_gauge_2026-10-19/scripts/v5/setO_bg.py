#!/usr/bin/env python3
"""Set O background alarms (STOP detections matching no object, track never matched): frames, id, distance,
lateral, size, joint_used.   setO_bg.py <repo> <work dir>"""
import json, os, sys
repo, wd = sys.argv[1], sys.argv[2]
sys.path[:0] = [repo, os.path.join(repo, "scripts")]
from resense.metrics import _assign_detections, load_gt, GTObstacle
gt = load_gt(os.path.join(repo, "labels/cloud_with_fake_obj.json"))
results = [json.loads(l) for l in open(os.path.join(wd, "cloud_with_fake_obj.jsonl"))]
matched, unmatched = set(), []
for r in results:
    rows = [row for row in gt.get(f"{int(r['frame']):05d}", []) if row.get("n_points", 1) > 0]
    gts = [GTObstacle.from_dict(row) for row in rows]
    dets = r.get("detections", [])
    a = _assign_detections(dets, gts)
    used = set(a.values())
    matched.update(int(dets[i]["id"]) for i in used if "id" in dets[i])
    unmatched.append([(int(r["frame"]), d) for i, d in enumerate(dets) if i not in used])
for fr in unmatched:
    for f, d in fr:
        if d.get("id") not in matched:
            t = results[f]["track"]
            print(f, d.get("id"), d["distance"], d["lateral"], d["size"], d.get("kind"), d.get("reason"), "joint_used", t.get("joint_used"),
                  "k %.2e step %.2e av %s" % (t["curvature"], t.get("curv_step", 0), t["axis_valid"]))
