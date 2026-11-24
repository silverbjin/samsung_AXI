#!/usr/bin/env python3
"""E integration witness: observe real UI -> D -> A -> Nav2; never publish a goal.

Only live ROS 2 messages are accepted. A pure-Python verifier is kept importable
without ROS for L0 regression, but synthetic samples cannot produce live PASS.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

LEGS = ("TO_TABLE", "TO_RETURN", "TO_HOME")
DEST = ("T03", "DISH_RETURN", "HOME")


def verify_observations(d):
    """Assess captured physical trace, not a simulation of a Nav2 result."""
    requests = d.get("requests", [])
    goals = d.get("goals", [])
    results = d.get("results", [])
    states = d.get("states", [])
    if len(requests) != 1 or requests[0]["table_id"] != "T03":
        return "UI_SINGLE_T03_REQUEST_NOT_PROVEN"
    req = requests[0]
    if req.get("ai_enabled") is not False:
        return "AI_OFF_REQUIRED"
    if (req.get("table_wait_s"), req.get("dropoff_wait_s")) != (10, 5):
        return "WAIT_10_5_NOT_CONFIGURED"
    rid = req["request_id"]
    if len(goals) != 3 or len(results) != 3:
        return "THREE_REAL_GOALS_OR_RESULTS_MISSING"
    if [g["leg"] for g in goals] != list(LEGS):
        return "GOAL_ORDER_WRONG"
    if [g["destination_id"] for g in goals] != list(DEST):
        return "DESTINATION_MISMATCH"
    if [r["leg"] for r in results] != list(LEGS):
        return "NAV_RESULT_ORDER_WRONG"
    for x in goals + results:
        if x.get("request_id") != rid:
            return "REQUEST_ID_MISMATCH"
    for i, result in enumerate(results):
        if result.get("result") != "SUCCEEDED" or result.get("reason") != "":
            return "NAV2_NOT_SUCCEEDED_" + LEGS[i]
        if goals[i]["odom_max_m"] < 0.25 or goals[i]["odom_count"] < 3:
            return "ODOM_MOVEMENT_NOT_PROVEN_" + LEGS[i]
        if goals[i]["scan_count"] < 3:
            return "SCAN_NOT_OBSERVED_" + LEGS[i]
    state_names = [s["state"] for s in states]
    required = ("TO_TABLE", "WAIT_LOADING", "TO_RETURN",
                "WAIT_UNLOADING", "TO_HOME", "COMPLETED")
    try:
        indexes = [state_names.index(s) for s in required]
    except ValueError:
        return "REQUIRED_STATUS_MISSING"
    if indexes != sorted(indexes):
        return "STATUS_ORDER_WRONG"
    if any(s["state"] in ("AI_CHECK", "NEEDS_CONFIRMATION")
           for s in states):
        return "AI_OFF_TRIGGERED_AI_CHECK"
    if goals[1]["t"] - results[0]["t"] < 9.7:
        return "TABLE_WAIT_BEFORE_NAV_SUCCESS_OR_TOO_SHORT"
    if goals[2]["t"] - results[1]["t"] < 4.7:
        return "RETURN_WAIT_BEFORE_NAV_SUCCESS_OR_TOO_SHORT"
    if states[indexes[-1]]["t"] < results[2]["t"] - 0.3:
        return "COMPLETED_BEFORE_NAV_RESULT"
    return ""


def observe(evidence_path, source_sha, timeout_s):
    import rclpy
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import LaserScan
    from std_msgs.msg import String
    from rclpy.qos import (
        QoSProfile, HistoryPolicy, ReliabilityPolicy, DurabilityPolicy,
        qos_profile_sensor_data,
    )

    data = {
        "scope": "SMARTDISH_E_AI_OFF_REAL_GAZEBO_WSL2_L3",
        "source_sha": source_sha,
        "verdict": "NOT_PASS",
        "first_error": None,
        "request_id": None,
        "requests": [], "goals": [], "results": [], "states": [],
        "odom_samples": 0, "scan_samples": 0,
        "time_type": "time.monotonic seconds",
        "ui_applied_completed": "SHELL_LOG_CHECK_REQUIRED",
    }
    last_xy = None
    completed_at = None
    current = None
    rclpy.init()
    node = rclpy.create_node("smartdish_e_live_witness")
    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST, depth=10,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )

    def die(reason):
        if not data["first_error"]:
            data["first_error"] = reason

    def odom_cb(msg):
        nonlocal last_xy
        last_xy = (float(msg.pose.pose.position.x),
                   float(msg.pose.pose.position.y))
        data["odom_samples"] += 1
        if current is not None and current["start_xy"] is not None:
            current["odom_count"] += 1
            current["odom_max_m"] = max(
                current["odom_max_m"], math.dist(last_xy, current["start_xy"]))

    def scan_cb(msg):
        if len(msg.ranges) > 10:
            data["scan_samples"] += 1
            if current is not None:
                current["scan_count"] += 1

    def parse_msg(msg):
        try:
            obj = json.loads(msg.data)
            if not isinstance(obj, dict):
                raise ValueError("NOT_OBJECT")
            return obj
        except (ValueError, TypeError) as e:
            die("INVALID_JSON_" + str(e))
            return None

    def on_request(msg):
        x = parse_msg(msg)
        if x is None:
            return
        if data["requests"]:
            die("SECOND_REQUEST_OBSERVED")
            return
        if not isinstance(x.get("request_id"), str) or not x["request_id"]:
            die("INVALID_REQUEST_ID")
            return
        data["requests"].append(x)
        data["request_id"] = x["request_id"]
        print("SMARTDISH_E_UI_REQUEST=" + json.dumps(x, sort_keys=True), flush=True)

    def on_goal(msg):
        nonlocal current
        x = parse_msg(msg)
        if x is None:
            return
        if not data["requests"] or x.get("request_id") != data["request_id"]:
            die("UNMATCHED_NAV_GOAL")
            return
        if current is not None:
            die("OVERLAPPING_GOALS")
            return
        if len(data["goals"]) >= 3:
            die("EXTRA_NAV_GOAL")
            return
        x.update(t=time.monotonic(), odom_count=0,
                 odom_max_m=0.0, scan_count=0, start_xy=last_xy)
        data["goals"].append(x)
        current = x
        print("SMARTDISH_E_NAV_GOAL=" +
              json.dumps({k: v for k, v in x.items() if k != "start_xy"},
                         sort_keys=True), flush=True)

    def on_result(msg):
        nonlocal current
        x = parse_msg(msg)
        if x is None:
            return
        if current is None or x.get("request_id") != data["request_id"]:
            die("RESULT_WITHOUT_ACTIVE_GOAL")
            return
        if x.get("leg") != current.get("leg"):
            die("RESULT_LEG_MISMATCH")
            return
        x["t"] = time.monotonic()
        data["results"].append(x)
        print("SMARTDISH_E_NAV_RESULT=" + json.dumps(x, sort_keys=True), flush=True)
        current.pop("start_xy", None)
        current["odom_max_m"] = round(current["odom_max_m"], 3)
        current = None
        if x.get("result") != "SUCCEEDED":
            die("NAV2_FAILED_OR_CANCELED_" + str(x.get("leg")))

    def on_status(msg):
        nonlocal completed_at
        x = parse_msg(msg)
        if x is None:
            return
        if not data["requests"] or x.get("request_id") != data["request_id"]:
            return
        x["t"] = time.monotonic()
        data["states"].append(x)
        print("SMARTDISH_E_STATE=" + json.dumps(x, sort_keys=True), flush=True)
        if x.get("state") == "COMPLETED":
            completed_at = time.monotonic()
        if x.get("state") in ("ERROR", "CANCELED"):
            die("MISSION_" + x["state"] + "_" + str(x.get("reason")))

    node.create_subscription(Odometry, "/odom", odom_cb, qos_profile_sensor_data)
    node.create_subscription(LaserScan, "/scan", scan_cb, qos_profile_sensor_data)
    for topic, cb in (
        ("/collection/request", on_request),
        ("/collection/nav_goal", on_goal),
        ("/collection/nav_result", on_result),
        ("/collection/status", on_status),
    ):
        node.create_subscription(String, topic, cb, qos)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    print("SMARTDISH_E_OBSERVER_READY_NO_GOAL", flush=True)
    begin = time.monotonic()
    try:
        while rclpy.ok() and time.monotonic() - begin < timeout_s:
            rclpy.spin_once(node, timeout_sec=0.15)
            if data["first_error"]:
                break
            if completed_at and time.monotonic() - completed_at > 1.0:
                reason = verify_observations(data)
                if reason:
                    die(reason)
                else:
                    data["verdict"] = "AI_OFF_LIVE_TRACE_PASS_UI_LOG_PENDING"
                break
        else:
            die("UI_CLICK_OR_THREE_LEG_COMPLETION_TIMEOUT")
    except KeyboardInterrupt:
        die("OPERATOR_INTERRUPTED")
    except BaseException as e:
        die("OBSERVER_EXCEPTION_" + repr(e))
    finally:
        data["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        evidence_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    if data["verdict"] != "AI_OFF_LIVE_TRACE_PASS_UI_LOG_PENDING":
        print("SMARTDISH_E_FIRST_FAILURE=" + str(data["first_error"]), flush=True)
        return 2
    print("SMARTDISH_E_LIVE_TRACE_PASS_UI_APPLIED_CHECK_PENDING", flush=True)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", type=Path, required=True)
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--timeout", type=int, default=1100)
    a = ap.parse_args()
    if len(a.source_sha) != 40:
        sys.exit("SOURCE_SHA_MUST_BE_FULL_40_CHAR")
    sys.exit(observe(a.evidence, a.source_sha, a.timeout))


if __name__ == "__main__":
    main()
