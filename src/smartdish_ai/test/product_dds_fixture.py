"""Real Jazzy DDS / atomic parameter service fixture; no checkpoint, no Gazebo."""
import hashlib
import json
import time
import unittest

import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from smartdish_ai.product_stability_inference_node import ProductStabilityInferenceNode

PROFILE = "OWNER_PRODUCT_RECOVERY"
RGB = bytes([1, 2, 3]) * (640 * 480)
DIGEST = hashlib.sha256(RGB).hexdigest()

class DdsTest(unittest.TestCase):
    def test_installed_adapter(self):
        rclpy.init()
        executor = SingleThreadedExecutor()
        calls, results = [], []
        nodes = []
        try:
            def fixture_loader(path, *, owner_gazebo_integration):
                self.assertTrue(owner_gazebo_integration)
                def predict(rgb, width, height):
                    calls.append(hashlib.sha256(rgb).hexdigest())
                    self.assertEqual((width, height), (640, 480))
                    return "UNSTABLE", .506081
                return predict, "CI_DOUBLE_PRODUCT_DDS"
            c = ProductStabilityInferenceNode(parameter_overrides=[
                Parameter("owner_gazebo_integration", value=True),
                Parameter("model_path", value="CI_FIXTURE_NOT_A_CHECKPOINT")],
                predictor_loader=fixture_loader)
            nodes.append(c)
            h = Node("c_product_dds_fixture")
            nodes.append(h)
            for node in nodes:
                executor.add_node(node)
            qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.VOLATILE)
            image_pub = h.create_publisher(Image, "/smartdish/tray/image_raw", qos)
            capture = h.create_publisher(String, "/collection/capture_result", qos)
            request = h.create_publisher(String, "/collection/ai_check_request", qos)
            status = h.create_publisher(String, "/collection/status", qos)
            sub = h.create_subscription(String, "/collection/stability",
                                        lambda msg: results.append(json.loads(msg.data)), qos)
            client = AsyncParameterClient(h, "/smartdish_stability_inference")
            def spin_until(predicate, timeout=10):
                end = time.monotonic() + timeout
                while not predicate():
                    self.assertLess(time.monotonic(), end, "DDS_TIMEOUT")
                    executor.spin_once(timeout_sec=.02)
            def send(pub, data):
                msg = String()
                msg.data = json.dumps(data)
                pub.publish(msg)
            def set_pair(stable, unstable):
                future = client.set_parameters_atomically([
                    Parameter("stable_confidence_min", value=stable),
                    Parameter("unstable_confidence_min", value=unstable)])
                spin_until(future.done)
                return future.result().result
            spin_until(lambda: all(p.get_subscription_count() >= 1 for p in
                                    (image_pub, capture, request, status))
                       and sub.get_publisher_count() >= 1 and client.services_are_ready())
            self.assertTrue(set_pair(0., 1.).successful)
            self.assertFalse(set_pair(0., 1.1).successful)
            fut = client.get_parameters(["stable_confidence_min", "unstable_confidence_min"])
            spin_until(fut.done)
            self.assertEqual([v.double_value for v in fut.result().values], [0., 1.])
            key = dict(schema_version=2, profile=PROFILE, request_id="dds-r", stack_id="s",
                       transfer_id="t", capture_id="c", image_stamp_ns=1000000000,
                       frame_id="smartdish_tray_optical", rgb_sha256=DIGEST)
            send(status, dict(key, state="WAIT_LOADING"))
            spin_until(lambda: c.core.active == "dds-r")
            self.assertFalse(set_pair(0., 0.).successful)
            # DDS request first, then ACK, then actual padded bgr8 frame.
            send(request, key)
            send(capture, dict(key, status="ACK", reason="", width=640, height=480,
                               encoding="bgr8", receipt_sha256="a"*64))
            image = Image()
            image.header.stamp.sec = 1
            image.header.frame_id = key["frame_id"]
            image.height, image.width, image.encoding, image.step = 480, 640, "bgr8", 1924
            image.data = (bytes([3, 2, 1]) * 640 + bytes(4)) * 480
            image_pub.publish(image)
            spin_until(lambda: len(results) == 1)
            out = results[0]
            self.assertEqual(calls, [DIGEST])
            self.assertEqual(out["rgb_sha256"], DIGEST)
            self.assertEqual(out["model_version"], "CI_DOUBLE_PRODUCT_DDS")
            self.assertTrue(out["inference_ok"])
            self.assertEqual(out["status"], "UNKNOWN")
            self.assertEqual(out["reason"], "LOW_CONFIDENCE")
            self.assertEqual(out["raw_confidence"], .506081)
            send(request, key)
            send(capture, dict(key, status="ACK", reason="", width=640, height=480,
                               encoding="bgr8", receipt_sha256="a"*64))
            end = time.monotonic() + .4
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.02)
            self.assertEqual(len(results), 1)
            self.assertEqual(len(calls), 1)
            send(status, dict(key, state="COMPLETED"))
            spin_until(lambda: c.core.active is None)
            self.assertTrue(set_pair(0., 0.).successful)
            print("C_PRODUCT_DDS_PASS predictor=CI_DOUBLE_PRODUCT_DDS rgb_sha256=" + DIGEST)
        finally:
            for node in reversed(nodes):
                executor.remove_node(node)
                node.destroy_node()
            executor.shutdown()
            if rclpy.ok():
                rclpy.shutdown()

if __name__ == "__main__":
    unittest.main()
