"""Are the organizers' markers published only while the object has returns, and what is inside the small boxes?

For every marker id of one marked bag: the points inside its box (grown by 5 cm) in every frame where the marker is
present, and inside the box linearly interpolated between two appearances in every frame where it is missing.
For the dust-size boxes (largest extent < 0.1 m): the points within 0.1 m and 0.3 m of the box centre in the six
frames before and after, at the same sensor-frame position.

    python marker_visibility.py <bag dir> <markers.jsonl> <out.json>
"""
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from marker_frames import clouds  # noqa: E402


def count(xyz, lo, hi, m=0.05):
    return int(((xyz >= lo - m) & (xyz <= hi + m)).all(1).sum())


bag, mk, out = sys.argv[1], sys.argv[2], sys.argv[3]
rows = [json.loads(line) for line in open(mk)]
box = {}
for r in rows:
    for m in r["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            box.setdefault(m["id"], {})[r["i"]] = (np.array(m["pts_min"]), np.array(m["pts_max"]))
missing = {}
for mid, fr in box.items():
    fs = sorted(fr)
    for f0, f1 in zip(fs, fs[1:]):
        for f in range(f0 + 1, f1):
            t = (f - f0) / (f1 - f0)
            missing.setdefault(mid, {})[f] = tuple(fr[f0][k] * (1 - t) + fr[f1][k] * t for k in (0, 1))
dust = [(f, mid, (lo + hi) / 2) for mid, fr in box.items() for f, (lo, hi) in fr.items() if (hi - lo).max() < 0.1]
db3 = sorted(glob.glob(os.path.join(bag, "*.db3")))[0]
pres, miss, near = {}, {}, {}
for i, xyz in clouds(db3, set(range(len(rows)))):
    for mid, fr in box.items():
        if i in fr:
            pres.setdefault(mid, []).append(count(xyz, *fr[i]))
        if i in missing.get(mid, {}):
            miss.setdefault(mid, []).append((i, count(xyz, *missing[mid][i])))
    for f, mid, c in dust:
        if abs(i - f) <= 6:
            d = np.linalg.norm(xyz - c, axis=1)
            near.setdefault((f, mid), []).append((i, int((d <= 0.1).sum()), int((d <= 0.3).sum())))
res = {"per_id": {}, "dust": []}
for mid in sorted(box):
    p, q = pres.get(mid, []), miss.get(mid, [])
    res["per_id"][mid] = {"present": len(p), "present_empty": sum(v == 0 for v in p), "present_min": min(p),
                          "missing_between": len(q), "missing_empty": sum(v == 0 for _, v in q),
                          "missing_nonzero": [x for x in q if x[1]]}
    print(f"id {mid:2d}: present {len(p):4d} frames (empty {res['per_id'][mid]['present_empty']}, min {min(p)} points); "
          f"missing between appearances {len(q):3d} (empty {res['per_id'][mid]['missing_empty']}); nonzero {[x for x in q if x[1]][:5]}")
for (f, mid), s in sorted(near.items()):
    own = next(v for v in s if v[0] == f)
    others = [v for v in s if v[0] != f]
    rec = {"frame": f, "id": mid, "own_le_0.1m": own[1], "own_le_0.3m": own[2],
           "others_max_le_0.1m": max(v[1] for v in others), "others_frames_nonzero_le_0.1m": sum(v[1] > 0 for v in others),
           "series": s}
    res["dust"].append(rec)
    print(f"dust box frame {f} id {mid}: {own[1]} points within 0.1 m in its frame; the 12 neighbouring frames: "
          f"max {rec['others_max_le_0.1m']}, nonzero in {rec['others_frames_nonzero_le_0.1m']}")
tp = sum(v["present"] for v in res["per_id"].values())
tp0 = sum(v["present_empty"] for v in res["per_id"].values())
tm = sum(v["missing_between"] for v in res["per_id"].values())
tm0 = sum(v["missing_empty"] for v in res["per_id"].values())
res["totals"] = {"present": tp, "present_empty": tp0, "missing_between": tm, "missing_empty": tm0}
print(f"TOTAL present boxes {tp} (empty {tp0}); interpolated missing boxes {tm} (empty {tm0})")
json.dump(res, open(out, "w"))
