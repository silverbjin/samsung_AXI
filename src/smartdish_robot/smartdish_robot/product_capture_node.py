"""Opt-in A capture DDS endpoint. Not launched by legacy or existing E runners.

Requires an approved upstream actual transfer receipt producer. The E/D
interface review must precede enabling; no product approval implied.
"""
import json
from pathlib import Path
import time
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock,ClockType
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from .product_contract import ContractError, FrameCache, TransactionJournal, parse_capture
from .product_capture import CaptureStore

class TrayCaptureNode(Node):
    def __init__(self, *, parameter_overrides=None):
        super().__init__("smartdish_product_tray_capture",parameter_overrides=parameter_overrides)
        self.declare_parameter("enabled",False)
        self.declare_parameter("evidence_dir","")
        if not self.get_parameter("enabled").value:
            raise RuntimeError("PRODUCT_CAPTURE_DISABLED")
        root=Path(self.get_parameter("evidence_dir").value)
        if not root.is_absolute() or not root.is_dir():
            raise RuntimeError("ACTUAL_RUN_EVIDENCE_DIR_REQUIRED")
        self.store=CaptureStore(root/"captures",TransactionJournal(root/"transfers"))
        self.cache=FrameCache()
        self.pending=None
        self.failed=False
        qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,
                       durability=DurabilityPolicy.VOLATILE)
        self.result=self.create_publisher(String,"/collection/capture_result",qos)
        self.create_subscription(String,"/collection/capture_request",self.on_request,qos)
        self.create_subscription(Image,"/smartdish/tray/image_raw",self.on_image,qos)
        self.create_timer(.05,self.tick,clock=Clock(clock_type=ClockType.STEADY_TIME))

    def publish(self,result):
        m=String();m.data=json.dumps(result,sort_keys=True,allow_nan=False)
        self.result.publish(m)

    def on_image(self,m):
        if self.failed:return
        try:
            stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
            if stamp<=0:return
            self.cache.observe(stamp,m.header.frame_id,m.width,m.height,m.encoding,m.step,m.data,time.monotonic())
        except ContractError as exc:
            self.get_logger().error("FRAME_INVALID: "+str(exc))
            if self.pending:self.finish_failure("FRAME_INVALID")
            self.failed=True

    def on_request(self,m):
        if self.failed:return
        try:
            req=parse_capture(m.data)
            if self.pending:
                if req!=self.pending[0]:
                    self.get_logger().error("CAPTURE_BUSY_OR_ID_CONFLICT")
                return
            old=self.store.reserve(req)
            if old is not None:
                self.publish(old);return
            self.pending=(req,time.monotonic()+5.)
            self.tick()
        except (ContractError,OSError,ValueError,KeyError) as exc:
            # No ACK on malformed/untrusted/no-LOAD request. D deadline must
            # hold safely; failure payload review is needed before activation.
            self.get_logger().error("CAPTURE_REJECTED_NO_ACK: "+str(exc))
            self.failed=True

    def finish_failure(self,reason):
        req,_=self.pending
        self.pending=None
        try:self.publish(self.store.fail(req,reason))
        except (ContractError,OSError,ValueError,KeyError) as exc:
            self.get_logger().error("CAPTURE_FAILURE_RECEIPT_NOT_COMMITTED: "+str(exc))
        self.failed=True

    def tick(self):
        if self.failed or self.pending is None:return
        req,deadline=self.pending
        now=time.monotonic()
        if now>=deadline:
            self.finish_failure("CAMERA_TIMEOUT");return
        try:
            frame=self.cache.select(req["min_sim_stamp_ns"],now)
            if frame is None:return
            if time.monotonic()>=deadline:
                self.finish_failure("CAMERA_TIMEOUT");return
            result=self.store.complete(req,frame,time.monotonic())
            # Disk commit must precede ACK. Late commit is retained but no
            # publication; D times out safely. Never substitute a newer frame.
            self.pending=None
            if time.monotonic()>=deadline:
                self.get_logger().error("CAPTURE_RECEIPT_LATE_NO_ACK")
                self.failed=True;return
            self.publish(result)
        except (ContractError,OSError,ValueError,KeyError) as exc:
            self.get_logger().error("CAPTURE_FRAME_OR_RECEIPT_INVALID: "+str(exc))
            if self.pending:self.finish_failure("FRAME_INVALID")

def main(args=None):
    rclpy.init(args=args)
    node=None
    try:
        node=TrayCaptureNode()
        rclpy.spin(node)
    finally:
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()

if __name__=="__main__":main()
