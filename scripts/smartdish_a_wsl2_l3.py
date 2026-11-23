#!/usr/bin/env python3
"""WSL2 owner L3: real Gazebo/Nav2 three-leg SmartDish A test.

Reuses the released S7 launch/Nav2 and shipped A NavigationAdapter.
Unlike GitHub CI's PTY harness, the operator must type approval at /dev/tty.
No simulated result, no direct cmd_vel, no bypass of Collision Monitor.
"""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import time

from s3_map_contract import validate_s2_map03_candidate
from ci_s2_map_smoke import end_process

LEGS = (("TO_TABLE", "T03"), ("TO_RETURN", "DISH_RETURN"), ("TO_HOME", "HOME"))


def assess_leg(item):
    """Small independent contract for test/teaching; never invents observations."""
    if item.get("result") != "SUCCEEDED" or item.get("reason") != "":
        return "NAV2_RESULT_NOT_SUCCEEDED"
    if item.get("odom_count", 0) < 3 or item.get("scan_count", 0) < 3:
        return "PHYSICAL_SENSOR_SAMPLES_MISSING"
    if item.get("odom_max_m", 0) < 0.25:
        return "PHYSICAL_ODOM_MOVEMENT_NOT_PROVEN"
    err = item.get("amcl_error_m")
    if err is None or not isinstance(err, (int, float)) or not math.isfinite(err) or err > .8:
        return "MAP_FRAME_GOAL_ACCURACY_NOT_PROVEN"
    return ""


