"""A-02: Safe adapter for /collection/nav_goal -> official BasicNavigator.

No custom planner, no /cmd_vel publisher, no fabricated navigation success.
Run only after existing restaurant_bringup Nav2/AMCL and Gazebo are started.
"""
import json
import math
from pathlib import Path
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator
from nav_msgs.msg import Odometry
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String

from .tty_approval import require_operator_approval

from .contract import (
    GoalContractError, NavigationGoal, load_pose_config, nav2_result_name,
    parse_goal, resolve_pose, result_json,
)


JSON_QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE,
)
SENSOR_AGE_LIMIT_S = 2.0


def log(marker, **fields):
    print("SMARTDISH_A_" + marker + " " +
          json.dumps(fields, sort_keys=True, ensure_ascii=False), flush=True)


def build_pose(nav: BasicNavigator, pose) -> PoseStamped:
    message = PoseStamped()
    message.header.frame_id = "map"
    message.header.stamp = nav.get_clock().now().to_msg()
    message.pose.position.x = pose.x
    message.pose.position.y = pose.y
    message.pose.orientation.z = math.sin(pose.yaw / 2.0)
    message.pose.orientation.w = math.cos(pose.yaw / 2.0)
    return message


def approve_in_tty():
    """Explicit field TTY acceptance. ROS topic subscription is created later."""
    require_operator_approval()
    log("OPERATOR_APPROVED", mode="EXPLICIT_TTY")


class NavigationAdapter:
    def __init__(self, navigator: BasicNavigator, poses):
        self.nav = navigator
        self.poses = poses
        self.last_scan = None
        self.last_odom = None
        self.xy = None
        self.active = None
        self.pending = None
        self.completed = []
        self.segment_start = None
        self.segment_samples = 0
        self.segment_max_m = 0.0
        self.result_pub = navigator.create_publisher(String, "/collection/nav_result", JSON_QOS)
        navigator.create_subscription(LaserScan, "/scan", self._scan_cb, 10)
        navigator.create_subscription(Odometry, "/odom", self._odom_cb, 10)
        # The goal subscription is created ONLY after Nav2, sensors and TTY approval.
        self.goal_sub = None

    def _scan_cb(self, msg: LaserScan):
        if msg.ranges:
            self.last_scan = time.monotonic()

    def _odom_cb(self, msg: Odometry):
        self.last_odom = time.monotonic()
        self.xy = (float(msg.pose.pose.position.x), float(msg.pose.pose.position.y))
        if self.active is not None and self.segment_start is not None:
            self.segment_samples += 1
            self.segment_max_m = max(
                self.segment_max_m, math.dist(self.segment_start, self.xy))

    def sensor_ready(self) -> bool:
        now = time.monotonic()
        return (self.xy is not None
                and self.last_scan is not None and self.last_odom is not None
                and now - self.last_scan <= SENSOR_AGE_LIMIT_S
                and now - self.last_odom <= SENSOR_AGE_LIMIT_S)

    def wait_for_sensors(self, timeout_s=35.0):
        deadline = time.monotonic() + timeout_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self.nav, timeout_sec=0.2)
            if self.sensor_ready():
                log("SENSOR_PREFLIGHT_PASS_NO_GOAL", scan=True, odom=True)
                return
        raise RuntimeError("PREGOAL_SCAN_OR_ODOM_MISSING")

    def enable_goal_subscription(self):
        self.goal_sub = self.nav.create_subscription(
            String, "/collection/nav_goal", self._goal_cb, JSON_QOS)
        log("READY", goal_topic="/collection/nav_goal",
            result_topic="/collection/nav_result", pose_frame="map")

    def _publish_result(self, goal: NavigationGoal, result: str, reason: str):
        msg = String()
        msg.data = result_json(goal.request_id, goal.leg, result, reason)
        self.result_pub.publish(msg)
        log("NAV_RESULT", request_id=goal.request_id, leg=goal.leg,
            result=result, reason=reason, odom_samples=self.segment_samples,
            odom_max_displacement_m=round(self.segment_max_m, 3))

    def _goal_cb(self, message: String):
        try:
            goal = parse_goal(message.data)
        except GoalContractError as exc:
            # No fake/empty request IDs. Return FAILED only for correlatable input.
            try:
                p = json.loads(message.data)
                if isinstance(p, dict) and isinstance(p.get("request_id"), str)                         and p["request_id"].strip() and isinstance(p.get("leg"), str):
                    self._publish_result(
                        NavigationGoal(p["request_id"], p["leg"], ""),
                        "FAILED", str(exc))
            except (ValueError, TypeError):
                pass
            log("GOAL_REJECTED_NO_NAV2", reason=str(exc))
            return

        key = (goal.request_id, goal.leg)
        if key in self.completed or (self.active and
                                      key == (self.active.request_id, self.active.leg))                 or (self.pending and
                    key == (self.pending.request_id, self.pending.leg)):
            log("DUPLICATE_IGNORED", request_id=goal.request_id, leg=goal.leg)
            return
        if self.pending or self.active:
            self._publish_result(goal, "FAILED", "BUSY")
            return
        self.pending = goal

    def _start_pending(self):
        goal, self.pending = self.pending, None
        try:
            pose = resolve_pose(self.poses, goal.destination_id)
        except GoalContractError as exc:
            self._publish_result(goal, "FAILED", str(exc))
            self._remember(goal)
            return
        if not self.sensor_ready():
            self._publish_result(goal, "FAILED", "SENSORS_NOT_READY")
            self._remember(goal)
            return
        self.segment_start = self.xy
        self.segment_samples = 0
        self.segment_max_m = 0.0
        self.active = goal
        try:
            self.nav.goToPose(build_pose(self.nav, pose))
            log("NAV_GOAL_SENT", request_id=goal.request_id, leg=goal.leg,
                destination_id=goal.destination_id,
                map_x=pose.x, map_y=pose.y, map_yaw=pose.yaw)
        except Exception as exc:
            log("NAV2_GOAL_EXCEPTION", error=repr(exc))
            self._publish_result(goal, "FAILED", "NAV2_GOAL_EXCEPTION")
            self._remember(goal)
            self.active = None

    def _remember(self, goal):
        self.completed.append((goal.request_id, goal.leg))
        if len(self.completed) > 256:
            self.completed.pop(0)

    def _complete_active(self):
        goal = self.active
        try:
            raw = self.nav.getResult()
            result, reason = nav2_result_name(raw)
            # A Nav2 Action result alone is not proof of actual displacement.
            if result == "SUCCEEDED" and (
                    self.segment_samples < 2 or self.segment_max_m < 0.05):
                result, reason = "FAILED", "ODOM_MOVEMENT_NOT_PROVEN"
        except Exception as exc:
            log("NAV2_RESULT_EXCEPTION", error=repr(exc))
            result, reason = "FAILED", "NAV2_RESULT_EXCEPTION"
        self._publish_result(goal, result, reason)
        self._remember(goal)
        self.active = None
        self.segment_start = None

    def run(self):
        while rclpy.ok():
            rclpy.spin_once(self.nav, timeout_sec=0.1)
            if self.pending and not self.active:
                self._start_pending()
            if self.active:
                try:
                    done = self.nav.isTaskComplete()
                except Exception as exc:
                    log("NAV2_POLL_EXCEPTION", error=repr(exc))
                    self._publish_result(self.active, "FAILED", "NAV2_POLL_EXCEPTION")
                    self._remember(self.active)
                    self.active = None
                    continue
                if done:
                    self._complete_active()


