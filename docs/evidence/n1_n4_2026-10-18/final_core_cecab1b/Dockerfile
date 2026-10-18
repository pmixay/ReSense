FROM resense:lidar-7b7b02c
COPY resense/config.py /opt/resense/resense/config.py
COPY resense/config.py /usr/local/lib/python3.10/dist-packages/resense/config.py
COPY configs/default.yaml /opt/resense/configs/default.yaml
COPY ros2_ws/src/resense_ros/config/detector.yaml /opt/resense/ros2_ws/src/resense_ros/config/detector.yaml
RUN cd / && python3 -c "from resense.config import DetectorConfig; from resense import _native; assert DetectorConfig().calibration.orientation_replay_frames == 0; assert DetectorConfig.from_yaml('/opt/resense/configs/default.yaml').calibration.orientation_replay_frames == 0; assert DetectorConfig.from_yaml('/opt/resense/ros2_ws/install/resense_ros/share/resense_ros/config/detector.yaml').calibration.orientation_replay_frames == 0; print(_native.status())"
