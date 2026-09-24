"""ros2 launch resense_ros detector.launch.py [bag:=/data/for_hackathon/roundT_doubleT] [rviz:=true] [loop:=true]

Every node parameter is a launch argument, so the demo can be retuned without rebuilding.
``input_topic`` is a comma-separated candidate list; the node also auto-discovers PointCloud2
topics unless ``auto_discover:=false`` (the organizers' bags disagree on the topic name).
``bag:=`` plays a bag from the launch file (``loop:=true`` forever, ``rate:=`` playback rate);
``ego_speed_mps:=22`` (or ``speed_topic:=`` / ``odom_topic:=``) feeds the train speed to the
multi-frame accumulation; ``publish_tf`` links the fixed frame ``resense_lidar`` to the bag's frame.
A different LiDAR mount: ``sensor_forward:=+x sensor_left:=+y sensor_up:=+z`` (axis mapping),
``mount_roll_deg:=`` / ``mount_pitch_deg:=`` / ``mount_yaw_deg:=`` (fixed tilt), and
``auto_calibrate:=true`` (default) finds orientation and tilt from the rails in the first frames.
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# node parameter -> (default, python type, description). The type matters: a LaunchConfiguration
# substitutes to a string, and rclpy rejects a string for a parameter declared bool or double.
PARAMS = {
    "input_topic": ("/lidar_points,/sensing/lidar/hesai128/pointcloud", str,
                    "comma-separated candidate input topics"),
    "auto_discover": ("true", bool, "also subscribe to PointCloud2 topics found on the graph"),
    "discover_period": ("2.0", float, "s between discovery scans while the input is silent"),
    "publish_markers": ("true", bool, "RViz MarkerArray"),
    "publish_corridor_cloud": ("true", bool, "points inside the corridor, for debugging"),
    "marker_x_max": ("250.0", float, "m, how far the corridor outline is drawn"),
    "output_frame": ("", str, "frame_id of the published markers/detections; empty = the input's"),
    "stats_period": ("2.0", float, "s between fps / latency log lines"),
    "ego_speed_mps": ("-1.0", float, "train speed in m/s for multi-frame accumulation; < 0 = unknown "
                                     "(speed_topic / odom_topic; none = single-frame path, no accumulation)"),
    "speed_topic": ("", str, "std_msgs/Float32 topic carrying the train speed in m/s (optional)"),
    "odom_topic": ("", str, "nav_msgs/Odometry topic; twist.linear.x is taken as the train speed (optional)"),
    "speed_timeout": ("1.0", float, "s after which a speed message no longer counts"),
    "publish_tf": ("true", bool, "broadcast a static identity TF tf_parent_frame -> input frame id"),
    "tf_parent_frame": ("resense_lidar", str, "fixed frame used by the RViz / Foxglove layouts"),
    # v0.6: sensor mount (the LiDAR position is not fixed between trains) and production guards
    "sensor_forward": ("", str, "sensor axis pointing forward, e.g. -y (hackathon mount) or +x; empty = config file"),
    "sensor_left": ("", str, "sensor axis pointing left; empty = config file"),
    "sensor_up": ("", str, "sensor axis pointing up; empty = config file"),
    "mount_roll_deg": ("-999.0", float, "fixed roll correction in deg (-999 = config file)"),
    "mount_pitch_deg": ("-999.0", float, "fixed pitch correction in deg (-999 = config file)"),
    "mount_yaw_deg": ("-999.0", float, "fixed yaw correction in deg (-999 = config file)"),
    "auto_calibrate": ("true", bool, "find the sensor orientation / roll / pitch from rails and bed in the first frames"),
    "stale_timeout": ("0.5", float, "s without an input frame before the decision becomes FAULT"),
    "startup_grace": ("2.0", float, "s after start before 'no LiDAR frame received yet' is published as FAULT"),
    "max_consecutive_errors": ("5", int, "processing exceptions in a row before the detector is reset"),
    # v0.6.1: several recordings / topic names through one running node
    "input_switch_timeout": ("1.0", float, "s the active input topic must be silent before another topic is taken"),
    "new_input_gap": ("30.0", float, "s of forward header-stamp jump taken as a new recording (detector restarted)"),
    "hole_reset_gap": ("1.0", float, "s of forward header-stamp jump that resets the scene state (calibration kept)"),
    "input_queue_depth": ("40", int, "frames the input subscription may hold between two processed frames"),
    # v0.6.4: `ros2 bag play` sends the first seconds of a recording back to back (it preloads the bag)
    "catchup_step": ("0.3", float, "s of recording between processed frames while frames wait (a burst from the "
                                   "player); 0 = always process the newest frame only"),
    "catchup_max_lag": ("5.0", float, "s: waiting frames older than the newest by more than this are dropped"),
    "input_reliability": ("auto", str, "input QoS: auto = match the publishers (reliable for ros2 bag play of the "
                                       "organizers' recordings), reliable, best_effort"),
}


def _bag_condition(loop: bool):
    """Play the bag only when bag:= is set, in the requested loop mode."""
    negate = "" if loop else "not "
    return IfCondition(PythonExpression([
        "'", LaunchConfiguration("bag"), "' != '' and ",
        negate, "'", LaunchConfiguration("loop"), "'.lower() in ('true', '1')",
    ]))


def generate_launch_description():
    share = get_package_share_directory("resense_ros")
    default_cfg = os.path.join(share, "config", "detector.yaml")
    default_rviz = os.path.join(share, "rviz", "resense.rviz")

    args = [DeclareLaunchArgument(k, default_value=d, description=doc)
            for k, (d, _, doc) in PARAMS.items()]
    args += [
        DeclareLaunchArgument("config_file", default_value=default_cfg),
        DeclareLaunchArgument("rviz", default_value="false"),
        DeclareLaunchArgument("bag", default_value="", description="optional bag to play"),
        DeclareLaunchArgument("rate", default_value="1.0"),
        DeclareLaunchArgument("loop", default_value="false", description="replay the bag forever"),
        DeclareLaunchArgument("delay", default_value="3.0",
                              description="s the player waits before the first message (DDS discovery)"),
    ]

    params = {k: ParameterValue(LaunchConfiguration(k), value_type=t)
              for k, (_, t, _) in PARAMS.items()}
    params["config_file"] = ParameterValue(LaunchConfiguration("config_file"), value_type=str)

    play = ["ros2", "bag", "play", LaunchConfiguration("bag"),
            "--rate", LaunchConfiguration("rate"), "--clock", "--delay", LaunchConfiguration("delay")]

    return LaunchDescription(args + [
        Node(package="resense_ros", executable="detector_node", name="resense_detector",
             output="screen", parameters=[params]),
        Node(package="rviz2", executable="rviz2", name="rviz2", arguments=["-d", default_rviz],
             condition=IfCondition(LaunchConfiguration("rviz")), output="log"),
        # NOTE: playing from the launch file races the node's startup; --delay (default 3 s) gives
        # discovery time, and scripts/run_headless.sh / dry_run.sh also wait for /resense/status.
        # Two variants rather than one conditional argument: an empty argv element would be read
        # by `ros2 bag play` as a second bag path.
        ExecuteProcess(cmd=play + ["--loop"], output="screen", condition=_bag_condition(True)),
        ExecuteProcess(cmd=play, output="screen", condition=_bag_condition(False)),
    ])
