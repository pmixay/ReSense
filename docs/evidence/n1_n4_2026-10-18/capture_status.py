#!/usr/bin/env python3
"""Write actual ROS status unchanged, with observer receipt time."""
import json
from pathlib import Path
import sys
import time

import rclpy
from std_msgs.msg import String

path = Path(sys.argv[1])
rclpy.init()
node = rclpy.create_node("n1_comparison_status_observer")
with path.open("w") as stream:
    def received(message):
        row = json.loads(message.data)
        row["_received_mono"] = time.monotonic()
        stream.write(json.dumps(row) + "\n")
        stream.flush()

    node.create_subscription(String, "/resense/status", received, 1000)
    path.with_suffix(".ready").write_text("ready\n")
    rclpy.spin(node)
