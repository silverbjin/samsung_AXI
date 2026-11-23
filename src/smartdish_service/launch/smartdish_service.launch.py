"""D nodes only. A's Navigation Adapter / Gazebo are started separately."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    ai = LaunchConfiguration("ai_available")
    return LaunchDescription([
        DeclareLaunchArgument("ai_available", default_value="false"),
        Node(package="smartdish_service", executable="smartdish_manager",
             output="screen", arguments=["--ai-available", ai]),
        Node(package="smartdish_service", executable="smartdish_ui",
             output="screen", arguments=["--ai-available", ai]),
    ])
