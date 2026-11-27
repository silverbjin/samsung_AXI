"""Explicit Owner-only C+D integration nodes; A/Nav2 launch separately.

Default false keeps the user-approved AI OFF launcher untouched.
"""
import os

from launch import LaunchDescription
from launch.actions import EmitEvent, RegisterEventHandler, OpaqueFunction
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def _guard_direct_owner_launch(context):
    """Direct launch cannot quietly skip the E Python runtime preflight."""
    owner = LaunchConfiguration("owner_gazebo_integration").perform(context).lower()
    ai = LaunchConfiguration("ai_available").perform(context).lower()
    model = LaunchConfiguration("model_path").perform(context)
    if owner in ("true", "1") and ai in ("true", "1") and model:
        if not os.environ.get("SMARTDISH_E_C_SITE_PACKAGES"):
            raise RuntimeError("E_OWNER_C_RUNTIME_CONTRACT_NOT_VERIFIED")
    return []


def generate_launch_description():
    # Only the C inference node sees the verified C venv site-packages.
    c_site = os.environ.get("SMARTDISH_E_C_SITE_PACKAGES", "").strip()
    parent_path = os.environ.get("PYTHONPATH", "")
    c_env = ({"PYTHONPATH": c_site + (":" + parent_path if parent_path else ""),
              "PYTHONNOUSERSITE": "1"}
             if c_site else {})
    ai = LaunchConfiguration("ai_available")
    owner = LaunchConfiguration("owner_gazebo_integration")
    model = LaunchConfiguration("model_path")
    c_node = Node(
        package="smartdish_ai", executable="stability_inference_node",
        output="screen", additional_env=c_env,
        parameters=[{
            "model_path": model,
            "owner_gazebo_integration": ParameterValue(owner, value_type=bool),
            "stable_confidence_min": 0.80,
            "unstable_confidence_min": 0.80,
            "max_image_age_s": 2.0,
        }])
    return LaunchDescription([
        DeclareLaunchArgument("ai_available", default_value="false"),
        DeclareLaunchArgument("owner_gazebo_integration", default_value="false"),
        DeclareLaunchArgument("model_path", default_value=""),
        OpaqueFunction(function=_guard_direct_owner_launch),
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
        c_node,
        # If a required real C model cannot load, end the Owner launch.
        # D/UI must not remain open suggesting model readiness.
        RegisterEventHandler(OnProcessExit(
            target_action=c_node,
            on_exit=[EmitEvent(event=Shutdown(
                reason="E_OWNER_C_MODEL_PROCESS_EXITED_FAIL_CLOSED"))])),
    ])
