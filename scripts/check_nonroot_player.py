#!/usr/bin/env python3
"""Runtime-only E2 check: uid 1000, unchanged HOME, launch and a tiny rosbag2 player.

docker run --rm --network none --user 1000:1000 -w / IMAGE \
  python3 /opt/resense/scripts/check_nonroot_player.py
Uses ROS's own writer/serialization, not Open3D or the optional research dependencies.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile


def main() -> None:
    import rosbag2_py
    from rclpy.serialization import serialize_message
    from std_msgs.msg import String

    assert os.getuid() == 1000 and os.getgid() == 1000
    assert os.environ['ROS_HOME'] == '/tmp/.ros'
    assert os.environ['ROS_LOG_DIR'] == '/tmp/.ros/log'
    print(json.dumps({k: os.environ.get(k) for k in ('HOME', 'ROS_HOME', 'ROS_LOG_DIR')}, indent=2), flush=True)
    with tempfile.TemporaryDirectory(prefix='resense-e2-') as tmp:
        bag = Path(tmp) / 'bag'
        writer = rosbag2_py.SequentialWriter()
        writer.open(rosbag2_py.StorageOptions(uri=str(bag), storage_id='sqlite3'),
                    rosbag2_py.ConverterOptions('', ''))
        writer.create_topic(rosbag2_py.TopicMetadata(
            name='/resense_e2_probe', type='std_msgs/msg/String', serialization_format='cdr'))
        for i in range(3):
            writer.write('/resense_e2_probe', serialize_message(String(data=f'e2-{i}')),
                         1_000_000_000 + i * 50_000_000)
        del writer
        for command in (
            ['ros2', 'launch', 'resense_ros', 'detector.launch.py', '--show-args'],
            ['ros2', 'bag', 'play', str(bag), '--read-ahead-queue-size', '10', '--disable-keyboard-controls'],
        ):
            subprocess.run(command, check=True, timeout=60)
    logs = Path(os.environ['ROS_LOG_DIR'])
    assert logs.is_dir() and os.access(logs, os.W_OK), logs
    print('PASS: uid 1000 launch resolution and synthetic bag playback, no HOME override', flush=True)


if __name__ == '__main__':
    main()
