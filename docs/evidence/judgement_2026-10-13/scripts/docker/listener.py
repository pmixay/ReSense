#!/usr/bin/env python3
"""Runs inside the ReSense image (rclpy): records every /resense/status JSON (decision, distance, node
latency, freshness) and every /resense/decision with the wall-clock arrival time, until SIGINT/SIGTERM or
--seconds. Writes <out>.jsonl."""
import argparse
import json
import signal
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--seconds", type=float, default=600)
a = ap.parse_args()


class L(Node):
    def __init__(self):
        super().__init__("jury_listener")
        self.f = open(a.out, "w")
        self.create_subscription(String, "/resense/status", self.on_status, 50)
        self.create_subscription(String, "/resense/decision", self.on_dec, 50)
        self.create_subscription(Float32, "/resense/latency_ms", self.on_lat, 50)

    def on_status(self, m):
        try:
            s = json.loads(m.data)
        except Exception:
            return
        node = s.get("node", {}) or {}
        fr = s.get("freshness", {}) or {}
        self.f.write(json.dumps({"t": time.time(), "k": "status", "decision": s.get("decision"),
                                 "nearest": s.get("nearest_distance"), "stamp": s.get("stamp"),
                                 "lat_ms": node.get("latency_ms"), "decode_ms": node.get("decode_ms"),
                                 "detect_ms": node.get("detect_ms"), "frames": node.get("frames"),
                                 "dropped": node.get("dropped_frames"), "skipped": node.get("catchup_skipped"),
                                 "cpu": node.get("cpu_cores"), "rss": node.get("rss_peak_mb"), "fps": node.get("fps"),
                                 "topic": node.get("input_topic"), "fresh": fr.get("valid"), "reason": fr.get("reason"),
                                 "age": fr.get("source_age_s"), "stop_held": s.get("stop_held"),
                                 "snapshot": s.get("snapshot_kind"),
                                 "dets": [(d.get("distance"), d.get("lateral")) for d in s.get("detections", [])]}) + "\n")

    def on_dec(self, m):
        self.f.write(json.dumps({"t": time.time(), "k": "decision", "v": m.data}) + "\n")

    def on_lat(self, m):
        self.f.write(json.dumps({"t": time.time(), "k": "latency", "v": m.data}) + "\n")


rclpy.init()
n = L()
stop = {"x": False}
signal.signal(signal.SIGTERM, lambda *_: stop.update(x=True))
signal.signal(signal.SIGINT, lambda *_: stop.update(x=True))
t0 = time.time()
while not stop["x"] and time.time() - t0 < a.seconds:
    rclpy.spin_once(n, timeout_sec=0.1)
n.f.close()
sys.exit(0)
