#!/usr/bin/env python3
"""One real Gazebo headless no-Goal smoke; fails unless sensor data arrives.

This deliberately does not assert navigation, SLAM completion, GUI or safety
performance. The owner WSL2 still supplies the final visible DEMO-01 evidence.
"""
import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--robot-sdf', type=Path, required=True)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--wait-seconds', type=int, default=180)
    args = p.parse_args()
    if not args.robot_sdf.is_file():
        raise SystemExit('BLOCKED: generated Waffle Pi SDF missing')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    summary = args.log.parent / 'ci-gazebo-summary.txt'
    command = ['ros2', 'launch', 'restaurant_bringup', 'world.launch.py',
               'gui:=false', 'robot_sdf:=' + str(args.robot_sdf.resolve())]
    with args.log.open('w') as output:
        proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                start_new_session=True, env=os.environ.copy())
        start = time.monotonic()
        try:
            import rclpy
            from rclpy.qos import qos_profile_sensor_data
            from rosgraph_msgs.msg import Clock
            from nav_msgs.msg import Odometry
            from sensor_msgs.msg import LaserScan, Image, PointCloud2
            from tf2_msgs.msg import TFMessage
            checks = {
                '/clock': (Clock, lambda m: m.clock.sec > 0),
                '/scan': (LaserScan, lambda m: len(m.ranges) >= 10 and any(math.isfinite(r) for r in m.ranges)),
                '/odom': (Odometry, lambda m: bool(m.header.frame_id and m.child_frame_id)),
                '/tf': (TFMessage, lambda m: bool(m.transforms)),
                '/restaurant/rgbd/image': (Image, lambda m: m.width > 0 and m.height > 0 and bool(m.data)),
                '/restaurant/rgbd/depth_image': (Image, lambda m: m.width > 0 and m.height > 0 and bool(m.data)),
                '/restaurant/rgbd/points': (PointCloud2, lambda m: m.width > 0 and m.height > 0 and bool(m.data)),
            }
            received = set()
            rclpy.init(args=None)
            node = rclpy.create_node('restaurant_ci_sensor_probe')
            try:
                subscriptions = []
                for topic, (type_, valid) in checks.items():
                    def callback(message, name=topic, verifier=valid):
                        if verifier(message):
                            received.add(name)
                    subscriptions.append(node.create_subscription(type_, topic, callback, qos_profile_sensor_data))
                while time.monotonic() - start < args.wait_seconds:
                    if proc.poll() is not None:
                        raise RuntimeError(f'GAZEBO_LAUNCH_EXITED_EARLY rc={proc.returncode}')
                    rclpy.spin_once(node, timeout_sec=1.0)
                    if received == set(checks):
                        print('RESTAURANT_CI_L2_GAZEBO_SENSORS_PASS_NO_GOAL', flush=True)
                        print('ROS_TOPICS=' + ','.join(sorted(received)), flush=True)
                        return
                missing = sorted(set(checks) - received)
                raise RuntimeError('GAZEBO_SENSOR_MISSING: ' + ','.join(missing))
            finally:
                node.destroy_node()
                rclpy.shutdown()
        except Exception as exc:
            print('RESTAURANT_CI_L2_FAIL: ' + str(exc), file=sys.stderr, flush=True)
            raise
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGINT)
                try:
                    proc.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=4)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait()
            text = args.log.read_text(errors='replace') if args.log.exists() else ''
            lines = text.splitlines()
            hints = [line for line in lines if any(word in line.lower() for word in ('error', 'fatal', 'exception', 'failed', 'not found', 'warn'))]
            summary.write_text('FIRST_ERRORS_OR_WARNINGS:\n' + '\n'.join(hints[:20]) +
                               '\nLAST_60_LINES:\n' + '\n'.join(lines[-60:]) + '\n')


if __name__ == '__main__':
    main()
