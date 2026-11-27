#!/usr/bin/env python3
"""L1 actual DDS fixture only: no Gazebo, no Nav2 navigation, no product PASS."""
import hashlib,json,os,tempfile,time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.executors import MultiThreadedExecutor
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.action import ActionServer,ActionClient,CancelResponse
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from nav2_msgs.action import NavigateToPose
from std_msgs.msg import String
from sensor_msgs.msg import Image
from smartdish_robot.product_capture_node import TrayCaptureNode
from smartdish_robot.product_capture import CaptureStore
from smartdish_robot.product_contract import PROFILE,StopMonitor
from smartdish_robot.product_navigation import NavigationBoundary
import threading

REQ=dict(schema_version=2,profile=PROFILE,request_id="ci-fixture",leg="TO_TABLE",destination_id="T03")
CAP=dict(schema_version=2,profile=PROFILE,request_id="ci-fixture",stack_id="fixture:T03",
         transfer_id="fixture-load",capture_id="fixture-capture",min_sim_stamp_ns=100)
class FixtureLoad:
    def load_receipt(self,request_id,stack_id,transfer_id):
        assert (request_id,stack_id,transfer_id)==tuple(CAP[k] for k in ("request_id","stack_id","transfer_id"))
        return {"event_sim_ns":100,"receipt_sha256":"a"*64},{"kind":"DDS_FIXTURE_NO_NAV2"}

def wait(check,timeout=12):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        if check():return
        time.sleep(.03)
    raise RuntimeError("DDS_TIMEOUT")

def main():
    assert os.environ.get("CI")=="true" and os.environ.get("GITHUB_ACTIONS")=="true"
    rclpy.init()
    nodes=[];executor=MultiThreadedExecutor(num_threads=4);thread=None
    out=Path("generated/a_product_dds");out.mkdir(parents=True,exist_ok=True)
    try:
        server=Node("a_fixture_action_server");client_node=Node("a_fixture_action_client")
        io=Node("a_fixture_dds_io")
        nodes.extend((server,client_node,io))
        received_cancel=[];accepted=[];events=[]
        def execute(handle):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                if handle.is_cancel_requested:
                    received_cancel.append(bytes(handle.goal_id.uuid).hex())
                    handle.canceled();return NavigateToPose.Result()
                time.sleep(.03)
            handle.abort();return NavigateToPose.Result()
        action_server=ActionServer(server,NavigateToPose,"/a_fixture_navigate",
            execute_callback=execute,cancel_callback=lambda _:CancelResponse.ACCEPT,
            callback_group=ReentrantCallbackGroup())
        action_client=ActionClient(client_node,NavigateToPose,"/a_fixture_navigate")
        stop=StopMonitor()
        nav=NavigationBoundary(action_client,lambda _:NavigateToPose.Goal(),stop,
            lambda *a:accepted.append(a) or True,lambda d:events.append(("nav",d)),
            lambda d:events.append(("cancel",d)),preflight=lambda:True,arrival_verified=lambda _:False)
        with tempfile.TemporaryDirectory() as td:
            cap=TrayCaptureNode(parameter_overrides=[Parameter("enabled",value=True),Parameter("evidence_dir",value=td)])
            nodes.append(cap)
            # Isolated test-only replacement; production store requires actual LOAD journal.
            cap.store=CaptureStore(Path(td)/"fixture_capture",FixtureLoad())
            qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)
            pub=io.create_publisher(String,"/collection/capture_request",qos)
            img=io.create_publisher(Image,"/smartdish/tray/image_raw",qos)
            results=[]
            sub=io.create_subscription(String,"/collection/capture_result",lambda m:results.append(json.loads(m.data)),qos)
            for n in nodes:executor.add_node(n)
            thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
            wait(lambda:action_client.server_is_ready() and pub.get_subscription_count()==1 and img.get_subscription_count()==1 and io.count_publishers("/collection/capture_result")==1)
            nav.start(REQ)
            until=time.monotonic()+8
            while not accepted and time.monotonic()<until:
                nav.tick();time.sleep(.03)
            assert accepted
            uuid=accepted[0][-1];assert len(uuid)==32
            nav.cancel(dict(REQ,goal_uuid=uuid))
            until=time.monotonic()+10
            while not events and time.monotonic()<until:
                now=time.monotonic();stop.observe(time.monotonic_ns(),now,0.,0.)
                nav.tick();time.sleep(.08)
            assert events and events[0][0]=="cancel",events
            ack=events[0][1]
            assert ack["status"]=="ACK" and ack["terminal_status"]=="CANCELED" and ack["stop_verified"] is True
            assert ack["goal_uuid"]==uuid and received_cancel==[uuid] and nav.locked
            m=String();m.data=json.dumps(CAP);pub.publish(m)
            time.sleep(.15)
            raw=bytes([40,50,60])*(640*480)
            frame=Image();frame.header.frame_id="smartdish_tray_optical";frame.header.stamp.nanosec=101
            frame.width=640;frame.height=480;frame.encoding="rgb8";frame.step=1920;frame.data=raw
            img.publish(frame);wait(lambda:len(results)==1)
            assert results[0]["status"]=="ACK" and results[0]["image_stamp_ns"]==101
            assert results[0]["rgb_sha256"]==hashlib.sha256(raw).hexdigest()
            pub.publish(m);wait(lambda:len(results)==2)
            assert results[0]==results[1]
            (out/"evidence.json").write_text(json.dumps({"scope":"ACTUAL_DDS_FIXTURE_NO_GAZEBO_NO_NAV2",
                "source_sha":os.environ.get("SOURCE_SHA"),"actual_action_uuid":uuid,
                "cancel_ack":ack,"fixture_capture_ack":results[0],"exact_duplicate":True},indent=2,sort_keys=True))
            print("A_PRODUCT_DDS_FIXTURE_PASS_NO_NAV2_NO_GAZEBO")
    finally:
        executor.shutdown(timeout_sec=5)
        if thread:thread.join(timeout=5)
        for n in reversed(nodes):n.destroy_node()
        if rclpy.ok():rclpy.shutdown()
if __name__=="__main__":main()