def run(a):
    if not os.environ.get("WSL_DISTRO_NAME"):
        raise RuntimeError("A_OWNER_L3_REQUIRES_WSL2_NO_GOAL")
    if not os.isatty(0):
        raise RuntimeError("A_OWNER_L3_REQUIRES_INTERACTIVE_STDIN_NO_GOAL")
    import rclpy
    from rclpy.action import ActionClient
    from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
    from nav2_msgs.action import NavigateToPose
    from nav_msgs.msg import Odometry, OccupancyGrid
    from sensor_msgs.msg import LaserScan
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from tf2_msgs.msg import TFMessage
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import String
    from smartdish_robot.contract import load_pose_config, resolve_pose

    root = Path(__file__).resolve().parents[1]
    expected_map = root / "maps/candidates/s2_map03/restaurant_map.yaml"
    expected_poses = root / "src/smartdish_robot/config/table_poses.yaml"
    if a.map.resolve() != expected_map.resolve() or a.poses.resolve() != expected_poses.resolve():
        raise RuntimeError("A_OWNER_L3_REQUIRES_PINNED_S7_MAP_AND_PRODUCTION_POSES")
    custody = validate_s2_map03_candidate(root)
    poses = load_pose_config(a.poses)
    targets = {dest: resolve_pose(poses, dest) for _, dest in LEGS}
    verified_xy = {"HOME": (0., 0.), "T03": (5.25, .38),
                   "DISH_RETURN": (-1.15, 1.60)}
    for dest, expected in verified_xy.items():
        if math.dist((targets[dest].x, targets[dest].y), expected) > .001:
            raise RuntimeError("A_OWNER_L3_UNVERIFIED_PRODUCTION_POSE_" + dest)
    for file in (a.robot_sdf, a.map, a.params, a.poses):
        if not file.is_file():
            raise RuntimeError("A_OWNER_L3_REQUIRED_FILE_MISSING_" + str(file))
    if a.gui and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("A_OWNER_L3_GUI_DISPLAY_NOT_SET")

    a.evidence.parent.mkdir(parents=True, exist_ok=True)
    a.launch_log.parent.mkdir(parents=True, exist_ok=True)
    a.adapter_log.parent.mkdir(parents=True, exist_ok=True)
    state = {"clock": False, "scan": 0, "odom": None, "odom_n": 0,
             "map": None, "amcl": None, "map_tf": False, "odom_tf": False}
    results = {}
    evidence = {
        "kind": "SMARTDISH_A_REAL_GAZEBO_WSL2_OWNER_L3",
        "verdict": "NOT_RUN", "source_sha": a.source_sha,
        "request_id": "A-WSL2-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
                      + "-" + str(os.getpid()),
        "map_source_run": custody["release_run"],
        "map_pgm_sha256": custody["pgm_sha256"],
        "map_frame": "map", "gui_requested": a.gui,
        "tty_policy": "HUMAN_OPERATOR_TYPED_TO_DEV_TTY",
        "poses": {key: [pose.x, pose.y, pose.yaw] for key, pose in targets.items()},
        "legs": [], "nav_results": [], "first_error": None,
    }
    proc = None
    adapter = None
    node = None
    initialized = False
    launch_handle = None
    adapter_handle = None

    def odom_cb(m):
        state["odom"] = (float(m.pose.pose.position.x),
                         float(m.pose.pose.position.y))
        state["odom_n"] += 1

    def scan_cb(m):
        if len(m.ranges) > 10:
            state["scan"] += 1

    def tf_cb(m):
        for t in m.transforms:
            state["map_tf"] |= t.header.frame_id == "map" and t.child_frame_id == "odom"
            state["odom_tf"] |= (t.header.frame_id == "odom"
                                  and t.child_frame_id in ("base_link", "base_footprint"))

    def result_cb(m):
        try:
            obj = json.loads(m.data)
            if (set(obj) != {"request_id", "leg", "result", "reason"}
                    or obj["request_id"] != evidence["request_id"]
                    or obj["leg"] not in dict(LEGS) or obj["leg"] in results):
                raise ValueError("FOREIGN_DUPLICATE_OR_INVALID_RESULT")
        except (ValueError, KeyError, TypeError) as exc:
            evidence["first_error"] = "RESULT_CONTRACT_VIOLATION_" + str(exc)
            return
        results[obj["leg"]] = obj
        evidence["nav_results"].append(obj)
        print("SMARTDISH_A_WSL2_NAV_RESULT=" + json.dumps(obj, sort_keys=True),
              flush=True)

    def spin_once():
        if proc is not None and proc.poll() is not None:
            raise RuntimeError("A_OWNER_L3_NAV_LAUNCH_EXITED_" + str(proc.returncode))
        if adapter is not None and adapter.poll() is not None:
            raise RuntimeError("A_OWNER_L3_ADAPTER_EXITED_" + str(adapter.returncode))
        rclpy.spin_once(node, timeout_sec=.2)
        if evidence["first_error"]:
            raise RuntimeError(evidence["first_error"])

    def wait_until(predicate, seconds, name):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            spin_once()
            if predicate():
                return
        raise RuntimeError("A_OWNER_L3_TIMEOUT_" + name)

    try:
        launch_handle = a.launch_log.open("w")
        cmd = ["ros2", "launch", "restaurant_bringup", "navigation.launch.py",
               "gui:=" + ("true" if a.gui else "false"),
               "s6_stagger_nav_start:=true",
               "robot_sdf:=" + str(a.robot_sdf.resolve()),
               "map:=" + str(a.map.resolve()),
               "params_file:=" + str(a.params.resolve())]
        print("SMARTDISH_A_WSL2_START_REAL_GAZEBO gui=" + str(a.gui), flush=True)
        proc = subprocess.Popen(cmd, stdout=launch_handle,
                                stderr=subprocess.STDOUT, start_new_session=True)
        rclpy.init(args=None)
        initialized = True
        node = rclpy.create_node("smartdish_a_wsl2_l3_owner")
        node.create_subscription(Odometry, "/odom", odom_cb, qos_profile_sensor_data)
        node.create_subscription(LaserScan, "/scan", scan_cb, qos_profile_sensor_data)
        node.create_subscription(Clock, "/clock",
                                 lambda m: state.update(clock=m.clock.sec > 0),
                                 qos_profile_sensor_data)
        node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose",
                                 lambda m: state.update(amcl=(
                                     m.pose.pose.position.x, m.pose.pose.position.y)), 10)
        node.create_subscription(TFMessage, "/tf", tf_cb, qos_profile_sensor_data)
        map_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(OccupancyGrid, "/map",
                                 lambda m: state.update(map=m), map_qos)
        json_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.VOLATILE)
        publisher = node.create_publisher(String, "/collection/nav_goal", json_qos)
        node.create_subscription(String, "/collection/nav_result", result_cb, json_qos)
        nav_action = ActionClient(node, NavigateToPose, "/navigate_to_pose")

        wait_until(lambda: state["clock"] and state["scan"] >= 3
                   and state["odom"] is not None and state["map"] is not None,
                   220, "CLOCK_SCAN_ODOM_MAP")
        map_msg = state["map"]
        if (map_msg.info.width != custody["width"]
                or map_msg.info.height != custody["height"]
                or map_msg.header.frame_id != "map"):
            raise RuntimeError("A_OWNER_L3_SAVED_MAP_WRONG")
        wait_until(lambda: state["amcl"] is not None and state["map_tf"]
                   and state["odom_tf"] and nav_action.wait_for_server(timeout_sec=.1),
                   170, "AMCL_TF_NAV2")
        if math.dist(state["amcl"], (0., 0.)) > .90:
            raise RuntimeError("A_OWNER_L3_ROBOT_NOT_STARTING_AT_HOME")
        print("SMARTDISH_A_WSL2_REAL_GAZEBO_PREFLIGHT_PASS_NO_GOAL", flush=True)

        from ament_index_python.packages import get_package_prefix
        adapter_exe = Path(get_package_prefix("smartdish_robot")) / \
            "lib/smartdish_robot/navigation_adapter"
        if not adapter_exe.is_file():
            raise RuntimeError("A_OWNER_L3_ADAPTER_ENTRYPOINT_NOT_INSTALLED")
        adapter_handle = a.adapter_log.open("w")
        adapter_cmd = [str(adapter_exe), "--ros-args",
                       "-p", "goals_enabled:=true",
                       "-p", "set_initial_home:=false",
                       "-p", "poses_file:=" + str(a.poses.resolve())]
        print("SMARTDISH_A_WSL2_WAIT_OPERATOR_TTY_INPUT_NO_GOAL", flush=True)
        print("로봇 위치·주변 장애물을 확인한 다음 터미널 요청에 직접 승인 문구를 입력하십시오.", flush=True)
        print("동의하지 않으면 다른 문구를 입력하거나 Ctrl+C로 중지하십시오.", flush=True)
        # Inherit the user's controlling /dev/tty. Never supply approval via
        # stdin, pseudo-TTY injection, environment variable, or a ROS topic.
        adapter = subprocess.Popen(adapter_cmd, stdin=subprocess.DEVNULL,
                                   stdout=adapter_handle, stderr=subprocess.STDOUT,
                                   start_new_session=False)
        ready_marker = "SMARTDISH_A_READY"
        wait_until(lambda: publisher.get_subscription_count() >= 1 and
                   ready_marker in a.adapter_log.read_text(errors="replace"),
                   180, "HUMAN_OPERATOR_APPROVAL")
        print("SMARTDISH_A_WSL2_HUMAN_TTY_APPROVED_READY", flush=True)
        for leg, dest in LEGS:
            start = state["odom"]
            n_odom, n_scan = state["odom_n"], state["scan"]
            max_delta = 0.0
            msg = String()
            msg.data = json.dumps({
                "request_id": evidence["request_id"],
                "leg": leg, "destination_id": dest,
            }, separators=(",", ":"))
            publisher.publish(msg)
            print("SMARTDISH_A_WSL2_GOAL_SENT=" + msg.data, flush=True)
            deadline = time.monotonic() + a.leg_timeout
            while time.monotonic() < deadline:
                spin_once()
                max_delta = max(max_delta, math.dist(start, state["odom"]))
                if leg in results:
                    break
            else:
                raise RuntimeError("A_OWNER_L3_NAV_RESULT_TIMEOUT_" + leg)
            result = results[leg]
            current_amcl = state["amcl"]
            record = {
                "leg": leg, "destination_id": dest,
                "result": result["result"], "reason": result["reason"],
                "odom_max_m": round(max_delta, 3),
                "odom_count": state["odom_n"] - n_odom,
                "scan_count": state["scan"] - n_scan,
                "goal_map": [targets[dest].x, targets[dest].y],
                "amcl_xy": current_amcl,
                "amcl_error_m": (round(math.dist(current_amcl,
                                         (targets[dest].x, targets[dest].y)), 3)
                                 if current_amcl is not None else None),
            }
            evidence["legs"].append(record)
            print("SMARTDISH_A_WSL2_PHYSICAL_LEG=" +
                  json.dumps(record, sort_keys=True), flush=True)
            reason = assess_leg(record)
            if reason:
                raise RuntimeError("A_OWNER_L3_" + reason + "_" + leg)
        if len(evidence["nav_results"]) != 3:
            raise RuntimeError("A_OWNER_L3_THREE_NAV_RESULTS_NOT_PROVEN")
        evidence["verdict"] = "ROBOT_ONLY_REAL_GAZEBO_WSL2_L3_PASS"
        print("SMARTDISH_A_WSL2_ROBOT_ONLY_3LEG_L3_PASS", flush=True)
    except BaseException as exc:
        evidence["verdict"] = "FAIL"
        evidence["first_error"] = evidence["first_error"] or repr(exc)
        print("SMARTDISH_A_WSL2_FIRST_FAILURE=" + evidence["first_error"], flush=True)
        raise
    finally:
        evidence.update(scan_count=state["scan"], odom_count=state["odom_n"],
                        map_tf=state["map_tf"], odom_tf=state["odom_tf"],
                        final_amcl_xy=state["amcl"])
        a.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        if adapter is not None and adapter.poll() is None:
            adapter.send_signal(signal.SIGINT)
            try:
                adapter.wait(timeout=12)
            except subprocess.TimeoutExpired:
                adapter.terminate()
                try:
                    adapter.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    adapter.kill()
                    adapter.wait()
        if node is not None:
            node.destroy_node()
        if initialized and rclpy.ok():
            rclpy.shutdown()
        end_process(proc)
        if adapter_handle:
            adapter_handle.close()
        if launch_handle:
            launch_handle.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("robot_sdf", "map", "params", "poses", "launch_log",
                "adapter_log", "evidence"):
        p.add_argument("--" + key.replace("_", "-"), dest=key,
                       required=True, type=Path)
    p.add_argument("--source-sha", required=True)
    p.add_argument("--leg-timeout", type=float, default=465)
    p.add_argument("--gui", action="store_true")
    a = p.parse_args()
    if a.leg_timeout < 30 or a.leg_timeout > 900:
        p.error("--leg-timeout must be 30..900 seconds")
    run(a)


if __name__ == "__main__":
    main()
