#!/usr/bin/env python3
"""Small source-vs-generated configuration sanity check; no fake ROS pass."""
from pathlib import Path
import xml.etree.ElementTree as ET
import yaml

root = Path(__file__).resolve().parents[1]
world = ET.parse(root / 'src/restaurant_world/worlds/restaurant.sdf').getroot()
robot = ET.parse(root / 'generated/waffle_pi_rgbd.sdf').getroot()
params = yaml.safe_load((root / 'generated/nav2_params.yaml').read_text())
assert world.find("./world[@name='restaurant']") is not None
assert robot.find(".//sensor[@name='restaurant_registered_rgbd'][@type='rgbd_camera']") is not None
assert robot.find(".//sensor[@name='hls_lfcd_lds'][@type='gpu_lidar']") is not None
assert params['collision_monitor']['ros__parameters']['cmd_vel_out_topic'] == 'cmd_vel'
assert params['collision_monitor']['ros__parameters']['observation_sources'] == ['scan']
voxel = params['local_costmap']['local_costmap']['ros__parameters']['voxel_layer']
assert voxel['observation_sources'] == 'scan'
assert voxel['scan']['data_type'] == 'LaserScan'
assert voxel['scan']['topic'] in ('scan', '/scan')
assert 'rgbd' not in voxel
print('RESTAURANT_CI_GENERATED_CONTRACT_PASS')
