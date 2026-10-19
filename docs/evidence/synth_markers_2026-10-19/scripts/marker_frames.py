"""Look at the cloud inside the organizers' marker boxes: points per box and a top / side view per frame.

For the chosen frames of one marked bag (rosbag2 sqlite, Pandar axes: forward = -y, left = +x, up = +z) it decodes the
PointCloud2 (finite x, y, z only), counts the points inside each active LINE_LIST box (box bounds from read_markers.py,
grown by --margin) and within 1 m of the box centre, prints one line per box, and writes <out>_<frame>.png with the
points around the boxes (top view forward x lateral, side view forward x up) and the boxes drawn on top.

    python marker_frames.py <bag dir> <markers.jsonl> <out prefix> --frames 21,27,35,178,300 [--margin 0.05]
        [--window 0,12] [--lat 6] [--dets <run.jsonl>]   (detections drawn in the run's vehicle frame, which is the
        mount-calibrated sensor frame: close to, not exactly, the forward/lateral of the boxes)
"""
import argparse
import glob
import json
import os
import sqlite3

import matplotlib
import numpy as np
from rosbags.typesys import Stores, get_typestore

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TS = get_typestore(Stores.ROS2_HUMBLE)
DT = {1: "i1", 2: "u1", 3: "i2", 4: "u2", 5: "i4", 6: "u4", 7: "f4", 8: "f8"}


def clouds(db3, want):
    con = sqlite3.connect(f"file:{db3}?mode=ro", uri=True)
    tids = [tid for tid, typ in con.execute("SELECT id, type FROM topics") if typ == "sensor_msgs/msg/PointCloud2"]
    q = "SELECT data FROM messages WHERE topic_id IN (%s) ORDER BY timestamp, id" % ",".join(map(str, tids))
    for i, (data,) in enumerate(con.execute(q)):
        if i in want:
            m = TS.deserialize_cdr(data, "sensor_msgs/msg/PointCloud2")
            dt = np.dtype({"names": [f.name for f in m.fields], "formats": [DT[f.datatype] for f in m.fields],
                           "offsets": [f.offset for f in m.fields], "itemsize": m.point_step})
            a = np.frombuffer(bytes(m.data), dtype=dt.newbyteorder(">" if m.is_bigendian else "<"))
            xyz = np.stack([a["x"], a["y"], a["z"]], 1).astype(float)
            yield i, xyz[np.isfinite(xyz).all(1)]
        if i >= max(want):
            break


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bag")
    ap.add_argument("markers")
    ap.add_argument("out")
    ap.add_argument("--frames", required=True)
    ap.add_argument("--margin", type=float, default=0.05)
    ap.add_argument("--window", help="forward range of the plot, 'f0,f1' (m); default: around the boxes")
    ap.add_argument("--lat", type=float, default=6.0, help="half-width of the plot (m)")
    ap.add_argument("--dets", help="a judge_runner.py run (.jsonl): draw its detections of the frame in blue")
    a = ap.parse_args()
    want = {int(f) for f in a.frames.split(",")}
    rows = {r["i"]: r for r in (json.loads(line) for line in open(a.markers))}
    run = {r["i"]: r for r in (json.loads(line) for line in open(a.dets))} if a.dets else {}
    db3 = sorted(glob.glob(os.path.join(a.bag, "*.db3")))[0]
    report = []
    for i, xyz in clouds(db3, want):
        boxes = [m for m in rows[i]["markers"] if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]]
        fwd, lat, up = -xyz[:, 1], xyz[:, 0], xyz[:, 2]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7))
        for m in boxes:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            c = (lo + hi) / 2
            inside = ((xyz >= lo - a.margin) & (xyz <= hi + a.margin)).all(1)
            near = np.linalg.norm(xyz - c, axis=1) <= 1.0
            rec = {"frame": i, "id": m["id"], "fwd": round(-c[1], 2), "lat": round(c[0], 2), "up": round(c[2], 2),
                   "size_fwd_lat_up": [round(hi[1] - lo[1], 2), round(hi[0] - lo[0], 2), round(hi[2] - lo[2], 2)],
                   "pts_in_box": int(inside.sum()), "pts_within_1m": int(near.sum())}
            report.append(rec)
            print(json.dumps(rec))
            for ax, (u0, u1, v0, v1) in ((ax1, (-hi[1], -lo[1], lo[0], hi[0])), (ax2, (-hi[1], -lo[1], lo[2], hi[2]))):
                ax.add_patch(plt.Rectangle((u0, v0), u1 - u0, v1 - v0, fill=False, ec="red", lw=1))
                ax.annotate(str(m["id"]), (u1, v1), fontsize=7, color="red")
        for d in run.get(i, {}).get("dets", []):
            c, sz = np.array(d["c"]), np.array(d["size"])
            for ax, (u, v) in ((ax1, (0, 1)), (ax2, (0, 2))):
                ax.add_patch(plt.Rectangle((c[u] - sz[u] / 2, c[v] - sz[v] / 2), max(sz[u], 0.05), max(sz[v], 0.05),
                                           fill=False, ec="blue", lw=1.2))
            ax1.annotate(f"STOP det {d['d']} m" if run[i]["decision"] == "STOP" else f"det {d['d']} m",
                         (c[0], c[1] + sz[1] / 2), fontsize=7, color="blue")
        if a.window:
            f0, f1 = map(float, a.window.split(","))
        elif boxes:
            cs = np.array([(-(np.array(m["pts_min"])[1] + np.array(m["pts_max"])[1]) / 2) for m in boxes])
            f0, f1 = cs.min() - 6, cs.max() + 6
        else:
            f0, f1 = 0, 60
        sel = (fwd > f0) & (fwd < f1) & (np.abs(lat) < a.lat) & (up > -3) & (up < 4)
        for ax in (ax1, ax2):
            ax.set_xlim(f0, f1)
        ax1.scatter(fwd[sel], lat[sel], s=0.5, c="k")
        ax2.scatter(fwd[sel], up[sel], s=0.5, c="k")
        ax1.set_ylabel("lateral (m, left +)")
        ax2.set_ylabel("up (m, sensor)")
        ax2.set_xlabel("forward (m)")
        ax1.set_title(f"{os.path.basename(a.bag.rstrip('/'))} frame {i}: {len(boxes)} marker boxes (red)"
                      + (f", {run[i]['decision']}, detections (blue)" if i in run else ""))
        fig.tight_layout()
        fig.savefig(f"{a.out}_{i:04d}.png", dpi=90)
        plt.close(fig)
    json.dump(report, open(a.out + "_boxes.json", "w"), indent=1)


if __name__ == "__main__":
    main()
