#!/usr/bin/env python3
"""Characterize the PointCloud2 messages of a rosbag2 sqlite3 file (or a readable prefix of one).

    characterize_bag.py BAG.db3 --out OUT.json [--npz-dir DIR --npz-frames 0,100,200] [--limit N]

Reads raw CDR rows straight from sqlite (rowid order; stops cleanly at the first unreadable page,
which makes it usable on a truncated copy), decodes with ``resense_ros.fastcloud.parse_pointcloud2``
plus a generic numpy structured view of the fields (any layout), and writes per-message stats:
stamps, frame_id, layout, point counts, no-return zeros, the block after the last zero (the
organizers' Set O insertion convention), intensity / ring / extra-field ranges, duplicate xyz
pairs, per-axis extents and percentiles, azimuth / elevation ranges in the sensor frame, ranges.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys

import numpy as np

sys.path.insert(0, os.environ.get("RESENSE_ROS", "/home/user/rs-1.1.0/ros2_ws/src/resense_ros"))
sys.path.insert(0, os.environ.get("RESENSE_REPO", "/home/user/rs-1.1.0"))

from resense_ros import fastcloud  # noqa: E402

DT = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}


def iter_rows(db3: str, limit: int = 0):
    con = sqlite3.connect(f"file:{db3}?mode=ro", uri=True)
    topics = {tid: (name, typ) for tid, name, typ in con.execute("SELECT id, name, type FROM topics")}
    n = 0
    try:
        for tid, ts, data in con.execute("SELECT topic_id, timestamp, data FROM messages ORDER BY id"):
            name, typ = topics[tid]
            yield name, typ, ts, data
            n += 1
            if limit and n >= limit:
                break
    except sqlite3.DatabaseError as e:
        print(f"stopped after {n} rows: {e}", file=sys.stderr)
    finally:
        con.close()


def structured(msg):
    names, formats, offsets = [], [], []
    for f in msg.fields:
        names.append(f.name)
        base = DT[f.datatype]
        formats.append((">" if msg.is_bigendian else "<") + base if f.count == 1 else (f"{f.count}" + base))
        offsets.append(f.offset)
    dt = np.dtype({"names": names, "formats": formats, "offsets": offsets, "itemsize": msg.point_step})
    n = msg.width * msg.height
    return np.frombuffer(bytes(msg.data[:n * msg.point_step]), dtype=dt, count=n)


def stats(a):
    a = np.asarray(a, dtype=np.float64)
    if a.size == 0:
        return None
    return {"min": float(a.min()), "p01": float(np.percentile(a, 1)), "p50": float(np.median(a)),
            "p99": float(np.percentile(a, 99)), "max": float(a.max())}


def frame_stats(msg, arr):
    x, y, z = (arr[k].astype(np.float64) for k in ("x", "y", "z"))
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    zero = finite & (x == 0) & (y == 0) & (z == 0)
    valid = finite & ~zero
    r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
    out = {"n_slots": int(arr.size), "n_nan": int((~finite).sum()), "n_zero": int(zero.sum()),
           "n_valid": int(valid.sum())}
    if zero.any():
        last = int(np.flatnonzero(zero)[-1])
        tail = np.arange(last + 1, arr.size)
        out["tail_after_last_zero"] = int(tail.size)
        if tail.size and "intensity" in arr.dtype.names:
            ti = arr["intensity"][tail].astype(np.float64)
            out["tail_intensity_unique"] = [float(v) for v in np.unique(ti)[:10]]
    vx, vy, vz, vr = x[valid], y[valid], z[valid], r[valid]
    out["x"], out["y"], out["z"], out["range"] = stats(vx), stats(vy), stats(vz), stats(vr)
    for t in (100, 150, 200, 250, 300):
        out[f"n_range_gt_{t}"] = int((vr > t).sum())
    for f in arr.dtype.names:
        if f in ("x", "y", "z"):
            continue
        v = arr[f][valid]
        if v.ndim > 1:
            continue
        s = stats(v)
        if s is not None:
            s["n_unique"] = int(np.unique(v).size)
        out[f"field_{f}"] = s
    xyz = np.stack([vx, vy, vz], 1).astype(np.float32)
    if xyz.shape[0]:
        u = np.unique(xyz.view(np.dtype((np.void, 12))))
        out["n_unique_xyz"] = int(u.size)
        same_next = np.all(xyz[1:] == xyz[:-1], axis=1)
        out["n_identical_consecutive"] = int(same_next.sum())
    out["hash_xyz"] = hashlib.sha1(np.ascontiguousarray(np.stack([x, y, z], 1).astype(np.float32))).hexdigest()[:16]
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("db3")
    p.add_argument("--out", required=True)
    p.add_argument("--npz-dir", default="")
    p.add_argument("--npz-frames", default="")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--every", type=int, default=1, help="full stats every N-th frame (stamps for all)")
    a = p.parse_args()
    want = {int(s) for s in a.npz_frames.split(",") if s}
    if a.npz_dir:
        os.makedirs(a.npz_dir, exist_ok=True)
    frames, layout, topics = [], None, {}
    for i, (topic, typ, ts, data) in enumerate(iter_rows(a.db3, a.limit)):
        topics.setdefault(topic, {"type": typ, "n": 0})
        topics[topic]["n"] += 1
        if typ != "sensor_msgs/msg/PointCloud2":
            continue
        msg = fastcloud.parse_pointcloud2(data)
        rec = {"i": i, "bag_t": ts / 1e9, "stamp": msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
               "frame_id": msg.header.frame_id, "topic": topic, "bytes": len(data)}
        lay = {"fields": [[f.name, f.offset, f.datatype, f.count] for f in msg.fields], "point_step": msg.point_step,
               "row_step": msg.row_step, "height": msg.height, "is_bigendian": msg.is_bigendian,
               "is_dense": msg.is_dense}
        if layout is None:
            layout = dict(lay, width_first=msg.width)
        elif lay["fields"] != layout["fields"] or lay["point_step"] != layout["point_step"]:
            rec["layout_changed"] = lay
        rec["width"], rec["height"] = msg.width, msg.height
        arr = structured(msg)
        if i % a.every == 0 or i in want:
            rec.update(frame_stats(msg, arr))
        if i in want and a.npz_dir:
            np.savez_compressed(os.path.join(a.npz_dir, f"f_{i:05d}.npz"), raw=arr)
        frames.append(rec)
        if i % 50 == 0:
            print(i, rec.get("n_valid"), flush=True)
    st = np.array([f["stamp"] for f in frames])
    bt = np.array([f["bag_t"] for f in frames])
    summ = {"db3": a.db3, "topics": topics, "layout": layout, "n_frames": len(frames)}
    for name, t in (("stamp", st), ("bag_t", bt)):
        if t.size > 1:
            d = np.diff(t)
            summ[f"{name}_interval"] = {"median": float(np.median(d)), "min": float(d.min()), "max": float(d.max()),
                                        "n_gt_0.15": int((d > 0.15).sum()), "n_nonpos": int((d <= 0).sum()),
                                        "first": float(t[0]), "last": float(t[-1])}
    json.dump({"summary": summ, "frames": frames}, open(a.out, "w"), indent=0)
    print(json.dumps(summ, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
