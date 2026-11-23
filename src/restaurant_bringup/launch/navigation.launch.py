"""S3 candidate: official Nav2 stack, published map and one real robot."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    here=get_package_share_directory('restaurant_bringup')
    nav=get_package_share_directory('nav2_bringup')
    root=os.environ.get('RESTAURANT_ROOT','')
    map_default=os.path.join(root,'maps','restaurant_map.yaml')
    params_default=os.path.join(root,'generated','nav2_params.yaml')
    return LaunchDescription([
        DeclareLaunchArgument('robot_sdf'),
        DeclareLaunchArgument('gui',default_value='true'),
        DeclareLaunchArgument('map',default_value=map_default),
        DeclareLaunchArgument('params_file',default_value=params_default),
        DeclareLaunchArgument('bridge_config',default_value=os.path.join(here,'config','bridge.yaml')),
        DeclareLaunchArgument('vision_camera_offset_z',default_value='0'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(here,'launch','world.launch.py')),
            launch_arguments={'robot_sdf':LaunchConfiguration('robot_sdf'),
                              'gui':LaunchConfiguration('gui'),
                              'bridge_config':LaunchConfiguration('bridge_config'),
                              'vision_camera_offset_z':LaunchConfiguration('vision_camera_offset_z')}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav,'launch','bringup_launch.py')),
            launch_arguments={'slam':'False','map':LaunchConfiguration('map'),
                              'params_file':LaunchConfiguration('params_file'),
                              'use_sim_time':'True','autostart':'True',
                              'use_composition':'False','use_respawn':'False'}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav,'launch','rviz_launch.py')),
            condition=IfCondition(LaunchConfiguration('gui')),
            launch_arguments={'use_sim_time':'true'}.items()),
    ])
