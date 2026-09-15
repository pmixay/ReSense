"""ros2 launch resense_ros detector.launch.py [bag:=/data/for_hackathon/roundT_doubleT] [rviz:=true]"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition, LaunchConfigurationNotEquals
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    share = get_package_share_directory("resense_ros")
    default_cfg = os.path.join(share, "config", "detector.yaml")
    default_rviz = os.path.join(share, "rviz", "resense.rviz")
    return LaunchDescription([
        DeclareLaunchArgument("input_topic", default_value="/lidar_points"),
        DeclareLaunchArgument("config_file", default_value=default_cfg),
        DeclareLaunchArgument("rviz", default_value="false"),
        DeclareLaunchArgument("bag", default_value="", description="optional bag to play (ros2 bag play)"),
        DeclareLaunchArgument("rate", default_value="1.0"),
        Node(
            package="resense_ros", executable="detector_node", name="resense_detector", output="screen",
            parameters=[{"input_topic": LaunchConfiguration("input_topic"),
                         "config_file": LaunchConfiguration("config_file")}],
        ),
        Node(
            package="rviz2", executable="rviz2", name="rviz2", arguments=["-d", default_rviz],
            condition=IfCondition(LaunchConfiguration("rviz")), output="log",
        ),
        ExecuteProcess(
            cmd=["ros2", "bag", "play", LaunchConfiguration("bag"), "--rate", LaunchConfiguration("rate"), "--clock"],
            condition=LaunchConfigurationNotEquals("bag", ""), output="screen",
        ),
    ])
