#!/usr/bin/env python3
"""C08 real ROS 2 Jazzy *transport* smoke; no model/Goal/Gazebo.

Run after colcon building smartdish_ai in an isolated ROS_DOMAIN_ID.
Missing checkpoint MUST yield UNKNOWN. A synthetic camera frame and ROS
request prove DDS topic wiring, QoS discovery and duplicate suppression,
not physical image quality or trained model performance.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy, qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import String


QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                 reliability=ReliabilityPolicy.RELIABLE,
                 durability=DurabilityPolicy.VOLATILE)


def pump_until(node: Node, condition, seconds: float, description: str):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if condition():
            return
    raise AssertionError(f'C08_TIMEOUT_{description}')


def main():
    log_file = Path(tempfile.gettempdir()) / f'smartdish-c08-ros-{os.getpid()}.log'
    with log_file.open('w', encoding='utf-8') as log:
        process = subprocess.Popen(
            ['ros2', 'run', 'smartdish_ai', 'stability_inference_node'],
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        node = None
        try:
            rclpy.init()
            node = Node('smartdish_c08_ros_transport_probe')
            image_pub = node.create_publisher(Image, '/smartdish/tray/image_raw', qos_profile_sensor_data)
            request_pub = node.create_publisher(String, '/collection/ai_check_request', QOS)
            replies = []
            node.create_subscription(String, '/collection/stability',
                                     lambda x: replies.append(json.loads(x.data)), QOS)
            pump_until(node, lambda: process.poll() is not None or (
                image_pub.get_subscription_count() > 0 and
                request_pub.get_subscription_count() > 0 and
                node.count_publishers('/collection/stability') > 0),
                30, 'DISCOVERY')
            if process.poll() is not None:
                raise AssertionError(f'C08_NODE_EXIT_{process.returncode}')

            image = Image()
            image.header.stamp = node.get_clock().now().to_msg()
            image.width, image.height = 16, 16
            image.encoding, image.is_bigendian = 'bgr8', 0
            image.step = 16 * 3 + 4  # padding exercises real ROS Image decoding
            image.data = (bytes((10, 30, 80)) * 16 + b'\x00' * 4) * 16
            image_pub.publish(image)
            rclpy.spin_once(node, timeout_sec=0.2)

            def request(req_id, capture_id):
                msg = String()
                msg.data = json.dumps({'request_id': req_id, 'capture_id': capture_id})
                request_pub.publish(msg)

            request('C08-REQ-1', 'C08-CAP-1')
            pump_until(node, lambda: len(replies) >= 1, 10, 'FIRST_REPLY')
            expected = {'request_id': 'C08-REQ-1', 'capture_id': 'C08-CAP-1',
                        'status': 'UNKNOWN', 'confidence': None,
                        'model_version': 'none'}
            assert replies[0] == expected, f'C08_UNEXPECTED_REPLY {replies}'
            request('C08-REQ-1', 'C08-CAP-1')  # same key must not emit again
            for _ in range(6):
                rclpy.spin_once(node, timeout_sec=0.1)
            assert len(replies) == 1, f'C08_DUPLICATE_RESPONSE {replies}'
            request('C08-REQ-1', 'C08-CAP-2')
            pump_until(node, lambda: len(replies) >= 2, 10, 'SECOND_REPLY')
            assert replies[1] == dict(expected, capture_id='C08-CAP-2')
            assert len(replies) == 2
            # No model means UNKNOWN even if a valid real DDS frame arrived.
            print('C08_REAL_ROS2_JAZZY_NO_MODEL_UNKNOWN_TRANSPORT_PASS '
                  'responses=2 duplicates=0 protocol=RELIABLE_VOLATILE_KEEP_LAST_10 '
                  'real_gazebo=NOT_RUN model_training=NOT_RUN', flush=True)
        finally:
            if node is not None:
                node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
            print(f'C08_NODE_LOG={log_file}', flush=True)


if __name__ == '__main__':
    main()
