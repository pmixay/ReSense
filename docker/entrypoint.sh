#!/bin/bash
set -e
source /opt/ros/humble/setup.bash
source /opt/resense/ros2_ws/install/setup.bash
# DDS transport: RESENSE_DDS=udp (default, the image's UDP-only profile) or shm (opt-in shared
# memory + UDP, needs --ipc=host); one INFO line names it (docker/dds_transport.sh)
source /opt/resense/dds_transport.sh
resense_dds_transport
exec "$@"
