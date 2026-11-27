import ast
import pytest
from smartdish_a04_launch_overlay import patch_docking

SOURCE="""nodes=[Node(name='controller_server',remappings=remappings + [('cmd_vel','cmd_vel_nav')]),
Node(name='docking_server',remappings=remappings),
ComposableNode(name='docking_server',remappings=remappings),
Node(name='collision_monitor',remappings=remappings)]"""
def test_exact_docking_only():
    p=patch_docking(SOURCE)
    assert p.count("('cmd_vel', 'cmd_vel_nav')")==2
    assert "Node(name='collision_monitor',remappings=remappings)" in p
    assert "Node(name='controller_server',remappings=remappings + [('cmd_vel','cmd_vel_nav')])" in p
    ast.parse(p)
def test_drift_fails_closed():
    with pytest.raises(RuntimeError):patch_docking("Node(name='docking_server',remappings=remappings)")
    with pytest.raises(RuntimeError):patch_docking(SOURCE.replace("remappings=remappings)","remappings=other)"))
