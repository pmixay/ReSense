#!/usr/bin/env python3
"""Find the points a synthetic bag adds to (and removes from) a real recording it was built on.

    diff_vs_reference.py SYNTH.db3 REF_DECODED_DIR --out OUT.json [--points OUT.npz]

REF_DECODED_DIR is a frame cache (``f_NNNNN.npz`` with ``xyz`` float32 sensor frame, points with
2.5 m <= range <= max range of the frame; ``meta.json`` with per-frame header stamps). Each synthetic
message is matched to the reference frame with the same header stamp (|dt| < 1 ms). Its valid points
inside the reference frame's range bounds are compared exactly (float32 xyz) with the reference: the
"new" points are inserted, the "gone" ones were removed (hidden behind an insertion or replaced).
New points are clustered (DBSCAN, eps 0.6 m, min 3) and each cluster is reported with its size,
centre, intensity and ring values.
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


def structured(msg):
    dt = np.dtype({"names": [f.name for f in msg.fields], "formats": ["<" + DT[f.datatype] for f in msg.fields],
                   "offsets": [f.offset for f in msg.fields], "itemsize": msg.point_step})
    n = msg.width * msg.height
    return np.frombuffer(bytes(msg.data[:n * msg.point_step]), dtype=dt, count=n)


def key(a):
    return np.ascontiguousarray(a.astype(np.float32)).view(np.dtype((np.void, 12))).ravel()


def clusters(xyz, inten, ring):
    if len(xyz) < 3:
        return []
    lab = DBSCAN(eps=0.6, min_samples=3).fit_predict(xyz)
    out = []
    for c in sorted(set(lab) - {-1}):
        m = lab == c
        p = xyz[m]
        r = np.linalg.norm(p, axis=1)
        out.append({"n": int(m.sum()), "c": [round(float(v), 2) for v in p.mean(0)],
                    "lo": [round(float(v), 2) for v in p.min(0)], "hi": [round(float(v), 2) for v in p.max(0)],
                    "range_min": round(float(r.min()), 2),
                    "inten": [round(float(v), 1) for v in np.unique(inten[m])[:8]],
                    "rings": [int(ring[m].min()), int(ring[m].max())] if ring is not None else None})
    out.sort(key=lambda c: -c["n"])
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("db3")
    p.add_argument("ref")
    p.add_argument("--out", required=True)
    p.add_argument("--points", default="")
    a = p.parse_args()
    meta = json.load(open(os.path.join(a.ref, "meta.json")))
    rst = np.array([m["stamp"] for m in meta])
    con = sqlite3.connect(f"file:{a.db3}?mode=ro", uri=True)
    recs, pts = [], []
    for i, (data,) in enumerate(con.execute("SELECT data FROM messages ORDER BY timestamp, id")):
        msg = fastcloud.parse_pointcloud2(data)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        arr = structured(msg)
        xyz = np.stack([arr["x"], arr["y"], arr["z"]], 1)
        inten = arr["intensity"].astype(np.float32)
        ring = arr["ring"] if "ring" in arr.dtype.names else None
        rec = {"i": i, "stamp": round(stamp, 4)}
        j = int(np.argmin(np.abs(rst - stamp)))
        if abs(rst[j] - stamp) > 1e-3:
            rec["ref"] = None
            recs.append(rec)
            continue
        ref = np.load(os.path.join(a.ref, f"f_{j:05d}.npz"))["xyz"]
        rr = np.linalg.norm(ref, axis=1)
        r = np.linalg.norm(xyz, axis=1)
        sel = (r >= rr.min() - 1e-3) & (r <= rr.max() + 1e-3) & np.isfinite(r)
        ks, kr = key(xyz), key(ref)
        new = sel & ~np.isin(ks, kr)
        gone = ~np.isin(kr, ks[sel])
        rec.update({"ref": j, "n_new": int(new.sum()), "n_gone": int(gone.sum()),
                    "clusters": clusters(xyz[new], inten[new], None if ring is None else ring[new]),
                    "n_new_noise": 0})
        rec["n_new_noise"] = rec["n_new"] - sum(c["n"] for c in rec["clusters"])
        if new.any():
            g = np.linalg.norm(ref[gone], axis=1) if gone.any() else np.zeros(0)
            rec["gone_range"] = [round(float(g.min()), 1), round(float(g.max()), 1)] if g.size else None
            if a.points:
                pts.append(np.column_stack([np.full(new.sum(), i, np.float32), xyz[new], inten[new]]))
        recs.append(rec)
        if i % 50 == 0:
            print(i, j, rec["n_new"], rec["n_gone"], len(rec["clusters"]), flush=True)
    con.close()
    json.dump(recs, open(a.out, "w"))
    if a.points and pts:
        np.savez_compressed(a.points, pts=np.concatenate(pts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
