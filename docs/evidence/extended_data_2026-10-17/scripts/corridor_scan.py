#!/usr/bin/env python3
"""Per-frame scan of the free space in front of the sensor (no detector involved).

    corridor_scan.py BAG.db3 --out OUT.json [--points OUT.npz] [--forward -y] [--left x] [--up z]
                     [--half-width 1.6] [--zmin -0.8] [--zmax 2.0] [--dmax 120]

The box: forward distance 3 m .. dmax, |lateral| <= half-width, zmin <= up <= zmax in the sensor
frame (axes given as signed sensor axes; the Pandar recordings are forward = -y, left = +x, up = +z,
the sensor ~1.1 m above the rail head, so zmin -0.8 is ~0.3 m above the rail). On a straight empty
tunnel the box holds almost nothing; inserted objects and dust show up as points in it. Points are
clustered (DBSCAN eps 0.6 m, min 3); each frame reports the count, the unclustered "scatter" count,
the clusters (size, centre, intensity) and the count per 10 m bin.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

import numpy as np
from sklearn.cluster import DBSCAN

sys.path.insert(0, os.environ.get("RESENSE_ROS", "/home/user/rs-1.1.0/ros2_ws/src/resense_ros"))
sys.path.insert(0, os.environ.get("RESENSE_REPO", "/home/user/rs-1.1.0"))

from resense_ros import fastcloud  # noqa: E402

DT = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}
AX = {"x": 0, "y": 1, "z": 2}


def axis(spec: str):
    s = -1.0 if spec.startswith("-") else 1.0
    return AX[spec.lstrip("+-")], s


def structured(msg):
    dt = np.dtype({"names": [f.name for f in msg.fields], "formats": ["<" + DT[f.datatype] for f in msg.fields],
                   "offsets": [f.offset for f in msg.fields], "itemsize": msg.point_step})
    n = msg.width * msg.height
    return np.frombuffer(bytes(msg.data[:n * msg.point_step]), dtype=dt, count=n)


def iter_rows(db3, limit=0):
    con = sqlite3.connect(f"file:{db3}?mode=ro", uri=True)
    n = 0
    try:
        for (data,) in con.execute("SELECT data FROM messages ORDER BY id"):
            yield data
            n += 1
            if limit and n >= limit:
                break
    except sqlite3.DatabaseError as e:
        print(f"stopped after {n} rows: {e}", file=sys.stderr)
    finally:
        con.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("db3")
    p.add_argument("--out", required=True)
    p.add_argument("--points", default="")
    p.add_argument("--forward", default="-y")
    p.add_argument("--left", default="x")
    p.add_argument("--up", default="z")
    p.add_argument("--half-width", type=float, default=1.6)
    p.add_argument("--zmin", type=float, default=-0.8)
    p.add_argument("--zmax", type=float, default=2.0)
    p.add_argument("--dmax", type=float, default=120.0)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--every", type=int, default=1)
    a = p.parse_args()
    (fi, fs), (li, ls), (ui, us) = axis(a.forward), axis(a.left), axis(a.up)
    recs, pts = [], []
    for i, data in enumerate(iter_rows(a.db3, a.limit)):
        if i % a.every:
            continue
        msg = fastcloud.parse_pointcloud2(data)
        arr = structured(msg)
        xyz = np.stack([arr["x"], arr["y"], arr["z"]], 1).astype(np.float32)
        d, lat, up = fs * xyz[:, fi], ls * xyz[:, li], us * xyz[:, ui]
        m = (d > 3) & (d < a.dmax) & (np.abs(lat) <= a.half_width) & (up >= a.zmin) & (up <= a.zmax)
        q = np.stack([d[m], lat[m], up[m]], 1)
        it = arr["intensity"][m].astype(np.float32) if "intensity" in arr.dtype.names else np.zeros(len(q))
        rec = {"i": i, "stamp": round(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9, 4), "n": int(m.sum()),
               "bins10": np.histogram(q[:, 0], bins=np.arange(0, a.dmax + 10, 10))[0].tolist() if len(q) else []}
        cl = []
        if len(q) >= 3:
            lab = DBSCAN(eps=0.6, min_samples=3).fit_predict(q)
            rec["scatter"] = int((lab == -1).sum())
            for c in sorted(set(lab) - {-1}):
                k = lab == c
                pc = q[k]
                cl.append({"n": int(k.sum()), "c": [round(float(v), 2) for v in pc.mean(0)],
                           "ext": [round(float(v), 2) for v in np.ptp(pc, 0)],
                           "inten_med": round(float(np.median(it[k])), 1),
                           "inten_eq1": round(float(np.mean(it[k] == 1)), 2)})
            cl.sort(key=lambda c: -c["n"])
        else:
            rec["scatter"] = int(len(q))
        rec["clusters"] = cl[:12]
        rec["n_clusters"] = len(cl)
        recs.append(rec)
        if a.points and len(q):
            pts.append(np.column_stack([np.full(len(q), i, np.float32), q, it]))
        if i % 50 == 0:
            print(i, rec["n"], rec["scatter"], len(cl), flush=True)
    json.dump(recs, open(a.out, "w"))
    if a.points and pts:
        np.savez_compressed(a.points, pts=np.concatenate(pts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
