"""Explicit Owner-only C+D integration nodes; A/Nav2 launch separately.

Default false keeps the user-approved AI OFF launcher untouched.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    ai = LaunchConfiguration("ai_available")
    owner = LaunchConfiguration("owner_gazebo_integration")
    model = LaunchConfiguration("model_path")
    return LaunchDescription([
        DeclareLaunchArgument("ai_available", default_value="false"),
        DeclareLaunchArgument("owner_gazebo_integration", default_value="false"),
        DeclareLaunchArgument("model_path", default_value=""),
        # Both D nodes require the same opt-in. Normal AI OFF behavior defaults.
        Node(package="smartdish_service", executable="smartdish_manager",
             output="screen", condition=IfCondition(owner),
             arguments=["--ai-available", ai, "--owner-gazebo-integration"]),
        Node(package="smartdish_service", executable="smartdish_ui",
             output="screen", condition=IfCondition(owner),
             arguments=["--ai-available", ai, "--owner-gazebo-integration"]),
        Node(package="smartdish_service", executable="smartdish_manager",
             output="screen", condition=UnlessCondition(owner),
             arguments=["--ai-available", ai]),
        Node(package="smartdish_service", executable="smartdish_ui",
             output="screen", condition=UnlessCondition(owner),
             arguments=["--ai-available", ai]),
        Node(package="smartdish_ai", executable="stability_inference_node",
             output="screen",
             parameters=[{
                 "model_path": model,
                 "owner_gazebo_integration": ParameterValue(owner, value_type=bool),
                 "stable_confidence_min": 0.80,
                 "unstable_confidence_min": 0.80,
                 "max_image_age_s": 2.0,
             }]),
    ])
