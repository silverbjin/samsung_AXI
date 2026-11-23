"""S1 baseline: local SDF + unmodified official Jazzy Waffle Pi model.

The bridge YAML intentionally differs from ROBOTIS default: ROS2 Jazzy/Nav2
publishes geometry_msgs/Twist, while the original Waffle Pi YAML says TwistStamped.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable, DeclareLaunchArgument, IncludeLaunchDescription, GroupAction, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robotis = get_package_share_directory('turtlebot3_gazebo')
    here = get_package_share_directory('restaurant_bringup')
    world_pkg = get_package_share_directory('restaurant_world')
    gz_sim = get_package_share_directory('ros_gz_sim')
    world_file = os.path.join(world_pkg, 'worlds', 'restaurant.sdf')
    robot_default = os.path.join(robotis, 'models', 'turtlebot3_waffle_pi', 'model.sdf')
    robot_urdf = os.path.join(robotis, 'urdf', 'turtlebot3_waffle_pi.urdf')
    with open(robot_urdf, encoding='utf-8') as f:
        description = f.read()
    robot_sdf = LaunchConfiguration('robot_sdf')
    gui = LaunchConfiguration('gui')
    return LaunchDescription([
        DeclareLaunchArgument('robot_sdf', default_value=robot_default),
        DeclareLaunchArgument('gui', default_value='true'),
        # Optional S6 RGB-on-demand mode; default preserves accepted S5.
        DeclareLaunchArgument('bridge_config',default_value=os.path.join(here,'config','bridge.yaml')),
        # Separate S6 viewpoint-only smoke, not a navigation Goal.
        DeclareLaunchArgument('spawn_x',default_value='-2.60'),
        DeclareLaunchArgument('spawn_y',default_value='-2.20'),
        DeclareLaunchArgument('spawn_yaw',default_value='0'),
        DeclareLaunchArgument('vision_camera_offset_z',default_value='0'),
        # S6/WSLg opt-in only. S5 original GUI behavior is the default.
        DeclareLaunchArgument('s6_gui_xcb',default_value='false'),
        DeclareLaunchArgument('s6_gui_exit_shutdown',default_value='true'),
        AppendEnvironmentVariable('GZ_SIM_RESOURCE_PATH', os.path.join(robotis, 'models')),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(gz_sim, 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': ['-r -s -v2 ', world_file], 'on_exit_shutdown': 'true'}.items()),
        GroupAction(
            scoped=True,
            condition=IfCondition(gui),
            actions=[
                # Keep Qt workaround local to the Gazebo GUI launch scope.
                SetEnvironmentVariable(name='QT_QPA_PLATFORM',value='xcb',
                    condition=IfCondition(LaunchConfiguration('s6_gui_xcb'))),
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(os.path.join(gz_sim,'launch','gz_sim.launch.py')),
                    launch_arguments={'gz_args':'-g -v2',
                        'on_exit_shutdown':LaunchConfiguration('s6_gui_exit_shutdown')}.items()),
            ]),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description, 'use_sim_time': True}], output='screen'),
        Node(package='ros_gz_sim', executable='create', name='waffle_pi_spawner',
             arguments=['-name', 'waffle_pi', '-file', robot_sdf,
                        '-x', LaunchConfiguration('spawn_x'),
                        '-y', LaunchConfiguration('spawn_y'),
                        '-Y', LaunchConfiguration('spawn_yaw'), '-z', '0.02'], output='screen'),
        Node(package='ros_gz_bridge', executable='parameter_bridge',
             parameters=[{'config_file': LaunchConfiguration('bridge_config')}],
             output='screen'),
        # S2 RGB-D optical TF. Harmless in S1 even if RGB-D sensor not generated yet.
        Node(package='tf2_ros', executable='static_transform_publisher',
             arguments=['--x', '0', '--y', '0', '--z', LaunchConfiguration('vision_camera_offset_z'),
                        '--roll', '-1.57079632679', '--pitch', '0', '--yaw', '-1.57079632679',
                        '--frame-id', 'camera_link', '--child-frame-id', 'restaurant_rgbd_optical'],
             output='screen'),
    ])
