#!/usr/bin/env python3
"""A14-07: bounded REAL Gazebo/Jazzy positive controls for silent Contact sensors.

Independent proof that tray and floor sensor *types* can emit REAL contacts.
It NEVER synthesizes a no-contact message, validates the original silent
channel at capture time, or approves training GT. No A13 4-scene replay.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tarfile
import time

WORLD = "a14_contact_calibration"
TOPICS = {
    "tray": "/smartdish/a14/calibration/contact/tray",
    "floor": "/smartdish/a14/calibration/contact/floor",
}
PAIRS = {
    "tray": ("a14_cal_tray_target", "a14_cal_tray_projectile"),
    "floor": ("a14_cal_floor_target", "a14_cal_floor_projectile"),
}
WALL_BUDGET_S = 95.0
SERVER_READY_S = 24.0
ROS_DISCOVERY_S = 16.0
OBSERVE_S = 38.0
MIN_SIM_NS = 1_500_000_000
MAX_SAVED_PER_TOPIC = 80


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def generate_world():
    """Two different REAL falling bodies hit separate tray and floor targets.

    The SDF sensor schema is identical to A14 opt-in; target/topic identifiers
    are intentionally different so calibration cannot be presented as a
    production Contact trace.
    """
    pieces = [
        '<?xml version="1.0"?>',
        '<sdf version="1.9"><world name="' + WORLD + '">',
        '<gravity>0 0 -9.8</gravity>',
        '<physics name="a14_physics" type="ignored"><max_step_size>0.001</max_step_size></physics>',
    ]
    for filename, name in (
        ("gz-sim-physics-system", "gz::sim::systems::Physics"),
        ("gz-sim-user-commands-system", "gz::sim::systems::UserCommands"),
        ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
        ("gz-sim-contact-system", "gz::sim::systems::Contact"),
    ):
        pieces.append('<plugin filename="' + filename + '" name="' + name + '"/>')
    for key, x, z, top in (("tray", -1.5, 0.55, 0.60),
                            ("floor", 1.5, -0.05, 0.00)):
        model = "a14_cal_" + key + "_target"
        pieces.extend([
            '<model name="' + model + '"><static>true</static>',
            '<pose>' + str(x) + ' 0 ' + str(z) + ' 0 0 0</pose>',
            '<link name="body"><collision name="collision"><geometry><box>',
            '<size>1.2 1.2 0.1</size></box></geometry></collision>',
            '<sensor name="contact" type="contact"><always_on>true</always_on>',
            '<update_rate>50</update_rate><contact><collision>collision</collision>',
            '<topic>' + TOPICS[key] + '</topic></contact></sensor>',
            '</link></model>',
        ])
        # A separate dynamic projectile supplies undeniable positive contact.
        pieces.extend([
            '<model name="a14_cal_' + key + '_projectile"><static>false</static>',
            '<pose>' + str(x) + ' 0 ' + str(top + .80) + ' 0 0 0</pose>',
            '<link name="body"><inertial><mass>0.2</mass>',
            '<inertia><ixx>0.0008</ixx><iyy>0.0008</iyy><izz>0.0008</izz></inertia>',
            '</inertial><collision name="collision"><geometry><sphere>',
            '<radius>0.1</radius></sphere></geometry></collision></link></model>',
        ])
    pieces.append('</world></sdf>')
    return "\n".join(pieces) + "\n"


def bridge_config():
    rows = []
    for key, topic in TOPICS.items():
        rows.append({
            "ros_topic_name": topic, "gz_topic_name": topic,
            "ros_type_name": "ros_gz_interfaces/msg/Contacts",
            "gz_type_name": "gz.msgs.Contacts", "direction": "GZ_TO_ROS",
        })
    rows.append({
        "ros_topic_name": "/clock", "gz_topic_name": "/clock",
        "ros_type_name": "rosgraph_msgs/msg/Clock",
        "gz_type_name": "gz.msgs.Clock", "direction": "GZ_TO_ROS",
    })
    return rows


def pair_matches(key, collision1, collision2):
    names = (str(collision1), str(collision2))
    return all(any(expected in name for name in names) for expected in PAIRS[key])


def assess_positive_controls(events, clock_ns, source_sha):
    by_key = {}
    for key, topic in TOPICS.items():
        rows = [row for row in events if row.get("topic") == topic
                and isinstance(row.get("sim_time_ns"), int)
                and row["sim_time_ns"] > 0
                and row.get("stamp_source") == "ROS_CONTACT_HEADER_STAMP"
                and pair_matches(key, row.get("collision1", ""), row.get("collision2", ""))]
        by_key[key] = {
            "expected_topic": topic,
            "expected_pair": list(PAIRS[key]),
            "positive_collision_observed": bool(rows),
            "positive_event_count": len(rows),
            "first_stamp_ns": min((x["sim_time_ns"] for x in rows), default=None),
            "sample_collision_ids": ([rows[0].get("collision1_id"),
                                      rows[0].get("collision2_id")] if rows else []),
        }
    passed = clock_ns >= MIN_SIM_NS and all(
        item["positive_collision_observed"] for item in by_key.values())
    return {
        "schema": 1,
        "source_sha": source_sha,
        "physics_profile": "INDEPENDENT_CONTACT_POSITIVE_CALIBRATION",
        "verdict": "POSITIVE_CONTROL_PASS" if passed else "POSITIVE_CONTROL_HOLD",
        "sim_clock_max_ns": int(clock_ns),
        "sim_clock_coverage": "MEASURED" if clock_ns >= MIN_SIM_NS else "INCOMPLETE",
        "sensors": by_key,
        "production_contact_silence_resolved": False,
        "production_sensor_health": "NOT_MEASURED_BY_THIS_CONTROL",
        "no_contact_inferred_from_silence": False,
        "rule_candidate": "UNKNOWN",
        "label_status": "REVIEW_REQUIRED",
        "human_approved": False,
        "ground_truth": "NOT_OPERATOR_APPROVED",
        "approval_ledger_created": False,
        "first_error": None if passed else "A14_CAL_REAL_POSITIVE_CONTACT_OR_CLOCK_MISSING",
    }


def stop_owned(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGINT)
        proc.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=2)


def call(env, args, timeout=6):
    completed = subprocess.run(args, env=env, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, errors="replace",
                               timeout=timeout)
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-10000:],
        "stderr": completed.stderr[-5000:],
    }


def archive(directory):
    """Archives both successful and failed controls, without human GT."""
    folder = Path(directory)
    excluded = {"SHA256SUMS", "a14_contact_calibration_evidence.tar.gz",
                "a14_contact_calibration_evidence.tar.gz.sha256"}
    files = sorted(p for p in folder.iterdir() if p.is_file()
                   and p.name not in excluded and not p.is_symlink())
    (folder / "SHA256SUMS").write_text("".join(
        sha256(p) + "  " + p.name + "\n" for p in files))
    bundle = folder / "a14_contact_calibration_evidence.tar.gz"
    with tarfile.open(bundle, "w:gz") as output:
        for p in files + [folder / "SHA256SUMS"]:
            output.add(p, arcname=p.name)
    (folder / (bundle.name + ".sha256")).write_text(
        sha256(bundle) + "  " + bundle.name + "\n")
    return bundle


def run_calibration(source_sha, out_dir=None, budget_s=WALL_BUDGET_S):
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        raise ValueError("A14_CAL_SOURCE_SHA_FORMAT_INVALID")
    if not 30 <= budget_s <= WALL_BUDGET_S:
        raise ValueError("A14_CAL_WALL_BUDGET_INVALID")
    root = Path(__file__).resolve().parents[1]
    current = subprocess.check_output([
        "git", "-C", str(root), "-c", "safe.directory=" + str(root),
        "rev-parse", "HEAD"], text=True, timeout=8).strip()
    if current != source_sha:
        raise ValueError("A14_CAL_SOURCE_SHA_MISMATCH")
    folder = (Path(out_dir) if out_dir is not None else
              root / "generated" / "smartdish_a14" /
              ("contact_calibration_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
               + "_" + str(os.getpid())))
    folder.mkdir(parents=True, exist_ok=False)
    world_path = folder / "calibration_world.sdf"
    world_path.write_text(generate_world())
    import yaml
    bridge_path = folder / "calibration_bridge.yaml"
    bridge_path.write_text(yaml.safe_dump(bridge_config(), sort_keys=False))
    started = time.monotonic()
    deadline = started + budget_s
    env = os.environ.copy()
    env["GZ_PARTITION"] = "a14_cal_" + str(os.getpid())
    env["ROS_DOMAIN_ID"] = str(80 + os.getpid() % 32)
    result = {
        "schema": 1, "source_sha": source_sha,
        "verdict": "POSITIVE_CONTROL_HOLD",
        "world_sha256": sha256(world_path),
        "bridge_sha256": sha256(bridge_path),
        "gz_partition": env["GZ_PARTITION"],
        "ros_domain_id": env["ROS_DOMAIN_ID"],
        "max_wall_budget_seconds": budget_s,
        "source_type": "REAL_GAZEBO_ROS_CONTACTS_NOT_FIXTURE",
        "first_error": None, "human_approved": False,
        "ground_truth": "NOT_OPERATOR_APPROVED",
        "production_contact_silence_resolved": False,
        "rule_candidate": "UNKNOWN", "cleanup": [],
    }
    procs = []
    handles = []
    node = None
    rclpy_live = False
    events = []
    callbacks = dict.fromkeys(TOPICS, 0)
    sim_ns = 0
    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import qos_profile_sensor_data, QoSProfile
        from ros_gz_interfaces.msg import Contacts
        from rosgraph_msgs.msg import Clock
        os.environ["ROS_DOMAIN_ID"] = env["ROS_DOMAIN_ID"]
        rclpy.init()
        rclpy_live = True
        node = Node("a14_independent_contact_calibration")

        def clock_cb(msg):
            nonlocal sim_ns
            t = int(msg.clock.sec) * 1_000_000_000 + int(msg.clock.nanosec)
            sim_ns = max(sim_ns, t)

        def callback(key):
            def _observe(msg):
                callbacks[key] += 1
                stamp = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
                for contact in msg.contacts:
                    row = {
                        "topic": TOPICS[key],
                        "sim_time_ns": stamp,
                        "stamp_source": "ROS_CONTACT_HEADER_STAMP" if stamp > 0 else "INVALID_ZERO_STAMP",
                        "collision1": str(contact.collision1.name),
                        "collision2": str(contact.collision2.name),
                        "collision1_id": int(contact.collision1.id),
                        "collision2_id": int(contact.collision2.id),
                    }
                    if pair_matches(key, row["collision1"], row["collision2"]) \
                       and len(events) < MAX_SAVED_PER_TOPIC * len(TOPICS):
                        events.append(row)
            return _observe

        node.create_subscription(Clock, "/clock", clock_cb, QoSProfile(depth=10))
        for key, topic in TOPICS.items():
            node.create_subscription(Contacts, topic, callback(key),
                                     qos_profile_sensor_data)
        for name, command in (
            ("gazebo", ["gz", "sim", "-s", "-v2", str(world_path.resolve())]),
            ("bridge", ["ros2", "run", "ros_gz_bridge", "parameter_bridge",
                        "--ros-args", "-p", "config_file:=" + str(bridge_path.resolve())]),
        ):
            log_file = (folder / (name + ".log")).open("w")
            handles.append(log_file)
            procs.append(subprocess.Popen(
                command, env=env, stdin=subprocess.DEVNULL,
                stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True))
        # Bounded readiness: must have genuine Gazebo world service and ROS graph.
        service_ready = False
        while time.monotonic() < min(deadline, started + SERVER_READY_S):
            if procs[0].poll() is not None:
                raise RuntimeError("A14_CAL_GAZEBO_EXITED_DURING_STARTUP")
            answer = call(env, ["gz", "service", "-l"], timeout=4)
            if answer["returncode"] == 0 and "/world/" + WORLD + "/control" in answer["stdout"]:
                service_ready = True
                break
            rclpy.spin_once(node, timeout_sec=.10)
        if not service_ready:
            raise RuntimeError("A14_CAL_GAZEBO_WORLD_SERVICE_NOT_READY")
        readiness = {}
        until = min(deadline, time.monotonic() + ROS_DISCOVERY_S)
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=.1)
            readiness = {key: node.count_publishers(topic) for key, topic in TOPICS.items()}
            if all(count > 0 for count in readiness.values()):
                break
        result["ros_publisher_discovery"] = readiness
        if not all(count > 0 for count in readiness.values()):
            raise RuntimeError("A14_CAL_ROS_CONTACT_PUBLISHER_NOT_DISCOVERED")
        result["gazebo_topics_before_unpause"] = call(
            env, ["gz", "topic", "-l"], timeout=5)
        control = call(env, ["gz", "service",
                             "-s", "/world/" + WORLD + "/control",
                             "--reqtype", "gz.msgs.WorldControl",
                             "--reptype", "gz.msgs.Boolean",
                             "--timeout", "10000", "--req", "pause: false"], timeout=14)
        result["world_control"] = control
        if control["returncode"] != 0 or "data: true" not in control["stdout"].lower():
            raise RuntimeError("A14_CAL_GAZEBO_UNPAUSE_FAILED")
        observing_until = min(deadline, time.monotonic() + OBSERVE_S)
        while time.monotonic() < observing_until:
            if any(p.poll() is not None for p in procs):
                raise RuntimeError("A14_CAL_GAZEBO_OR_BRIDGE_EXITED")
            rclpy.spin_once(node, timeout_sec=.1)
            provisional = assess_positive_controls(events, sim_ns, source_sha)
            if provisional["verdict"] == "POSITIVE_CONTROL_PASS":
                break
        result.update(assess_positive_controls(events, sim_ns, source_sha))
        result["contact_callback_counts"] = callbacks.copy()
        if result["verdict"] != "POSITIVE_CONTROL_PASS":
            raise RuntimeError("A14_CAL_POSITIVE_SENSOR_OR_CLOCK_NOT_OBSERVED")
    except BaseException as exc:
        result["verdict"] = "POSITIVE_CONTROL_HOLD"
        result["first_error"] = str(exc)
    finally:
        for proc in reversed(procs):
            stop_owned(proc)
            result["cleanup"].append({
                "pid": proc.pid, "returncode_after_cleanup": proc.poll(),
                "stopped": proc.poll() is not None,
            })
        for fp in handles:
            fp.close()
        if node is not None:
            node.destroy_node()
        if rclpy_live:
            import rclpy
            rclpy.shutdown()
        result["all_owned_processes_stopped"] = all(
            row["stopped"] for row in result["cleanup"])
        result["wall_elapsed_seconds"] = round(time.monotonic() - started, 3)
        if not result["all_owned_processes_stopped"]:
            result["verdict"] = "POSITIVE_CONTROL_HOLD"
            result["first_error"] = "A14_CAL_OWNED_PROCESSES_NOT_CLEANED"
        (folder / "contact_events.jsonl").write_text("".join(
            json.dumps(row, sort_keys=True) + "\n" for row in events))
        (folder / "calibration_result.json").write_text(json.dumps(
            result, indent=2, sort_keys=True) + "\n")
        bundle = archive(folder)
        print("A14_CAL_DIAGNOSTIC_ARCHIVE=" + str(bundle), flush=True)
        print("A14_CAL_DIAGNOSTIC_ARCHIVE_SHA256=" + sha256(bundle), flush=True)
        print("A14_CAL_RESULT=" + result["verdict"], flush=True)
        print("A14_CAL_PRODUCTION_NO_CONTACT_NOT_PROVEN=true", flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sha", required=True)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--max-wall-seconds", type=float, default=WALL_BUDGET_S)
    args = parser.parse_args()
    try:
        result = run_calibration(args.sha, args.out_dir, args.max_wall_seconds)
    except Exception as exc:
        print("A14_CAL_PRECHECK_ERROR=" + repr(exc), file=sys.stderr, flush=True)
        return 2
    return 0 if result["verdict"] == "POSITIVE_CONTROL_PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
