#!/usr/bin/env python3
"""CI-only *real Gazebo* 3-leg test of the shipped A NavigationAdapter.

Uses the existing Nav2/AMCL/Collision Monitor and ROS std_msgs/String topics.
No mock Nav2, mock odom, synthetic success or owner WSL2 auto-approval.
"""
import argparse
import errno
import json
import math
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import time

from s3_map_contract import validate_s2_map03_candidate
from ci_s2_map_smoke import end_process

LEGS = (("TO_TABLE", "T03"), ("TO_RETURN", "DISH_RETURN"), ("TO_HOME", "HOME"))
REQ = "SMARTDISH-A-CI-L2-001"


def run(a):
    if (os.environ.get("CI", "").lower() != "true"
            or os.environ.get("GITHUB_ACTIONS", "").lower() != "true"
            or os.environ.get("WSL_DISTRO_NAME")
            or not os.environ.get("GZ_PARTITION", "").startswith("smartdish_a_")
            or not os.environ.get("ROS_DOMAIN_ID")):
        raise RuntimeError("CI_SIMULATION_ONLY_NO_OWNER_AUTOMATION")
    import rclpy
    from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                          qos_profile_sensor_data)
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from nav_msgs.msg import Odometry, OccupancyGrid
    from sensor_msgs.msg import LaserScan
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from tf2_msgs.msg import TFMessage
    from rosgraph_msgs.msg import Clock
    from std_msgs.msg import String
    from smartdish_robot.contract import load_pose_config, resolve_pose

    root = Path(__file__).resolve().parents[1]
    map_contract = validate_s2_map03_candidate(root)
    poses = load_pose_config(a.poses)
    targets = {dest: resolve_pose(poses, dest) for _, dest in LEGS}
    if a.map.resolve() != (root / "maps/candidates/s2_map03/restaurant_map.yaml").resolve():
        raise RuntimeError("REQUIRE_PINNED_S7_MAP")
    for name, xy in (("HOME", (0., 0.)), ("T03", (5.25, .38))):
        if math.dist((targets[name].x, targets[name].y), xy) > .001:
            raise RuntimeError("RELEASED_POSE_CHANGED_" + name)

    a.log.parent.mkdir(parents=True, exist_ok=True)
    a.evidence.parent.mkdir(parents=True, exist_ok=True)
    state = {"clock": False, "scan": 0, "odom": None, "odom_n": 0,
             "map": None, "amcl": None, "map_tf": False, "odom_tf": False}
    result_messages = {}
    evidence = {
        "kind": "A_REAL_GAZEBO_NAV2_ROBOT_ONLY",
        "verdict": "NOT_RUN", "request_id": REQ,
        "source_sha": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                               cwd=root, text=True).strip(),
        "map_sha256": map_contract["pgm_sha256"],
        "map_release_run": map_contract["release_run"],
        "poses": {k: [v.x, v.y, v.yaw] for k, v in targets.items()},
        "legs": [], "nav_results": [], "first_error": None,
        "tty_approval": "CI_ONLY_EXPLICIT_PROMPT_AFTER_10_SECONDS",
    }
    proc = None
    child = None
    fd = None
    node = None
    started = False

    def on_odom(m):
        state["odom"] = (float(m.pose.pose.position.x), float(m.pose.pose.position.y))
        state["odom_n"] += 1

    def on_scan(m):
        if len(m.ranges) > 10:
            state["scan"] += 1

    def on_tf(m):
        for t in m.transforms:
            state["map_tf"] |= t.header.frame_id == "map" and t.child_frame_id == "odom"
            state["odom_tf"] |= (t.header.frame_id == "odom"
                                  and t.child_frame_id in ("base_link", "base_footprint"))

    def on_result(m):
        obj = json.loads(m.data)
        if (obj.get("request_id") != REQ or obj.get("leg") in result_messages
                or set(obj) != {"request_id", "leg", "result", "reason"}):
            evidence["first_error"] = "INVALID_OR_DUPLICATE_NAV_RESULT:" + repr(obj)
            return
        result_messages[obj["leg"]] = obj
        evidence["nav_results"].append(obj)
        print("A_L2_REAL_NAV_RESULT=" + json.dumps(obj, sort_keys=True), flush=True)

    try:
        with a.log.open("w") as log:
            cmd = ["ros2", "launch", "restaurant_bringup", "navigation.launch.py",
                   "gui:=false", "s6_stagger_nav_start:=true",
                   "robot_sdf:=" + str(a.robot_sdf.resolve()),
                   "map:=" + str(a.map.resolve()),
                   "params_file:=" + str(a.params.resolve())]
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True, env=os.environ.copy())
            rclpy.init(args=None)
            started = True
            node = rclpy.create_node("smartdish_a_real_gazebo_l2")
            node.create_subscription(Odometry, "/odom", on_odom, qos_profile_sensor_data)
            node.create_subscription(LaserScan, "/scan", on_scan, qos_profile_sensor_data)
            node.create_subscription(Clock, "/clock",
                                     lambda m: state.update(clock=m.clock.sec > 0),
                                     qos_profile_sensor_data)
            node.create_subscription(PoseWithCovarianceStamped, "/amcl_pose",
                                     lambda m: state.update(amcl=(
                                         m.pose.pose.position.x, m.pose.pose.position.y)), 10)
            node.create_subscription(TFMessage, "/tf", on_tf, qos_profile_sensor_data)
            map_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                 durability=DurabilityPolicy.TRANSIENT_LOCAL)
            node.create_subscription(OccupancyGrid, "/map",
                                     lambda m: state.update(map=m), map_qos)
            qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.VOLATILE)
            publisher = node.create_publisher(String, "/collection/nav_goal", qos)
            node.create_subscription(String, "/collection/nav_result", on_result, qos)
            action = ActionClient(node, NavigateToPose, "/navigate_to_pose")

            def spin():
                if proc.poll() is not None:
                    raise RuntimeError("NAV_LAUNCH_EXITED:" + str(proc.returncode))
                if child:
                    pid, status = os.waitpid(child, os.WNOHANG)
                    if pid == child:
                        raise RuntimeError("ADAPTER_EXITED:" + str(status))
                rclpy.spin_once(node, timeout_sec=.2)
                if evidence["first_error"]:
                    raise RuntimeError(evidence["first_error"])

            def await_ready(check, seconds, marker):
                until = time.monotonic() + seconds
                while time.monotonic() < until:
                    spin()
                    if check():
                        return
                raise RuntimeError("TIMEOUT_" + marker)

            await_ready(lambda: state["clock"] and state["scan"] >= 3
                        and state["odom"] is not None and state["map"] is not None,
                        220, "CLOCK_SCAN_ODOM_MAP")
            m = state["map"]
            if (m.info.width != map_contract["width"]
                    or m.info.height != map_contract["height"] or m.header.frame_id != "map"):
                raise RuntimeError("WRONG_MAP_FRAME_OR_DIMENSIONS")
            await_ready(lambda: state["amcl"] is not None and state["map_tf"]
                        and state["odom_tf"] and action.wait_for_server(timeout_sec=.1),
                        170, "AMCL_TF_ACTION")
            if math.dist(state["amcl"], (0., 0.)) > .9:
                raise RuntimeError("AMCL_START_NOT_AT_HOME")
            print("A_L2_REAL_GAZEBO_PREFLIGHT_PASS_NO_GOAL", flush=True)

            # pty.fork supplies a controlling /dev/tty to the unchanged adapter.
            child, fd = pty.fork()
            if child == 0:
                os.execvpe("ros2", ["ros2", "run", "smartdish_robot", "navigation_adapter",
                                   "--ros-args", "-p", "goals_enabled:=true",
                                   "-p", "set_initial_home:=false",
                                   "-p", "poses_file:=" + str(a.poses.resolve())],
                           os.environ.copy())
            os.set_blocking(fd, False)
            transcript = ""
            prompted_at = None
            approved = False
            ready = False
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                spin()
                if select.select([fd], [], [], 0)[0]:
                    try:
                        data = os.read(fd, 16384)
                    except OSError as exc:
                        if exc.errno == errno.EIO:
                            raise RuntimeError("ADAPTER_TTY_CLOSED") from exc
                        raise
                    if data:
                        out = data.decode("utf-8", "replace")
                        print(out, end="", flush=True)
                        transcript = (transcript + out)[-15000:]
                        if "YES-SMARTDISH-A-GOALS 입력:" in transcript and prompted_at is None:
                            prompted_at = time.monotonic()
                            print("A_L2_TTY_PROMPT_OBSERVED_NO_GOAL", flush=True)
                        if "SMARTDISH_A_READY" in transcript:
                            ready = True
                if prompted_at and not approved and time.monotonic() - prompted_at > 10:
                    os.write(fd, b"YES-SMARTDISH-A-GOALS\n")
                    approved = True
                    print("A_L2_SIMULATION_TTY_APPROVED_AFTER_DELAY", flush=True)
                if ready and approved and publisher.get_subscription_count() >= 1:
                    break
            else:
                raise RuntimeError("ADAPTER_NOT_READY_OR_APPROVAL_MISSING")

            for leg, dest in LEGS:
                start = state["odom"]
                odom_n = state["odom_n"]
                scan_n = state["scan"]
                max_m = 0.
                msg = String()
                msg.data = json.dumps({"request_id": REQ, "leg": leg,
                                       "destination_id": dest}, separators=(",", ":"))
                publisher.publish(msg)
                print("A_L2_GOAL_SENT=" + msg.data, flush=True)
                deadline = time.monotonic() + a.leg_timeout
                while time.monotonic() < deadline:
                    spin()
                    max_m = max(max_m, math.dist(start, state["odom"]))
                    if leg in result_messages:
                        break
                else:
                    raise RuntimeError("NAV_RESULT_TIMEOUT_" + leg)
                result = result_messages[leg]
                item = {
                    "leg": leg, "destination_id": dest,
                    "result": result["result"], "reason": result["reason"],
                    "odom_max_m": round(max_m, 3),
                    "odom_count": state["odom_n"] - odom_n,
                    "scan_count": state["scan"] - scan_n,
                    "amcl": state["amcl"],
                    "goal_map": [targets[dest].x, targets[dest].y],
                    "amcl_error_m": round(math.dist(state["amcl"],
                        (targets[dest].x, targets[dest].y)), 3)
                        if state["amcl"] is not None else None,
                }
                evidence["legs"].append(item)
                print("A_L2_PHYSICAL_LEG=" + json.dumps(item, sort_keys=True), flush=True)
                if (item["result"] != "SUCCEEDED" or item["reason"]
                        or item["odom_count"] < 3 or item["scan_count"] < 3
                        or max_m < .25 or item["amcl_error_m"] is None
                        or item["amcl_error_m"] > .8):
                    raise RuntimeError("REAL_LEG_NOT_PROVEN_" + leg)
            if len(evidence["nav_results"]) != 3:
                raise RuntimeError("MISSING_THREE_REAL_NAV_RESULTS")
            evidence["verdict"] = "ROBOT_ONLY_REAL_GAZEBO_L2_PASS"
            print("SMARTDISH_A_REAL_GAZEBO_3LEG_L2_PASS", flush=True)
    except BaseException as exc:
        evidence["first_error"] = evidence["first_error"] or repr(exc)
        evidence["verdict"] = "FAIL"
        print("SMARTDISH_A_L2_FIRST_FAILURE=" + evidence["first_error"], flush=True)
        raise
    finally:
        evidence.update(scan_count=state["scan"], odom_count=state["odom_n"],
                        amcl_pose=state["amcl"], map_tf=state["map_tf"],
                        odom_tf=state["odom_tf"])
        a.evidence.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        if child:
            try: os.killpg(child, signal.SIGINT)
            except ProcessLookupError: pass
            try: os.waitpid(child, 0)
            except ChildProcessError: pass
        if fd is not None:
            os.close(fd)
        if node:
            node.destroy_node()
        if started and rclpy.ok():
            rclpy.shutdown()
        end_process(proc)


def main():
    p = argparse.ArgumentParser()
    for key in ("robot_sdf", "map", "params", "poses", "log", "evidence"):
        p.add_argument("--" + key.replace("_", "-"), dest=key, type=Path, required=True)
    p.add_argument("--leg-timeout", type=float, default=465)
    run(p.parse_args())


if __name__ == "__main__":
    main()
