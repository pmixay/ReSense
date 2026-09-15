# ReSense — ROS 2 Humble image with the detector node, RViz and offline tools.
#   docker build -t resense -f docker/Dockerfile .
#   docker run --rm -it --net=host -v /path/to/for_hackathon:/data resense \
#       ros2 launch resense_ros detector.launch.py bag:=/data/roundT_doubleT rviz:=true
FROM ros:humble-ros-base-jammy

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-numpy python3-scipy python3-sklearn python3-yaml \
        ros-humble-vision-msgs ros-humble-rviz2 ros-humble-rosbag2 \
        ros-humble-rosbag2-storage-default-plugins ros-humble-rosbag2-storage-mcap \
        ros-humble-foxglove-bridge \
    && rm -rf /var/lib/apt/lists/*

# offline / research tooling (bag reading without ROS, plots, synthetic injection)
RUN pip3 install --no-cache-dir "rosbags>=0.9" "matplotlib>=3.6" "open3d>=0.17" "pytest>=7"

WORKDIR /opt/resense
COPY pyproject.toml README.md ./
COPY resense ./resense
COPY configs ./configs
RUN pip3 install --no-cache-dir -e .

# ROS 2 workspace
COPY ros2_ws/src /opt/resense/ros2_ws/src
RUN . /opt/ros/humble/setup.sh && cd /opt/resense/ros2_ws && colcon build --symlink-install

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "resense_ros", "detector.launch.py"]
