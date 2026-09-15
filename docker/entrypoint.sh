#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
source /opt/resense/ros2_ws/install/setup.bash
exec "$@"
