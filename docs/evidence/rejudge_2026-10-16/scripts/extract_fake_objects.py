#!/usr/bin/env python3
"""Independent ground truth for cloud_with_fake_obj: the organizers' tool appends the object points at
the end of each message, after the last no-return (0,0,0) slot, all with intensity 1. This script reads
every message's full slot array (no range filter), takes those trailing points, checks their intensity,
maps them to the vehicle frame with the configured axis mapping (no calibration), splits them into objects
at X gaps > 6 m, and links objects across frames (nearest predicted X). It also fits the rails in each
frame (judge_geom.fit_rails) to give each object's lateral offset from the rail axis and its height above
the rail-head plane (extrapolated: uncertain far away).
Output: <out>.json  {frame: [{"x":nearest X, "xmax", "ymin","ymax","zmin","zmax","n", "dy_min","dy_max",
                               "h_min","h_max","track": id}]}
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from judge_geom import fit_rails  # noqa: E402
from judge_runner import NodeReplica, db3_files, iter_raw  # noqa: E402
from resense.pointcloud import pointcloud2_to_structured  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

bag, out = sys.argv[1], sys.argv[2]
R = NodeReplica().R_vs
res = {}
tracks = []      # [last_x, last_frame, id]
bad_int = 0
rail_every = 5
rails = None
for i, (ts, topic, raw) in enumerate(iter_raw(db3_files(bag)[0])):
    msg = fastcloud.parse_pointcloud2(raw)
    arr = pointcloud2_to_structured(fastcloud.packed(msg))
    x, y, z = arr["x"], arr["y"], arr["z"]
    zero = (x == 0) & (y == 0) & (z == 0)
    nz = np.flatnonzero(zero)
    last0 = nz[-1] if len(nz) else -1
    tail = slice(last0 + 1, len(x))
    objs = []
    if last0 + 1 < len(x):
        it = arr["intensity"][tail]
        bad_int += int(np.count_nonzero(it != 1))
        pts = np.c_[x[tail], y[tail], z[tail]].astype(np.float64) @ R.T
        if i % rail_every == 0 or rails is None:
            xyz_s, _, _, _, _ = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
            rails = fit_rails(xyz_s @ R.T) or rails
        o = np.argsort(pts[:, 0])
        pts = pts[o]
        cuts = np.flatnonzero(np.diff(pts[:, 0]) > 6.0) + 1
        for grp in np.split(pts, cuts):
            xs = float(grp[:, 0].min())
            rec = {"x": round(xs, 2), "xmax": round(float(grp[:, 0].max()), 2),
                   "ymin": round(float(grp[:, 1].min()), 2), "ymax": round(float(grp[:, 1].max()), 2),
                   "zmin": round(float(grp[:, 2].min()), 2), "zmax": round(float(grp[:, 2].max()), 2),
                   "n": int(len(grp))}
            if rails is not None:
                dy = grp[:, 1] - rails["axis"](grp[:, 0])
                h = grp[:, 2] - rails["zr"](grp[:, 0])
                rec.update(dy_min=round(float(dy.min()), 2), dy_max=round(float(dy.max()), 2),
                           h_min=round(float(h.min()), 2), h_max=round(float(h.max()), 2),
                           n_env=int(np.count_nonzero((np.abs(dy) <= 1.05) & (h >= 0.12) & (h <= 3.0))))
            # link: nearest track whose last x is within 6 m (objects approach)
            best = None
            for t in tracks:
                if i - t[1] <= 30 and abs(t[0] - xs) < 6.0 and (best is None or abs(t[0] - xs) < abs(best[0] - xs)):
                    best = t
            if best is None:
                best = [xs, i, len(tracks)]
                tracks.append(best)
            best[0], best[1] = xs, i
            rec["track"] = best[2]
            objs.append(rec)
    res[f"{i:05d}"] = objs
json.dump({"frames": res, "bad_intensity_points": bad_int, "n_tracks": len(tracks)}, open(out, "w"))
print("frames", len(res), "tracks", len(tracks), "non-1 intensity tail points", bad_int)
