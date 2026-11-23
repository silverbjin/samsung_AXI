"""A-02 isolated package/interface safety checks (not Gazebo L2)."""
from pathlib import Path
import ast
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src/smartdish_robot"
sys.path.insert(0, str(PKG))
from smartdish_robot.contract import parse_goal, resolve_pose, load_pose_config


def test_entrypoint_and_ros_dependencies():
    setup = (PKG / "setup.py").read_text()
    package = ET.parse(PKG / "package.xml")
    names = {e.text for e in package.findall("./exec_depend")}
    assert {"rclpy", "nav2_simple_commander", "std_msgs", "geometry_msgs",
            "sensor_msgs", "nav_msgs", "python3-yaml"} <= names
    assert "navigation_adapter = smartdish_robot.navigation_adapter:main" in setup
    assert (PKG / "resource/smartdish_robot").exists()


def test_default_launch_no_goal_and_only_one_adapter():
    source = (PKG / "launch/smartdish_robot.launch.py").read_text()
    ast.parse(source)
    assert '"goals_enabled": False' in source
    assert source.count('Node(package="smartdish_robot"') == 1


def test_adapter_never_bypasses_collision_monitor():
    source = (PKG / "smartdish_robot/navigation_adapter.py").read_text()
    tree = ast.parse(source)
    assert "goToPose(" in source
    assert "getResult(" in source
    assert "isTaskComplete(" in source
    assert '"/collection/nav_goal"' in source
    assert '"/collection/nav_result"' in source
    assert 'create_publisher(String, "/collection/nav_result"' in source
    assert '"/cmd_vel"' not in source
    assert "OPERATOR_TTY_REQUIRED_NO_GOAL" in source
    assert "ODOM_MOVEMENT_NOT_PROVEN" in source


def test_goal_config_required_before_nav2():
    src = (PKG / "smartdish_robot/navigation_adapter.py").read_text()
    assert src.index("resolve_pose(self.poses, goal.destination_id)") < src.index("self.nav.goToPose(")
    assert src.index("approve_in_tty()") < src.index("adapter.enable_goal_subscription()")


def test_handoff_manual_goal_command_is_real_json_not_escaped_json():
    """A-DBG-01: shell quoting -> ROS YAML -> actual String.data -> JSON."""
    import json
    import yaml
    guide = (ROOT / "docs/handoff/A_HANDOFF.md").read_text()
    command = next(line.strip() for line in guide.splitlines()
                   if line.strip().startswith("'data: ") and "REQ-A-01" in line)
    payload = yaml.safe_load(command[1:-1])["data"]
    decoded = json.loads(payload)
    assert decoded == {
        "request_id": "REQ-A-01",
        "leg": "TO_TABLE",
        "destination_id": "T03",
    }
