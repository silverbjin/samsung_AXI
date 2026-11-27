#!/usr/bin/env python3
"""C ROS2 adapter: one fresh tray image + AI request => one correlated JSON result.

Optional AI ON only. Missing camera/model => UNKNOWN, never navigates or sends cmd_vel.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .inference_core import InferenceCore
from .model_runtime import load_predictor


def unpack_ros_rgb(msg):
    """Accept rgb8/bgr8 with padded step; reject unsupported/corrupt images."""
    import numpy as np
    if msg.encoding not in ("rgb8", "bgr8"):
        raise ValueError("C_UNSUPPORTED_IMAGE_ENCODING")
    width, height, step = int(msg.width), int(msg.height), int(msg.step)
    if width < 16 or height < 16 or width > 4096 or height > 4096 or step < width * 3:
        raise ValueError("C_INVALID_IMAGE_DIMENSIONS")
    if len(msg.data) != step * height:
        raise ValueError("C_INVALID_IMAGE_BUFFER")
    frame = np.frombuffer(bytes(msg.data), dtype=np.uint8).reshape(height, step)
    rgb = frame[:, :width * 3].reshape(height, width, 3)
    if msg.encoding == "bgr8":
        rgb = rgb[:, :, ::-1]
    return rgb.tobytes(), width, height


def main():
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy, qos_profile_sensor_data
    from sensor_msgs.msg import Image
    from std_msgs.msg import String
    from rcl_interfaces.msg import SetParametersResult

    class StabilityInferenceNode(Node):
        def __init__(self):
            super().__init__("smartdish_stability_inference")
            self.declare_parameter("model_path", "")
            self.declare_parameter("owner_gazebo_integration", False)
            self.declare_parameter("confidence_min", 0.80)
            self.declare_parameter("stable_confidence_min", 0.80)
            self.declare_parameter("unstable_confidence_min", 0.80)
            self.declare_parameter("max_image_age_s", 2.0)
            model_path = str(self.get_parameter("model_path").value).strip()
            predictor, version = None, "none"
            if model_path:
                try:
                    owner_scope = self.get_parameter("owner_gazebo_integration").value
                    predictor, version = load_predictor(
                        Path(model_path), owner_gazebo_integration=owner_scope is True)
                    self.get_logger().info(
                        "C_MODEL_LOADED version=%s scope=%s" %
                        (version, "OWNER_GAZEBO_INTEGRATION_ONLY" if owner_scope
                         else "PRODUCT"))
                except Exception as exc:
                    self.get_logger().error(f"C_MODEL_UNAVAILABLE {type(exc).__name__}: {exc}")
            else:
                self.get_logger().warn("C_MODEL_UNAVAILABLE path not configured; safe UNKNOWN mode")
            self.core = InferenceCore(
                predictor, version,
                float(self.get_parameter("confidence_min").value),
                float(self.get_parameter("max_image_age_s").value),
                stable_confidence_min=self.get_parameter("stable_confidence_min").value,
                unstable_confidence_min=self.get_parameter("unstable_confidence_min").value)
            self.add_on_set_parameters_callback(self.on_threshold_parameters)
            contract_qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                                      reliability=ReliabilityPolicy.RELIABLE,
                                      durability=DurabilityPolicy.VOLATILE)
            self.publisher = self.create_publisher(String, "/collection/stability", contract_qos)
            self.create_subscription(String, "/collection/ai_check_request", self.request_callback, contract_qos)
            self.create_subscription(Image, "/smartdish/tray/image_raw", self.image_callback, qos_profile_sensor_data)
            self.get_logger().info("C_STABILITY_READY optional AI ON; JSON RELIABLE VOLATILE KEEP_LAST_10")

        def on_threshold_parameters(self, params):
            """Atomic ROS 2 parameter update, without restart/retraining."""
            incoming = {p.name: p.value for p in params}
            watched = {"stable_confidence_min", "unstable_confidence_min"}
            if not watched.intersection(incoming):
                return SetParametersResult(successful=True)
            stable = incoming.get("stable_confidence_min",
                                  self.core.stable_confidence_min)
            unstable = incoming.get("unstable_confidence_min",
                                    self.core.unstable_confidence_min)
            try:
                self.core.set_decision_thresholds(stable, unstable)
            except ValueError as exc:
                self.get_logger().warning(str(exc))
                return SetParametersResult(successful=False, reason=str(exc))
            self.get_logger().info(
                "C_DYNAMIC_THRESHOLD_APPLIED stable=%.3f unstable=%.3f" %
                self.core.decision_thresholds())
            return SetParametersResult(successful=True)

        def image_callback(self, msg):
            try:
                rgb, width, height = unpack_ros_rgb(msg)
                stamp = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
                # No ROS timestamp: use receipt-age TTL; nonzero stamp rejects replay.
                accepted = self.core.cache_rgb(rgb, width, height,
                                               received_at=time.monotonic(),
                                               stamp_ns=stamp if stamp else None)
                if not accepted:
                    self.get_logger().warn("C_FRAME_REJECTED_DUPLICATE_OR_INVALID")
            except Exception as exc:
                self.get_logger().warn(f"C_FRAME_REJECTED {type(exc).__name__}: {exc}")

        def request_callback(self, msg):
            result = self.core.handle_request(msg.data)
            if result is None:
                self.get_logger().warn("C_REQUEST_INVALID_OR_DUPLICATE")
                return
            out = String()
            out.data = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
            self.publisher.publish(out)
            self.get_logger().info(
                "C_STABILITY_RESULT request_id=%s capture_id=%s status=%s model_version=%s "
                "stable_min=%.3f unstable_min=%.3f" %
                (result["request_id"], result["capture_id"], result["status"],
                 result["model_version"], *self.core.decision_thresholds()))

    rclpy.init()
    node = StabilityInferenceNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
