"""ros2 launch resense_ros detector.launch.py [bag:=/data/for_hackathon/roundT_doubleT] [rviz:=true]

Every node parameter is a launch argument, so the demo can be retuned without rebuilding.
``input_topic`` is a comma-separated candidate list; the node also auto-discovers PointCloud2
topics unless ``auto_discover:=false`` (the organizers' bags disagree on the topic name).
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
    "discover_period": ("2.0", float, "s between discovery scans while no frame has arrived"),
    "publish_markers": ("true", bool, "RViz MarkerArray"),
    "publish_corridor_cloud": ("true", bool, "points inside the corridor, for debugging"),
    "marker_x_max": ("250.0", float, "m, how far the corridor outline is drawn"),
    "output_frame": ("", str, "frame_id of the published markers/detections; empty = the input's"),
    "stats_period": ("2.0", float, "s between fps / latency log lines"),
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
    ]

    params = {k: ParameterValue(LaunchConfiguration(k), value_type=t)
              for k, (_, t, _) in PARAMS.items()}
    params["config_file"] = ParameterValue(LaunchConfiguration("config_file"), value_type=str)

    play = ["ros2", "bag", "play", LaunchConfiguration("bag"),
            "--rate", LaunchConfiguration("rate"), "--clock"]

    return LaunchDescription(args + [
        Node(package="resense_ros", executable="detector_node", name="resense_detector",
             output="screen", parameters=[params]),
        Node(package="rviz2", executable="rviz2", name="rviz2", arguments=["-d", default_rviz],
             condition=IfCondition(LaunchConfiguration("rviz")), output="log"),
        # NOTE: playing from the launch file races the node's startup and loses the first frames;
        # scripts/run_headless.sh and scripts/dry_run.sh wait for /resense/status before playing.
        # Two variants rather than one conditional argument: an empty argv element would be read
        # by `ros2 bag play` as a second bag path.
        ExecuteProcess(cmd=play + ["--loop"], output="screen", condition=_bag_condition(True)),
        ExecuteProcess(cmd=play, output="screen", condition=_bag_condition(False)),
    ])
