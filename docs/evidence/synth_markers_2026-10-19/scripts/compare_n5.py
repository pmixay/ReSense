"""Compare the organizers' marker objects (marker_objects.py) with the team's N5 labels of 17.10.

Both are in the sensor frame mapped to forward = -y, left = +x, up = +z. Dust-size objects (largest extent < 0.1 m)
are left out. A marker object and an N5 row of the same frame match when the N5 row's near face is within
max(2 m, 2 %) of the marker object's near face and their lateral centres are within 1 m. Per marker object: the frames
it is marked, how many of them carry a matching N5 row and under which N5 names, and the median distance offset;
per N5 track: how many of its rows match no marker object.

    python compare_n5.py <bag>_objects.json labels_synthetic_<bag>.json <out.json>
"""
import json
import sys
from collections import Counter

import numpy as np

mk = json.load(open(sys.argv[1]))["objects"]
n5 = json.load(open(sys.argv[2]))
rows = {int(k): v for k, v in n5.items() if k != "_meta"}
objs = [o for o in mk if max(o["size_max"]) >= 0.1]


def match(fwd, lat, r):
    return abs(r["distance"] - fwd) <= max(2.0, 0.02 * fwd) and abs(r["lateral_sensor"] - lat) <= 1.0


out = {"marker_objects": [], "n5_tracks": {}}
used = Counter()
n5_total = Counter(r["name"] for v in rows.values() for r in v)
for k, o in enumerate(objs, 1):
    names, dd, hit = Counter(), [], 0
    n5_frames = [f for f, _, _ in o["track"] if rows.get(f)]
    for f, fwd, lat in o["track"]:
        m = [r for r in rows.get(f, []) if match(fwd, lat, r)]
        if m:
            hit += 1
            r = min(m, key=lambda r: abs(r["distance"] - fwd))
            names[r["name"]] += 1
            used[(f, r["name"])] += 1
            dd.append(r["distance"] - fwd)
    in_range = [t for t in o["track"] if 2.5 <= t[1] <= 250]
    rec = {"object": k, "ids": o["ids"], "frames": [o["first"], o["last"]], "marked_frames": o["n_frames"],
           "marked_frames_2.5_250m": len(in_range), "with_n5_match": hit, "n5_names": dict(names),
           "median_n5_minus_marker_m": round(float(np.median(dd)), 2) if dd else None,
           "first_marked_fwd": o["fwd_first"], "size_fwd_lat_up": o["size_median_fwd_lat_up"],
           "lat_centre_first_last": o["lat_centre_first_last"], "frames_with_any_n5_row": len(n5_frames)}
    out["marker_objects"].append(rec)
    print(f"marker object {k} ids {o['ids']} frames {o['first']}-{o['last']} ({o['n_frames']} marked, "
          f"{len(in_range)} at 2.5-250 m): N5 match in {hit} frames {dict(names)}; median N5 - marker "
          f"{rec['median_n5_minus_marker_m']} m; size {o['size_median_fwd_lat_up']}")
by_frame = {}
for o in objs:
    for f, fwd, lat in o["track"]:
        by_frame.setdefault(f, []).append((o["ids"], fwd, lat))
for name, total in sorted(n5_total.items()):
    matched = sum(v for (f, n), v in used.items() if n == name)
    unmatched = []
    for f, v in sorted(rows.items()):
        for r in v:
            if r["name"] == name and (f, name) not in used:
                near = min(by_frame.get(f, []), key=lambda m: abs(m[1] - r["distance"]), default=None)
                unmatched.append({"frame": f, "n5_distance": round(r["distance"], 2), "n5_lateral": round(r["lateral_sensor"], 2),
                                  "n5_points": r.get("n_points"), "nearest_marker": None if near is None else
                                  {"ids": near[0], "fwd": near[1], "lat": near[2]}})
    out["n5_tracks"][name] = {"rows": total, "matched_to_a_marker": matched, "unmatched": unmatched}
    print(f"N5 track {name}: {total} rows, {matched} match a marker object, {total - matched} do not")
    for u in unmatched:
        print("    unmatched", u)
json.dump(out, open(sys.argv[3], "w"), indent=1)
