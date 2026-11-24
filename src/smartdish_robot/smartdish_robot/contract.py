"""Pure-Python validation boundary for the SmartDish A↔D JSON contract.

No ROS imports: junior developers can test malformed inputs before running Gazebo.
"""
from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Mapping

import yaml


LEG_DESTINATION = {
    "TO_TABLE": "T03",
    "TO_RETURN": "DISH_RETURN",
    "TO_HOME": "HOME",
}


class GoalContractError(ValueError):
    """Malformed command: never forward it to Nav2."""


class UnconfiguredDestination(GoalContractError):
    """A map-frame access pose was not verified/configured."""


@dataclass(frozen=True)
class NavigationGoal:
    request_id: str
    leg: str
    destination_id: str


@dataclass(frozen=True)
class MapPose:
    x: float
    y: float
    yaw: float


def parse_goal(raw: str) -> NavigationGoal:
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise GoalContractError("INVALID_JSON") from exc
    if not isinstance(payload, dict):
        raise GoalContractError("JSON_OBJECT_REQUIRED")
    request_id = payload.get("request_id")
    if (not isinstance(request_id, str) or not request_id
            or request_id != request_id.strip() or len(request_id) > 128):
        raise GoalContractError("INVALID_REQUEST_ID")
    leg = payload.get("leg")
    dest = payload.get("destination_id")
    if not isinstance(leg, str) or not isinstance(dest, str):
        raise GoalContractError("INVALID_GOAL_FIELDS")
    if LEG_DESTINATION.get(leg) != dest:
        raise GoalContractError("INVALID_GOAL_COMBINATION")
    return NavigationGoal(request_id, leg, dest)


def load_pose_config(path: str | Path) -> Mapping:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GoalContractError("POSE_CONFIG_READ_FAILED") from exc
    if not isinstance(data, dict) or data.get("frame") != "map":
        raise GoalContractError("MAP_FRAME_REQUIRED")
    poses = data.get("poses")
    if not isinstance(poses, dict) or set(poses) != set(LEG_DESTINATION.values()):
        raise GoalContractError("POSE_KEYS_MISMATCH")
    return poses


def resolve_pose(poses: Mapping, destination_id: str) -> MapPose:
    if destination_id not in LEG_DESTINATION.values():
        raise GoalContractError("UNKNOWN_DESTINATION")
    item = poses.get(destination_id)
    if not isinstance(item, dict) or set(item) != {"x", "y", "yaw"}:
        raise UnconfiguredDestination("UNCONFIGURED_DESTINATION")
    numbers = [item.get(key) for key in ("x", "y", "yaw")]
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) for value in numbers):
        raise UnconfiguredDestination("UNCONFIGURED_DESTINATION")
    return MapPose(*(float(v) for v in numbers))


def result_json(request_id: str, leg: str, result: str, reason: str = "") -> str:
    if result not in {"SUCCEEDED", "FAILED", "CANCELED"}:
        raise GoalContractError("INVALID_NAV_RESULT")
    return json.dumps({
        "request_id": request_id, "leg": leg,
        "result": result, "reason": reason,
    }, ensure_ascii=False, separators=(",", ":"))


def nav2_result_name(task_result) -> tuple[str, str]:
    """Only a real finished BasicNavigator task may call this function."""
    name = getattr(task_result, "name", "")
    if name == "SUCCEEDED":
        return "SUCCEEDED", ""
    if name == "CANCELED":
        return "CANCELED", "NAV2_CANCELED"
    if name == "FAILED":
        return "FAILED", "NAV2_FAILED"
    return "FAILED", "NAV2_UNKNOWN_RESULT"
