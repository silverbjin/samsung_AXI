"""E-only velocity overlay does not relax the final CM graph gate."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_e_nav_velocity_overlay import rewrite_docking,rewrite_share

SOURCE="""from launch_ros.actions import Node
from launch_ros.descriptions import ComposableNode
nodes = [
    Node(package='nav2_collision_monitor', name='collision_monitor', remappings=remappings),
    Node(package='opennav_docking',name='docking_server',remappings=remappings),
    ComposableNode(package='opennav_docking',name='docking_server',remappings=remappings),
]
"""
def test_only_docking_is_rewired():
    s=rewrite_docking(SOURCE)
    assert s.count("('cmd_vel', 'cmd_vel_nav')")==2
    assert "Node(package='nav2_collision_monitor', name='collision_monitor', remappings=remappings)" in s

def test_unknown_upstream_fails_closed():
    with pytest.raises(RuntimeError):rewrite_docking(SOURCE.replace("ComposableNode(package=","Other(package="))
    with pytest.raises(RuntimeError):rewrite_docking(SOURCE.replace("name='docking_server'","name='unknown'"))

def test_share_rewrite_exactly_one_call():
    assert rewrite_share("x=get_package_share_directory('nav2_bringup')",Path("/tmp/e"))=="x='/tmp/e'"
    with pytest.raises(RuntimeError):rewrite_share("x=1",Path("/tmp/e"))