def main():
    rclpy.init()
    nav = BasicNavigator(node_name="smartdish_navigation_adapter")
    nav.set_parameters([Parameter("use_sim_time", Parameter.Type.BOOL, True)])
    default_poses = str(Path(get_package_share_directory("smartdish_robot")) /
                        "config/table_poses.yaml")
    nav.declare_parameter("poses_file", default_poses)
    nav.declare_parameter("goals_enabled", False)
    nav.declare_parameter("set_initial_home", False)
    adapter = None
    try:
        poses = load_pose_config(
            nav.get_parameter("poses_file").get_parameter_value().string_value)
        adapter = NavigationAdapter(nav, poses)
        # Never silently reset AMCL while an already-running robot is elsewhere.
        if nav.get_parameter("set_initial_home").value:
            home = resolve_pose(poses, "HOME")
            nav.setInitialPose(build_pose(nav, home))
            log("INITIAL_HOME_SET", operator_asserted_spawn_at_home=True)
        log("WAIT_NAV2_ACTIVE_NO_GOAL", localizer="amcl")
        nav.waitUntilNav2Active(localizer="amcl")
        adapter.wait_for_sensors()
        if not nav.get_parameter("goals_enabled").value:
            log("PREFLIGHT_PASS_NO_GOAL", goals_enabled=False)
            return
        approve_in_tty()
        adapter.enable_goal_subscription()
        adapter.run()
    except KeyboardInterrupt:
        if adapter and adapter.active:
            nav.cancelTask()
            log("INTERRUPTED_CANCEL_REQUESTED", confirmed_result=False)
    except (RuntimeError, GoalContractError) as exc:
        log("BLOCKED_NO_GOAL_OR_ABORTED", reason=str(exc))
        raise SystemExit(2)
    finally:
        nav.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
