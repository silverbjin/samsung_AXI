"""A-01 L0. No ROS mocks are misrepresented as physical navigation."""
from pathlib import Path
import json
import math
import sys

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/smartdish_robot"))
from smartdish_robot.contract import (
    GoalContractError, UnconfiguredDestination, parse_goal,
    load_pose_config, resolve_pose, result_json, nav2_result_name,
)

POSE_FILE = ROOT / "src/smartdish_robot/config/table_poses.yaml"


@pytest.mark.parametrize("leg,destination", [
    ("TO_TABLE", "T03"), ("TO_RETURN", "DISH_RETURN"),
    ("TO_HOME", "HOME"),
])
def test_three_exact_legs(leg, destination):
    assert parse_goal(json.dumps({
        "request_id": "REQ-001", "leg": leg, "destination_id": destination,
    })).destination_id == destination


@pytest.mark.parametrize("raw", [
    "{", "[]", "null", "42",
    '{"request_id":"","leg":"TO_TABLE","destination_id":"T03"}',
    '{"request_id":" REQ ","leg":"TO_TABLE","destination_id":"T03"}',
    '{"request_id":"REQ","leg":"TO_HOME","destination_id":"T03"}',
    '{"request_id":"REQ","leg":"TO_TABLE","destination_id":"HOME"}',
    '{"request_id":"REQ","leg":"TO_RETURN","destination_id":"T03"}',
    '{"request_id":"REQ","leg":"TO_UNKNOWN","destination_id":"HOME"}',
])
def test_bad_request_never_enters_nav2(raw):
    with pytest.raises(GoalContractError):
        parse_goal(raw)


def test_released_map_source_and_physically_verified_return():
    poses = load_pose_config(POSE_FILE)
    home = resolve_pose(poses, "HOME")
    t03 = resolve_pose(poses, "T03")
    old = yaml.safe_load((ROOT / "src/restaurant_delivery/config/s3_map_waypoints.yaml").read_text())
    assert (home.x, home.y, home.yaw) == tuple(old["pickup"][k] for k in ("x", "y", "yaw"))
    assert (t03.x, t03.y, t03.yaw) == tuple(old["table_3"][k] for k in ("x", "y", "yaw"))
    dish = resolve_pose(poses, "DISH_RETURN")
    assert (dish.x, dish.y, dish.yaw) == (-1.15, 1.60, -1.57079632679)
    # Future regressions must still reject an unconfigured/null return pose.
    with pytest.raises(UnconfiguredDestination, match="UNCONFIGURED_DESTINATION"):
        resolve_pose({"DISH_RETURN": {"x": None, "y": 1.60, "yaw": 0.0}},
                     "DISH_RETURN")


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), True, "5.25"])
def test_non_numeric_destination_fails_closed(bad):
    with pytest.raises(UnconfiguredDestination):
        resolve_pose({"HOME": {"x": bad, "y": 0, "yaw": 0}}, "HOME")


def test_wrong_frame_or_keys_rejected(tmp_path):
    for data in [
        {"frame": "odom", "poses": {"HOME": {}, "T03": {}, "DISH_RETURN": {}}},
        {"frame": "map", "poses": {"HOME": {}}},
    ]:
        file = tmp_path / "bad.yaml"
        file.write_text(yaml.safe_dump(data))
        with pytest.raises(GoalContractError):
            load_pose_config(file)


def test_nav_result_contract_and_task_result_mapping():
    class FakeTask:
        def __init__(self, name): self.name = name
    for name, expected in [("SUCCEEDED", "SUCCEEDED"),
                           ("FAILED", "FAILED"), ("CANCELED", "CANCELED"),
                           ("UNKNOWN", "FAILED")]:
        result, reason = nav2_result_name(FakeTask(name))
        assert result == expected
        obj = json.loads(result_json("REQ-001", "TO_TABLE", result, reason))
        assert list(obj) == ["request_id", "leg", "result", "reason"]
        assert obj["request_id"] == "REQ-001"
    with pytest.raises(GoalContractError):
        result_json("R", "TO_TABLE", "UNKNOWN")
