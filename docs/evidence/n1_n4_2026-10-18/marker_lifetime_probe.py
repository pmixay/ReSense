#!/usr/bin/env python3
"""Publish the actual node's gauge markers, then stop publishing without DELETE/watchdog."""
import json
from pathlib import Path
import subprocess
import time
from types import SimpleNamespace

import numpy as np
import rclpy
from std_msgs.msg import Header
from visualization_msgs.msg import MarkerArray

from resense.config import DetectorConfig
from resense.frame import axis_matrix
from resense.track import TrackModel
from resense_ros.detector_node import DetectorNode
from resense_ros.gauge_display import GaugeDisplay

out = Path('/out')
rviz = subprocess.Popen(['rviz2', '-d', '/opt/resense/ros2_ws/src/resense_ros/rviz/resense.rviz'])
rclpy.init()
node = rclpy.create_node('gauge_expiry_probe')
publisher = node.create_publisher(MarkerArray, '/resense/markers', 10)
cfg = DetectorConfig()
display = GaugeDisplay()
track = TrackModel(np.array([0., 0., -1.6]), (3., 100.), 0., 0., .0002, axis_valid=120.)
for index in range(30):
    display.update(track, index*.1, {'level': 'ok', 'monitored_range': 120.})
markers = DetectorNode.gauge_markers(SimpleNamespace(cfg=cfg, gauge_display=display),
                                   Header(frame_id='resense_lidar'), axis_matrix(cfg.sensor).T)
assert all(marker.lifetime.nanosec == 500_000_000 for marker in markers)
def phase(name):
    (out/'phase.json').write_text(json.dumps({'phase': name, 'wall': time.time()}))
try:
    deadline = time.monotonic()+20
    while not publisher.get_subscription_count():
        if time.monotonic() >= deadline:
            raise RuntimeError('RViz marker subscription absent')
        rclpy.spin_once(node, timeout_sec=.05)
    phase('publishing')
    until = time.monotonic()+4
    while time.monotonic()<until:
        publisher.publish(MarkerArray(markers=markers))
        rclpy.spin_once(node, timeout_sec=.1)
    phase('silent_no_delete')
    until = time.monotonic()+3
    while time.monotonic()<until:
        rclpy.spin_once(node, timeout_sec=.1)
    phase('complete')
finally:
    node.destroy_node()
    rclpy.shutdown()
    rviz.terminate()
    rviz.wait(timeout=10)
