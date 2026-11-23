"""ROS 2 transport for the pure D MissionManager.

Only A's Navigation Adapter may originate /collection/nav_result. D never
publishes Nav2 Action feedback or /cmd_vel.
"""
import argparse
import json
import logging

from .mission_manager import ACTIVE_STATES, MissionManager


def _decode(data):
    try:
        value = json.loads(data)
        return value if isinstance(value, dict) else None
    except (ValueError, TypeError):
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="SmartDish ROS 2 Mission Manager")
    parser.add_argument("--ai-available", choices=("true", "false"), default="false",
                        help="Explicit enable only after C inference and camera verified")
    args, ros_args = parser.parse_known_args(argv)

    import rclpy
    from rclpy.node import Node
    from rclpy.clock import Clock, ClockType
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
    from std_msgs.msg import String

    qos = QoSProfile(
        history=HistoryPolicy.KEEP_LAST, depth=10,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.VOLATILE,
    )

    class CollectionNode(Node):
        def __init__(self):
            super().__init__("smartdish_mission_manager")
            self.logic = MissionManager(ai_available=args.ai_available == "true")
            self.pubs = {
                topic: self.create_publisher(String, topic, qos)
                for topic in ("/collection/nav_goal", "/collection/status",
                              "/collection/ai_check_request")
            }
            self.create_subscription(String, "/collection/request", self.on_request, qos)
            self.create_subscription(String, "/collection/nav_result", self.on_nav_result, qos)
            self.create_subscription(String, "/collection/stability", self.on_stability, qos)
            self.create_subscription(String, "/collection/staff_confirm", self.on_staff, qos)
            # Callback scheduling and deadline arithmetic must both use
            # real monotonic time, even when /use_sim_time is enabled.
            self.create_timer(0.2, self.on_timer,
                              clock=Clock(clock_type=ClockType.STEADY_TIME))
            self.get_logger().info(
                "SMARTDISH_D_MANAGER_READY AI_AVAILABLE=" + args.ai_available +
                " NAV_SUBSCRIBERS=" + str(self.pubs["/collection/nav_goal"].get_subscription_count())
            )

        def flush(self):
            for topic, body in self.logic.drain():
                msg = String()
                msg.data = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                self.pubs[topic].publish(msg)
                self.get_logger().info("SMARTDISH_D_EVENT topic=" + topic + " json=" + msg.data)

        def on_request(self, msg):
            body = _decode(msg.data)
            # Prevent silent loss under VOLATILE QoS if the A adapter has not
            # discovered this topic. No synthetic ACK / Nav2 result.
            if (isinstance(body, dict) and MissionManager._valid_request(body)
                    and self.logic.state not in ACTIVE_STATES
                    and self.pubs["/collection/nav_goal"].get_subscription_count() < 1):
                self.logic._error_for_request(body.get("request_id"), "ADAPTER_NOT_READY_NO_GOAL")
            else:
                self.logic.handle_request(body)
            self.flush()

        def on_nav_result(self, msg):
            self.logic.on_nav_result(_decode(msg.data))
            self.flush()

        def on_stability(self, msg):
            self.logic.on_stability(_decode(msg.data))
            self.flush()

        def on_staff(self, msg):
            self.logic.on_staff_confirm(_decode(msg.data))
            self.flush()

        def on_timer(self):
            self.logic.tick()
            self.flush()

    rclpy.init(args=ros_args)
    node = CollectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("SMARTDISH_D_STOPPED_BY_OPERATOR")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
