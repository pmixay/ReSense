#!/usr/bin/env python3
"""Jury runner: replays rosbag2 sqlite3 files through the sealed detector exactly as the ROS node
does it (resense_ros.fastcloud decode of the raw CDR bytes, sensor->vehicle axis matrix of the
config, Frame with the header stamp, ring=None when the cloud has no ring field, the node's
continuity rules: >1 s header-stamp hole -> detector.reset(), >30 s or backwards -> new Detector),
and applies the node's decision rule (STOP > FAULT(health error) > CAUTION(warning or health
decision_level warn) > GO).

Freshness / catch-up of the live node are NOT modelled here (every frame is processed, as the node
does when it keeps up); the Docker run measures those separately.

Usage:
  judge_runner.py --bag <dir-or-db3> [--bag ...] --out <prefix>   (several --bag = one detector, in order)
Writes <prefix>.jsonl (one record per frame) and <prefix>.csv (flat summary).
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402 (thread env vars must be set before numpy loads)
import csv  # noqa: E402 (thread env vars must be set before numpy loads)
import glob  # noqa: E402 (thread env vars must be set before numpy loads)
import json  # noqa: E402 (thread env vars must be set before numpy loads)
import resource  # noqa: E402 (thread env vars must be set before numpy loads)
import sqlite3  # noqa: E402 (thread env vars must be set before numpy loads)
import sys  # noqa: E402 (thread env vars must be set before numpy loads)
import time  # noqa: E402 (thread env vars must be set before numpy loads)

REPO = os.environ.get("RESENSE_REPO", "/home/user/ReSense")
sys.path.insert(0, os.path.join(REPO, "ros2_ws/src/resense_ros"))

import numpy as np  # noqa: E402

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

CONFIG = os.path.join(REPO, "configs/default.yaml")


def node_decision(res) -> str:
    h = getattr(res, "health", {}) or {}
    level = h.get("level", "ok")
    if res.obstacle:
        return "STOP"
    if level == "error":
        return "FAULT"
    if res.warning or h.get("decision_level", level) == "warn":
        return "CAUTION"
    return "GO"


def db3_files(path: str):
    if os.path.isdir(path):
        files = glob.glob(os.path.join(path, "*.db3"))
        import re
        files.sort(key=lambda f: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", os.path.basename(f))])
        return files
    return [path]


def iter_raw(db3: str):
    """(bag_time_ns, topic, raw_cdr) for every PointCloud2 message, in timestamp order."""
    con = sqlite3.connect(f"file:{db3}?mode=ro", uri=True)
    try:
        topics = {tid: name for tid, name, typ in con.execute("SELECT id, name, type FROM topics")
                  if typ == "sensor_msgs/msg/PointCloud2"}
        if not topics:
            return
        q = ("SELECT topic_id, timestamp, data FROM messages WHERE topic_id IN (%s) ORDER BY timestamp, id"
             % ",".join(str(t) for t in topics))
        for tid, ts, data in con.execute(q):
            yield ts, topics[tid], data
    finally:
        con.close()


class NodeReplica:
    def __init__(self, config: str = CONFIG, overrides: dict | None = None):
        self.cfg = DetectorConfig.from_yaml(config)
        self.cfg.calibration.enabled = True          # node default auto_calibrate:=true
        for k, v in (overrides or {}).items():       # "section.key": value (robustness probes only)
            sec, key = k.split(".", 1)
            setattr(getattr(self.cfg, sec), key, v)
        self.detector = Detector(self.cfg)
        self.R_vs = axis_matrix(self.cfg.sensor).astype(np.float32)
        self.active = None       # (topic, frame_id)
        self.last_stamp = None
        self.resets = []

    def continuity(self, topic, frame_id, stamp, idx):
        if self.active is None:
            self.active = (topic, frame_id)
        elif (topic, frame_id) != self.active:
            self.active = (topic, frame_id)
            self.detector = Detector(self.cfg)
            self.resets.append((idx, "new_input"))
            self.last_stamp = None
        if self.last_stamp is not None:
            gap = stamp - self.last_stamp
            if gap < -0.5 or gap > 30.0:
                self.detector = Detector(self.cfg)
                self.resets.append((idx, f"new_recording gap {gap:+.2f}"))
            elif gap > 1.0:
                self.detector.reset()
                self.resets.append((idx, f"hole_reset gap {gap:+.2f}"))
        self.last_stamp = stamp

    def process_raw(self, raw: bytes, topic: str, idx: int, transform=None):
        t0 = time.perf_counter()
        msg = fastcloud.parse_pointcloud2(raw)
        stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.continuity(topic, msg.header.frame_id, stamp, idx)
        xyz_s, inten, ring, n_raw, n_near = fastcloud.decode(fastcloud.packed(msg), self.cfg.sensor.min_range,
                                                             self.cfg.sensor.max_range)
        if transform is not None:                    # robustness probes: modify the sensor-frame cloud
            xyz_s, inten, ring = transform(xyz_s, inten, ring, idx)
        xyz_v = xyz_s @ self.R_vs.T
        frame = Frame(xyz=xyz_v, intensity=inten, ring=ring if fastcloud.has_field(msg, "ring") else None,
                      stamp=stamp, frame_id=msg.header.frame_id, meta={"n_raw": n_raw, "n_near": n_near})
        t1 = time.perf_counter()
        res = self.detector.process(frame, ego_speed=None)
        t2 = time.perf_counter()
        return msg, stamp, res, (t1 - t0) * 1e3, (t2 - t1) * 1e3


def det_dict(d):
    return {"d": round(float(d.distance), 2), "lat": round(float(d.lateral), 2),
            "size": [round(float(v), 2) for v in d.size], "n": int(d.n_points), "zone": d.zone,
            "kind": d.kind, "reason": d.reason, "conf": round(float(d.confidence), 3), "age": int(d.age),
            "hmin": round(float(d.height_min), 2), "c": [round(float(v), 2) for v in d.center]}


def record(idx, bag_t, stamp, res, dec_ms, det_ms, frame_id, topic):
    h = res.health or {}
    tr = res.track
    return {
        "i": idx, "bag_t": round(bag_t, 4), "stamp": round(stamp, 4), "frame_id": frame_id, "topic": topic,
        "decision": node_decision(res), "obstacle": bool(res.obstacle), "warning": bool(res.warning),
        "nearest": None if res.nearest_distance is None else round(float(res.nearest_distance), 2),
        "clear": round(float(res.clear_distance), 1), "level": h.get("level"),
        "dlevel": h.get("decision_level", h.get("level")), "msgs": h.get("messages", []),
        "monitored": h.get("monitored_range"), "rail_lock": h.get("rail_lock"),
        "dets": [det_dict(d) for d in res.detections], "warns": [det_dict(d) for d in res.warnings],
        "n_points": int(res.n_points), "decode_ms": round(dec_ms, 2), "detect_ms": round(det_ms, 2),
        "total_ms": round(res.timing_ms.get("total", 0.0), 2),
        "track_center": round(float(getattr(tr, "center", 0.0)), 3),
        "curv": float(getattr(tr, "curvature", 0.0)),
        "mount": (res.mount or {}).get("status"), "mount_h": (res.mount or {}).get("height"),
        "ego": None if res.ego_speed_estimate is None else round(float(res.ego_speed_estimate), 2),
    }


CSV_COLS = ["i", "bag_t", "stamp", "decision", "obstacle", "warning", "nearest", "clear", "level", "dlevel",
            "n_dets", "n_warns", "det_d", "det_lat", "det_kind", "warn_d", "warn_lat", "n_points", "decode_ms",
            "detect_ms", "track_center", "mount_h", "ego"]


def csv_row(r):
    return [r["i"], r["bag_t"], r["stamp"], r["decision"], int(r["obstacle"]), int(r["warning"]), r["nearest"],
            r["clear"], r["level"], r["dlevel"], len(r["dets"]), len(r["warns"]),
            ";".join(str(d["d"]) for d in r["dets"]), ";".join(str(d["lat"]) for d in r["dets"]),
            ";".join(d["kind"] or "c" for d in r["dets"]),
            ";".join(str(d["d"]) for d in r["warns"]), ";".join(str(d["lat"]) for d in r["warns"]),
            r["n_points"], r["decode_ms"], r["detect_ms"], r["track_center"], r["mount_h"], r["ego"]]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bag", action="append", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    rep = NodeReplica()
    t_start, cpu0 = time.time(), time.process_time()
    n = 0
    with open(a.out + ".jsonl", "w") as fj, open(a.out + ".csv", "w", newline="") as fc:
        w = csv.writer(fc)
        w.writerow(CSV_COLS)
        for bag in a.bag:
            for db3 in db3_files(bag):
                for ts, topic, raw in iter_raw(db3):
                    msg, stamp, res, dec_ms, det_ms = rep.process_raw(raw, topic, n)
                    r = record(n, ts / 1e9, stamp, res, dec_ms, det_ms, msg.header.frame_id, topic)
                    fj.write(json.dumps(r) + "\n")
                    w.writerow(csv_row(r))
                    n += 1
                    if a.limit and n >= a.limit:
                        break
    wall, cpu = time.time() - t_start, time.process_time() - cpu0
    meta = {"frames": n, "wall_s": round(wall, 1), "cpu_s": round(cpu, 1),
            "rss_peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
            "resets": rep.resets, "bags": a.bag}
    json.dump(meta, open(a.out + ".meta.json", "w"), indent=1)
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
