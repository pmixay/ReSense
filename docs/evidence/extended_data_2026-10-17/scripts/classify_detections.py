#!/usr/bin/env python3
"""Tag each detector detection / warning of a judge_runner run by the intensity of the raw points
under it: the organizers' inserted points carry intensity exactly 1 (Set O and the 16.10 synthetic
bags), so a box whose points are almost all intensity 1 is an inserted object, one whose points are
not is background (a false alarm on an empty scene, or the dust if its points carry other values).

    classify_detections.py BAG.db3 RUN.jsonl --out OUT.json

The detection centre ``c`` is (forward, left, up) in the vehicle frame; with the identity mount of
these recordings it is the sensor point (x, y, z) = (c[1], -c[0], c[2]) (sensor forward = -y,
left = +x). Points within the detection box grown by 0.2 m are counted.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

import numpy as np

sys.path.insert(0, os.environ.get("RESENSE_ROS", "/home/user/rs-1.1.0/ros2_ws/src/resense_ros"))
sys.path.insert(0, os.environ.get("RESENSE_REPO", "/home/user/rs-1.1.0"))

from resense_ros import fastcloud  # noqa: E402

DT = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}


def structured(msg):
    dt = np.dtype({"names": [f.name for f in msg.fields], "formats": ["<" + DT[f.datatype] for f in msg.fields],
                   "offsets": [f.offset for f in msg.fields], "itemsize": msg.point_step})
    n = msg.width * msg.height
    return np.frombuffer(bytes(msg.data[:n * msg.point_step]), dtype=dt, count=n)


def tag(xyz, inten, d):
    c = np.array([d["c"][1], -d["c"][0], d["c"][2]])
    s = np.array(d["size"], dtype=float)
    half = np.array([s[1], s[0], s[2]]) / 2 + 0.2      # size is (forward, left, up)
    m = np.all(np.abs(xyz - c) <= half, axis=1)
    n = int(m.sum())
    return {"d": d["d"], "lat": d["lat"], "n_pts": n,
            "int1": round(float(np.mean(inten[m] == 1)), 2) if n else None,
            "int_med": round(float(np.median(inten[m])), 1) if n else None}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("db3")
    p.add_argument("jsonl")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    recs = [json.loads(line) for line in open(a.jsonl)]
    con = sqlite3.connect(f"file:{a.db3}?mode=ro", uri=True)
    out = []
    for r, (data,) in zip(recs, con.execute("SELECT data FROM messages ORDER BY timestamp, id")):
        if not r["dets"] and not r["warns"]:
            continue
        arr = structured(fastcloud.parse_pointcloud2(data))
        xyz = np.stack([arr["x"], arr["y"], arr["z"]], 1).astype(np.float64)
        inten = arr["intensity"].astype(np.float32)
        out.append({"i": r["i"], "decision": r["decision"], "dets": [tag(xyz, inten, d) for d in r["dets"]],
                    "warns": [tag(xyz, inten, d) for d in r["warns"]]})
    con.close()
    json.dump(out, open(a.out, "w"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
