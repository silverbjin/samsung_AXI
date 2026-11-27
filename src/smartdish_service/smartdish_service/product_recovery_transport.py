"""D-owned ROS transport, isolated from the legacy/station manager.

E must supply verified initial READY and accepted Goal UUID via the two
in-process adapter methods; no new public topic or invented readiness.
This module is not a standalone launcher until that boundary is approved.
"""
import json
from .product_recovery_fsm import RecoveryFSM, LEGS
from .product_admission import approved_model_sha256

def make_recovery_node(*, owner_ai_requested=False):
    from rclpy.node import Node
    from rclpy.clock import Clock, ClockType
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from std_msgs.msg import String
    from rclpy.parameter_client import AsyncParameterClient

    class RecoveryNode(Node):
        def __init__(self):
            super().__init__("smartdish_mission_manager")
            digest = approved_model_sha256(owner_gazebo_integration=True) if owner_ai_requested is True else None
            self.logic=RecoveryFSM(model_version="resnet18-"+digest[:12] if digest else None)
            qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,
                           durability=DurabilityPolicy.VOLATILE)
            self.pubs={topic:self.create_publisher(String,"/collection/"+topic,qos)
                       for topic in ("status","nav_goal","dish_transfer_request","capture_request",
                                     "ai_check_request","nav_cancel_request")}
            self.subs=[]
            for topic,fn in (("request",self.request),("nav_result",self.logic.on_nav_result),
                             ("dish_transfer_result",self.logic.on_transfer),
                             ("capture_result",self.logic.on_capture),("stability",self.logic.on_stability),
                             ("staff_confirm",self.logic.on_staff),("nav_cancel_result",self.logic.on_cancel)):
                self.subs.append(self.create_subscription(String,"/collection/"+topic,self.callback(fn),qos))
            self.c=AsyncParameterClient(self,"/smartdish_stability_inference")
            self.pending=None
            self.timer=self.create_timer(0.2,self.on_timer,clock=Clock(clock_type=ClockType.STEADY_TIME))

        def callback(self,fn):
            def receive(msg):
                try:
                    d=json.loads(msg.data)
                    accepted=fn(d)
                    if accepted is True:
                        self.get_logger().info("D_PRODUCT_ACCEPT "+fn.__name__+" request_id="+str(d.get("request_id")))
                except (TypeError,ValueError,KeyError,OverflowError) as exc:
                    self.get_logger().warning("D_PRODUCT_INVALID_EVENT "+type(exc).__name__)
                self.flush()
            return receive

        def flush(self):
            for topic,body in self.logic.drain():
                key=topic.rsplit("/",1)[-1]
                msg=String()
                msg.data=json.dumps(body,allow_nan=False,separators=(",",":"))
                self.pubs[key].publish(msg)
                self.get_logger().info("D_PRODUCT_EVENT "+topic+" "+msg.data)

        def arm_verified(self,stack_id,thresholds):
            """Only call from E-approved A READY adapter after real physical check.
            Not an operator-supplied parameter or synthetic receipt."""
            result=self.logic.arm(stack_id,thresholds)
            self.flush()
            return result

        def bind_accepted_goal(self,request_id,leg,goal_uuid):
            """Only A's actual accepted UUID, with current request correlation."""
            if request_id!=self.logic.request_id:
                return False
            result=self.logic.bind_goal_uuid(leg,goal_uuid)
            self.flush()
            return result

        def request(self,d):
            if not isinstance(d,dict) or self.pending is not None or self.logic.state!="IDLE" or not self.logic.ready:
                return False
            if not any(ep.node_name=="smartdish_navigation_adapter" for ep in
                       self.get_subscriptions_info_by_topic("/collection/nav_goal")):
                self.get_logger().error("D_PRODUCT_ADAPTER_NOT_READY_NO_GOAL")
                return False
            if d.get("ai_enabled") is not True:
                return self.logic.handle_request(d)
            if not self.logic.model_version or not self.c.wait_for_services(timeout_sec=0.0):
                self.get_logger().error("D_PRODUCT_C_NOT_READY_NO_GOAL")
                return False
            # Query C at mission start; UI cannot supply the snapshot.
            f=self.c.get_parameters(["stable_confidence_min","unstable_confidence_min"])
            self.pending=(f,dict(d),self.logic.clock()+5.0)
            return False

        def on_timer(self):
            if self.pending is not None:
                f,d,deadline=self.pending
                if self.logic.clock()>=deadline:
                    self.pending=None
                    self.get_logger().error("D_PRODUCT_THRESHOLD_GET_TIMEOUT_NO_GOAL")
                elif f.done():
                    self.pending=None
                    try:
                        values=f.result().values
                        if len(values)!=2 or any(v.type!=3 for v in values):
                            raise ValueError("C_THRESHOLD_TYPE")
                        self.logic.thresholds=RecoveryFSM.validate_thresholds(tuple(v.double_value for v in values))
                        self.logic.handle_request(d)
                    except (ValueError,TypeError,AttributeError,RuntimeError) as exc:
                        self.get_logger().error("D_PRODUCT_THRESHOLD_GET_FAILED_NO_GOAL "+type(exc).__name__)
            self.logic.tick()
            self.flush()

    return RecoveryNode()
