#!/usr/bin/env python3
"""Find the organizers' inserted points in a synthetic bag without a reference recording.

    find_inserted.py BAG.db3 --out OUT.json [--points OUT.npz]

The inserted points of Set O and of the 16.10 synthetic bags carry intensity exactly 1 (checked on
synthetic_platform against its real reference: 99 % of the added points). Real returns with
intensity 1 exist (dark surfaces) but sit inside surfaces of mixed intensity. Per frame, in the
sensor-frame box forward 2.5..250 m (forward = -y), |x| <= 4 m, -1.5 <= z <= 4 m:

* the intensity-1 points are clustered (DBSCAN eps 0.5 m, min 4);
* a cluster is kept as "inserted" when, among all points within its bounding box grown by 0.15 m,
  at least 85 % have intensity 1 (a real dark patch is surrounded by other intensities);
* "free" intensity-1 points: those with no point of any intensity within 0.3 m other than other
  intensity-1 points, and more than 0.3 m above the lowest 2 % of z in their 5 m forward bin (not on
  the floor) -- a volume-filling dust cloud shows up here.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

import numpy as np
from scipy.spatial import cKDTree
from sklearn.cluster import DBSCAN

sys.path.insert(0, os.environ.get("RESENSE_ROS", "/home/user/rs-1.1.0/ros2_ws/src/resense_ros"))
sys.path.insert(0, os.environ.get("RESENSE_REPO", "/home/user/rs-1.1.0"))

from resense_ros import fastcloud  # noqa: E402

DT = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}


def structured(msg):
    dt = np.dtype({"names": [f.name for f in msg.fields], "formats": ["<" + DT[f.datatype] for f in msg.fields],
                   "offsets": [f.offset for f in msg.fields], "itemsize": msg.point_step})
    n = msg.width * msg.height
    return np.frombuffer(bytes(msg.data[:n * msg.point_step]), dtype=dt, count=n)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("db3")
    p.add_argument("--out", required=True)
    p.add_argument("--points", default="")
    a = p.parse_args()
    con = sqlite3.connect(f"file:{a.db3}?mode=ro", uri=True)
    recs, pts = [], []
    for i, (data,) in enumerate(con.execute("SELECT data FROM messages ORDER BY timestamp, id")):
        arr = structured(fastcloud.parse_pointcloud2(data))
        xyz = np.stack([arr["x"], arr["y"], arr["z"]], 1).astype(np.float32)
        it = arr["intensity"].astype(np.float32)
        fwd = -xyz[:, 1]
        box = (fwd > 2.5) & (fwd < 250) & (np.abs(xyz[:, 0]) <= 4) & (xyz[:, 2] >= -1.5) & (xyz[:, 2] <= 4)
        q, qi = xyz[box], it[box]
        one = qi == 1
        e = q[one]
        rec = {"i": i, "n_box": int(box.sum()), "n_int1": int(one.sum()), "objects": []}
        if len(e) >= 4:
            lab = DBSCAN(eps=0.5, min_samples=4).fit_predict(e)
            for c in sorted(set(lab) - {-1}):
                k = e[lab == c]
                lo, hi = k.min(0) - 0.15, k.max(0) + 0.15
                inb = np.all((q >= lo) & (q <= hi), axis=1)
                share = float(np.mean(qi[inb] == 1))
                if share < 0.85:
                    continue
                rec["objects"].append({"n": int(len(k)), "share": round(share, 2),
                                       "c": [round(float(v), 2) for v in k.mean(0)],
                                       "ext": [round(float(v), 2) for v in np.ptp(k, 0)],
                                       "fwd_min": round(float(-k[:, 1].max()), 2)})
                if a.points:
                    pts.append(np.column_stack([np.full(len(k), i, np.float32), k]))
            rec["objects"].sort(key=lambda o: o["fwd_min"])
            # free (volume) intensity-1 points
            tree = cKDTree(q)
            nb = tree.query_ball_point(e, r=0.3)
            iso = np.array([np.all(qi[j] == 1) for j in nb])
            ef = -e[:, 1]
            floor = np.full(len(e), np.nan, np.float32)
            bins = np.floor(-q[:, 1] / 5).astype(int)
            eb = np.floor(ef / 5).astype(int)
            for b in np.unique(eb):
                zb = q[bins == b, 2]
                if zb.size:
                    floor[eb == b] = np.percentile(zb, 2)
            free = iso & (e[:, 2] > floor + 0.3)
            rec["n_free"] = int(free.sum())
            if free.any():
                rec["free_fwd"] = [round(float(np.percentile(ef[free], v)), 1) for v in (5, 50, 95)]
                rec["free_x"] = [round(float(np.percentile(e[free, 0], v)), 2) for v in (5, 50, 95)]
                rec["free_z"] = [round(float(np.percentile(e[free, 2], v)), 2) for v in (5, 50, 95)]
        recs.append(rec)
        if i % 50 == 0:
            print(i, rec["n_int1"], len(rec["objects"]), rec.get("n_free"), flush=True)
    con.close()
    json.dump(recs, open(a.out, "w"))
    if a.points and pts:
        np.savez_compressed(a.points, pts=np.concatenate(pts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
