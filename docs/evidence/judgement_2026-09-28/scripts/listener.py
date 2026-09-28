"""Judge's listener for the jury chain: logs the arrival of every input cloud (raw bytes, keyed by its
header stamp, not deserialised), /resense/decision, /resense/nearest_distance and /resense/status,
each with the wall-clock receive time. Runs inside the resense image (rclpy).

    python3 listener.py /out/listen.jsonl          # NO_CLOUD=1: outputs only, no cloud subscription
"""
import json
import os
import struct
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Float32, String

INPUTS = ("/sensing/lidar/hesai128/pointcloud", "/lidar_points")


class Listener(Node):
    def __init__(self, out):
        super().__init__("judge_listener")
        self.out = out
        best_effort = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                                 history=HistoryPolicy.KEEP_LAST)
        reliable = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE, history=HistoryPolicy.KEEP_LAST)
        for topic in (() if os.environ.get("NO_CLOUD") else INPUTS):
            self.create_subscription(PointCloud2, topic, lambda m, t=topic: self.cloud(m, t), best_effort, raw=True)
        self.create_subscription(String, "/resense/decision", lambda m: self.write("decision", m.data), reliable)
        self.create_subscription(Float32, "/resense/nearest_distance", lambda m: self.write("nearest", m.data),
                                 reliable)
        self.create_subscription(String, "/resense/status", lambda m: self.write("status", m.data), reliable)

    def cloud(self, raw, topic):
        t = time.time()
        sec, nsec = struct.unpack_from("<iI", raw, 4)      # CDR header, then header.stamp
        self.out.write(json.dumps({"t": t, "k": "cloud", "topic": topic, "stamp": sec + nsec * 1e-9,
                                   "bytes": len(raw)}) + "\n")

    def write(self, kind, value):
        self.out.write(json.dumps({"t": time.time(), "k": kind, "v": value}) + "\n")


def main():
    out = open(sys.argv[1], "w", buffering=1)
    rclpy.init()
    node = Listener(out)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, Exception):
        pass


if __name__ == "__main__":
    main()
