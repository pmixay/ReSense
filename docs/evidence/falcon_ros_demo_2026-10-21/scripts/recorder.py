#!/usr/bin/env python3
"""Passive recorder run inside the image: logs the arrival time (wall clock) of every /iv_points
message (header stamp only, raw CDR, no copy of the points) and of the node's output topics.
One JSON object per line: {"t": wall_s, "topic": ..., ...}.  Usage: recorder.py OUT.jsonl [INPUT_TOPIC]"""
import json, struct, sys, time, rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from std_msgs.msg import String, Float32, Bool

out = open(sys.argv[1], "w", buffering=1)
topic_in = sys.argv[2] if len(sys.argv) > 2 else "/iv_points"
rclpy.init()
node = rclpy.create_node("rsd_recorder")
qos = QoSProfile(depth=1000, history=HistoryPolicy.KEEP_LAST, reliability=ReliabilityPolicy.BEST_EFFORT,
                 durability=DurabilityPolicy.VOLATILE)
qos_out = QoSProfile(depth=1000, history=HistoryPolicy.KEEP_LAST, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.VOLATILE)
n_in = [0]

def raw_in(buf):
    t = time.time()
    b = bytes(buf)
    sec, nsec = struct.unpack_from("<iI", b, 4)   # CDR header (4 B), then Header.stamp
    n_in[0] += 1
    out.write(json.dumps({"t": t, "topic": "in", "stamp": sec + nsec * 1e-9, "n": n_in[0], "bytes": len(b)}) + "\n")

def on_status(m):
    t = time.time()
    try:
        j = json.loads(m.data)
    except Exception:
        out.write(json.dumps({"t": t, "topic": "status", "bad": m.data[:200]}) + "\n"); return
    fr = j.get("freshness") or j.get("result_freshness") or {}
    out.write(json.dumps({"t": t, "topic": "status", "stamp": j.get("stamp"), "decision": j.get("decision"),
                          "nearest_distance": j.get("nearest_distance"), "profile": j.get("sensor_profile"),
                          "node": j.get("node"), "freshness": fr, "raw_keys": sorted(j.keys())}) + "\n")

def simple(name):
    def cb(m):
        out.write(json.dumps({"t": time.time(), "topic": name, "v": m.data}) + "\n")
    return cb

node.create_subscription(__import__("sensor_msgs.msg", fromlist=["PointCloud2"]).PointCloud2, topic_in, raw_in, qos, raw=True)
node.create_subscription(String, "/resense/status", on_status, qos_out)
node.create_subscription(String, "/resense/decision", simple("decision"), qos_out)
for nm, ty in (("nearest_distance", Float32), ("clear_distance", Float32), ("obstacle_detected", Bool),
               ("warning", Bool), ("latency_ms", Float32), ("fps", Float32)):
    node.create_subscription(ty, "/resense/" + nm, simple(nm), qos_out)
open("/rec/ready", "w").write("ok")
rclpy.spin(node)
