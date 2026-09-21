# ReSense — ROS 2 Humble image with the detector node, RViz and the Foxglove bridge.
#
#   docker build -t resense -f docker/Dockerfile .                         # runtime image (what the jury builds)
#   docker build -t resense --build-arg WITH_TOOLS=1 -f docker/Dockerfile . # + offline tools and the test suite (CI)
#   docker run --rm -it --net=host -v /path/to/for_hackathon:/data resense \
#       ros2 launch resense_ros detector.launch.py bag:=/data/roundT_doubleT rviz:=true
#
# The runtime image contains only what the node needs: pinned numpy / scipy / scikit-learn /
# pyyaml, the ROS 2 packages, RViz, rosbag2, foxglove_bridge. WITH_TOOLS=1 adds the pure python
# bag reader, plots, Open3D (synthetic obstacles) and pytest so the suite can be run inside the
# image:  docker run --rm resense python3 -m pytest -q /opt/resense/tests
FROM ros:humble-ros-base-jammy

ARG WITH_TOOLS=0

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip python3-numpy python3-yaml \
        ros-humble-vision-msgs ros-humble-nav-msgs ros-humble-tf2-ros-py \
        ros-humble-rviz2 ros-humble-rosbag2 \
        ros-humble-rosbag2-storage-default-plugins ros-humble-rosbag2-storage-mcap \
        ros-humble-foxglove-bridge \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/resense
COPY pyproject.toml README.md ./
COPY resense ./resense
COPY configs ./configs
# Exact versions so that the jury builds the stack we measured on (numpy stays 1.x: ROS 2 Humble
# python bindings are not built against numpy 2). The package itself is installed without
# dependency resolution on top of them, and not in editable mode: jammy's pip 22.0.2 with the
# system setuptools 59.6 has no PEP 660 build_editable hook.
RUN pip3 install "numpy==1.26.4" "scipy==1.13.1" "scikit-learn==1.5.2" "pyyaml==6.0.2" \
    && pip3 install --no-deps .

# optional offline / research tooling (bag reading without ROS, plots, synthetic injection, tests)
# scripts/ carries the dataset-free ROS smoke test (make_smoke_bag.py + smoke_test.sh) and the
# acceptance checker; they are small and need nothing beyond the runtime stack (the smoke bag
# generator itself needs open3d, i.e. WITH_TOOLS=1).
COPY tests ./tests
COPY scripts ./scripts
RUN if [ "$WITH_TOOLS" = "1" ]; then \
        pip3 install "rosbags==0.10.11" "matplotlib==3.10.7" "open3d==0.19.0" "pytest==8.4.2"; \
    fi

# ROS 2 workspace. configs/default.yaml is the single source of truth for the detector
# parameters; it is copied over the package copy so the node can never run stale values.
COPY ros2_ws/src /opt/resense/ros2_ws/src
COPY configs/default.yaml /opt/resense/ros2_ws/src/resense_ros/config/detector.yaml
RUN . /opt/ros/humble/setup.sh && cd /opt/resense/ros2_ws && colcon build --symlink-install

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
CMD ["ros2", "launch", "resense_ros", "detector.launch.py"]
