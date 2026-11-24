"""Opt-in SmartDish A adapter. NO_GOAL is the only launch default.

For real goals, use interactive 'ros2 run ... -p goals_enabled:=true' so
the /dev/tty confirmation cannot be hidden by a launch service supervisor.
"""
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
from pathlib import Path


def generate_launch_description():
    poses = str(Path(get_package_share_directory("smartdish_robot")) /
                "config/table_poses.yaml")
    return LaunchDescription([
        DeclareLaunchArgument("poses_file", default_value=poses),
        Node(package="smartdish_robot", executable="navigation_adapter",
             name="smartdish_navigation_adapter",
             parameters=[{"poses_file": LaunchConfiguration("poses_file"),
                          "goals_enabled": False,
                          "set_initial_home": False}],
             output="screen"),
    ])
