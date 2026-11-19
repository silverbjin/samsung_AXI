"""S2 proposed mapping: official Nav2 SLAM Toolbox launch, no custom SLAM."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    here = get_package_share_directory('restaurant_bringup')
    nav = get_package_share_directory('nav2_bringup')
    return LaunchDescription([
        DeclareLaunchArgument('robot_sdf'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(here,'launch','world.launch.py')),
            launch_arguments={'robot_sdf': LaunchConfiguration('robot_sdf')}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav,'launch','slam_launch.py')),
            launch_arguments={'use_sim_time':'true','autostart':'true',
                              'params_file':os.path.join(nav,'params','nav2_params.yaml')}.items()),
    ])
