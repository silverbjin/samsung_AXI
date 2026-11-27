"""ROS 2 transport for the pure D MissionManager.

Only A's Navigation Adapter may originate /collection/nav_result. D never
publishes Nav2 Action feedback or /cmd_vel.
"""
import argparse
import json
import logging

from .mission_manager import ACTIVE_STATES, MissionManager
from .product_admission import approved_model_sha256, product_ai_on_authorized


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
    parser.add_argument("--owner-gazebo-integration", action="store_true",
                        help="Owner v1 Gazebo-only model, always requires staff confirmation")
    parser.add_argument("--owner-station-acceptance", action="store_true", help="Internal final acceptance, AI ON T03 10/5 only")
    args, ros_args = parser.parse_known_args(argv)
    if args.owner_station_acceptance and (not args.owner_gazebo_integration or args.ai_available!="true"):
        parser.error("Owner station acceptance requires explicit AI ON")

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
            requested_ai = args.ai_available == "true"
            allowed_ai = product_ai_on_authorized(
                requested_ai,
                owner_gazebo_integration=args.owner_gazebo_integration)
            self.owner_mode = (args.owner_gazebo_integration and allowed_ai)
            self.logic = MissionManager(
                ai_available=allowed_ai,
                approved_model_sha256=(
                    approved_model_sha256(
                        owner_gazebo_integration=args.owner_gazebo_integration)
                    if allowed_ai else None),
                owner_manual_confirm_ai=(
                    args.owner_gazebo_integration and allowed_ai))
            if allowed_ai and args.owner_gazebo_integration:
                self.get_logger().warning(
                    "E_OWNER_GAZEBO_INTEGRATION_ONLY PERFORMANCE_WAIVED "
                    "NO_AUTO_GOAL_AFTER_AI_STABLE")
            if requested_ai and not allowed_ai:
                self.get_logger().warning(
                    "AI_ON_PRODUCT_NOT_AUTHORIZED C17_MODEL_PIN_OR_E_RELEASE_MISSING")
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

        def _adapter_is_ready(self):
            """Owner L1: graph subscriber NAME, not arbitrary subscriber count.

            This is a graph-level readiness heuristic, NOT cryptographic
            DDS participant authentication or a Nav2 safety certificate.
            """
            if not self.owner_mode:
                return self.pubs["/collection/nav_goal"].get_subscription_count() >= 1
            try:
                endpoints = self.get_subscriptions_info_by_topic(
                    "/collection/nav_goal")
                return any(ep.node_name == "smartdish_navigation_adapter"
                           for ep in endpoints)
            except Exception:
                return False

        def flush(self):
            for topic, body in self.logic.drain():
                if topic == "/collection/nav_goal" and self.owner_mode:
                    if not self._adapter_is_ready():
                        self.logic.state = "ERROR"
                        self.logic.reason = "ADAPTER_DISCONNECTED_NO_GOAL"
                        self.logic.current_leg = None
                        self.logic._status()
                        # Publish the ERROR status but not a phantom Nav Goal.
                        for status_topic, status_body in self.logic.drain():
                            msg = String()
                            msg.data = json.dumps(status_body, ensure_ascii=False,
                                                  separators=(",", ":"))
                            self.pubs[status_topic].publish(msg)
                        self.get_logger().error("E_OWNER_ADAPTER_DISCONNECTED_NO_GOAL")
                        continue
                msg = String()
                msg.data = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
                self.pubs[topic].publish(msg)
                self.get_logger().info("SMARTDISH_D_EVENT topic=" + topic + " json=" + msg.data)

        def on_request(self, msg):
            body = _decode(msg.data)
            # Prevent silent loss under VOLATILE QoS if the A adapter has not
            # discovered this topic. No synthetic ACK / Nav2 result.
            if (args.owner_station_acceptance and isinstance(body,dict) and MissionManager._valid_request(body)
                    and (body.get("ai_enabled") is not True or body.get("table_wait_s")!=10 or body.get("dropoff_wait_s")!=5)):
                self.logic._error_for_request(body.get("request_id"),"OWNER_STATION_AI_ON_10_5_REQUIRED_NO_GOAL")
            elif (isinstance(body, dict) and MissionManager._valid_request(body)
                    and body.get("ai_enabled") is True
                    and not self.logic.ai_available):
                # Reject unapproved AI before checking the A Adapter. No Goal.
                self.logic.handle_request(body)
            elif (isinstance(body, dict) and MissionManager._valid_request(body)
                    and self.logic.state not in ACTIVE_STATES
                    and not self._adapter_is_ready()):
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
            body=_decode(msg.data)
            if self.logic.on_staff_confirm(body):
                self.get_logger().info("SMARTDISH_D_STAFF_CONFIRM_ACCEPTED="+json.dumps(body))
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
