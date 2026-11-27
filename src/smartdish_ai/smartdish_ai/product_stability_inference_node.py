"""Explicit Owner-only product recovery ROS adapter. Legacy node stays unchanged."""
import json
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from rcl_interfaces.msg import ParameterDescriptor, SetParametersResult
from sensor_msgs.msg import Image
from std_msgs.msg import String

from .model_runtime import load_predictor
from .product_inference import ProductInference
from .stability_inference_node import unpack_ros_rgb

THRESHOLDS = ("stable_confidence_min", "unstable_confidence_min")


class ProductStabilityInferenceNode(Node):
    def __init__(self, *, parameter_overrides=None, predictor_loader=load_predictor):
        # Same parameter service name as legacy; E launches exactly one C node.
        super().__init__("smartdish_stability_inference", parameter_overrides=parameter_overrides)
        immutable = ParameterDescriptor(read_only=True)
        self.declare_parameter("owner_gazebo_integration", False, immutable)
        self.declare_parameter("model_path", "", immutable)
        if self.get_parameter("owner_gazebo_integration").value is not True:
            raise PermissionError("C_OWNER_PRODUCT_RECOVERY_SCOPE_REQUIRED")
        self.declare_parameter(THRESHOLDS[0], 0.0)
        self.declare_parameter(THRESHOLDS[1], 0.0)
        predictor, version = None, "none"
        path = self.get_parameter("model_path").value.strip()
        if path:
            try:
                # The production entrypoint never injects a CI double. Existing
                # model_runtime performs the exact Owner checkpoint/metadata gate.
                predictor, version = predictor_loader(Path(path), owner_gazebo_integration=True)
                self.get_logger().info("C_MODEL_LOADED version=" + version + " scope=OWNER_GAZEBO_INTEGRATION_ONLY")
            except Exception as exc:
                self.get_logger().error("C_MODEL_UNAVAILABLE " + type(exc).__name__)
        else:
            self.get_logger().error("C_MODEL_UNAVAILABLE path not configured")
        self.core = ProductInference(
            predictor, version,
            stable=self.get_parameter(THRESHOLDS[0]).value,
            unstable=self.get_parameter(THRESHOLDS[1]).value)
        self.add_on_set_parameters_callback(self._parameters)
        qos = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                         reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.VOLATILE)
        self.publisher = self.create_publisher(String, "/collection/stability", qos)
        self.create_subscription(Image, "/smartdish/tray/image_raw", self._image, qos)
        self.create_subscription(String, "/collection/capture_result", self._capture, qos)
        self.create_subscription(String, "/collection/ai_check_request", self._request, qos)
        self.create_subscription(String, "/collection/status", self._status, qos)
        self.steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(0.05, self._tick, clock=self.steady)
        self.get_logger().info("C_PRODUCT_RECOVERY_READY model_available=" +
                               str(predictor is not None) + " RELIABLE VOLATILE KEEP_LAST_10")

    def _parameters(self, params):
        incoming = {p.name: p.value for p in params}
        if not incoming or not set(incoming).issubset(THRESHOLDS):
            return SetParametersResult(successful=False, reason="C_UNSUPPORTED_DYNAMIC_PARAMETER")
        old = self.core.thresholds
        try:
            values = self.core.set_thresholds(incoming.get(THRESHOLDS[0], old[0]),
                                              incoming.get(THRESHOLDS[1], old[1]))
        except ValueError as exc:
            return SetParametersResult(successful=False, reason=str(exc))
        self.get_logger().info("C_DYNAMIC_THRESHOLD_APPLIED stable=%.3f unstable=%.3f" % values)
        return SetParametersResult(successful=True)

    @staticmethod
    def _decode(msg):
        try:
            return json.loads(msg.data)
        except (ValueError, TypeError):
            return None

    def _publish(self, results):
        for result in results:
            out = String()
            out.data = json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True)
            self.publisher.publish(out)
            self.get_logger().info("C_PRODUCT_INFERENCE_RESULT=" + out.data)

    def _image(self, msg):
        now = time.monotonic()
        try:
            rgb, width, height = unpack_ros_rgb(msg)
            stamp = int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)
            if not self.core.cache_rgb(rgb, width, height, stamp, msg.header.frame_id, now):
                self.get_logger().warning("C_PRODUCT_FRAME_REJECTED")
        except (TypeError, ValueError, OverflowError) as exc:
            self.get_logger().warning("C_PRODUCT_FRAME_INVALID " + type(exc).__name__)
        self._publish(self.core.tick(time.monotonic()))

    def _capture(self, msg):
        self._publish(self.core.capture(self._decode(msg), time.monotonic()))

    def _request(self, msg):
        self._publish(self.core.request(self._decode(msg), time.monotonic()))

    def _status(self, msg):
        self.core.mission_status(self._decode(msg))

    def _tick(self):
        self._publish(self.core.tick(time.monotonic()))


def main():
    rclpy.init()
    node = None
    try:
        node = ProductStabilityInferenceNode()
        # Single threaded executor serializes threshold, capture and prediction.
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
