"""L1 fixture-only. Real ROS DDS + Tk, NO Gazebo, NO model, NO Nav2.
A/C replies originate only from isolated CI fixture nodes; accelerated clock.
"""
import hashlib
import json
import os
import time
import tkinter as tk
from unittest.mock import patch
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.parameter_client import AsyncParameterClient
from rcl_interfaces.msg import SetParametersResult
from sensor_msgs.msg import Image
from std_msgs.msg import String
from smartdish_service.product_recovery_fsm import PROFILE
from smartdish_service.product_recovery_transport import make_recovery_node
from smartdish_service.product_recovery_ui import RecoveryView
from smartdish_service.product_recovery_thresholds import ThresholdTransaction
from smartdish_service import product_recovery_fsm

LAYOUT={"tables":{"T03":{"rect":[585,110,745,178],"enabled":True}},
        "areas":{"HOME":[40,380,290,430],"DISH_RETURN":[480,380,770,430]}}
DIGEST="f"*64
MODEL="resnet18-"+DIGEST[:12]
RGB=bytes([11,22,33])*(640*480)
RGB_SHA=hashlib.sha256(RGB).hexdigest()
STAMP=1000000101
QOS=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.VOLATILE)

def main():
    print("D_L1_DDS_FIXTURE_ONLY NO_GAZEBO NO_NAV2 NO_MODEL",flush=True)
    assert "install" in str(Path(product_recovery_fsm.__file__).resolve()), product_recovery_fsm.__file__
    assert os.environ.get("ROS_DOMAIN_ID")=="79"
    rclpy.init()
    # Only inside this isolated fixture test; deployed authorization unmodified.
    with patch("smartdish_service.product_recovery_transport.approved_model_sha256",return_value=DIGEST):
        d=make_recovery_node(owner_ai_requested=True)
    a=Node("smartdish_navigation_adapter")
    c=Node("smartdish_stability_inference")
    ui=Node("smartdish_ui")
    c.declare_parameter("stable_confidence_min",0.5)
    c.declare_parameter("unstable_confidence_min",0.5)
    def validate(params):
        return SetParametersResult(successful=all(p.type_.value==3 and 0<=p.value<=1 for p in params))
    c.add_on_set_parameters_callback(validate)
    tx=ThresholdTransaction(AsyncParameterClient(ui,"/smartdish_stability_inference"))
    root=tk.Tk()
    ex=SingleThreadedExecutor()
    for node in (a,c,d,ui): ex.add_node(node)
    clock=[0.0]
    d.logic.clock=lambda:clock[0]
    pubs={}
    for key in ("nav_result","dish_transfer_result","capture_result","nav_cancel_result"):
        pubs[key]=a.create_publisher(String,"/collection/"+key,QOS)
    pubs["stability"]=c.create_publisher(String,"/collection/stability",QOS)
    for key in ("request","staff_confirm"):
        pubs[key]=ui.create_publisher(String,"/collection/"+key,QOS)
    image_pub=a.create_publisher(Image,"/smartdish/tray/image_raw",QOS)
    def send(key,obj):
        msg=String()
        msg.data=json.dumps(obj,allow_nan=False)
        pubs[key].publish(msg)
    view=RecoveryView(root,LAYOUT,send,tx.request,True)
    goals=[]
    transfers=[]
    captures=[]
    inference=[]
    statuses=[]
    def subscribe(node,key,fn):
        node.create_subscription(String,"/collection/"+key,lambda m:fn(json.loads(m.data)),QOS)
    subscribe(a,"nav_goal",goals.append)
    subscribe(a,"dish_transfer_request",transfers.append)
    subscribe(a,"capture_request",captures.append)
    subscribe(c,"ai_check_request",inference.append)
    def status(data):
        statuses.append(data)
        view.on_status(data)
    subscribe(ui,"status",status)
    subscribe(ui,"capture_result",view.on_capture)
    def on_frame(msg):
        if view.frame_cache.add(msg): view.render_preview()
    ui.create_subscription(Image,"/smartdish/tray/image_raw",on_frame,QOS)
    def until(condition,seconds=10):
        stop=time.monotonic()+seconds
        while time.monotonic()<stop:
            ex.spin_once(timeout_sec=0.02)
            tx.poll()
            root.update()
            if condition(): return
        raise AssertionError("DDS_WAIT_TIMEOUT state="+d.logic.state+" ui="+view.state)
    def body(**kw):
        return dict(schema_version=2,profile=PROFILE,request_id=view.request_id,**kw)
    def nav(leg,identity):
        assert d.bind_accepted_goal(view.request_id,leg,identity)
        send("nav_result",body(leg=leg,goal_uuid=identity,result="SUCCEEDED",
                               terminal_status="SUCCEEDED",stop_verified=True,reason="CI_FIXTURE"))
    try:
        until(lambda:all(p.get_subscription_count()>0 for p in pubs.values() if p!=pubs["nav_cancel_result"])
              and d.adapter_ready() and tx.client.wait_for_services(timeout_sec=0.0)
              and image_pub.get_subscription_count()>0)
        assert d.arm_verified("stack-1",(0.5,0.5))
        until(lambda:view.ready)
        view.select()
        view.stable.set("0.00")
        view.unstable.set("1.00")
        view.threshold_button.invoke()
        until(lambda:view.threshold_confirmed)
        assert c.get_parameter("stable_confidence_min").value==0
        assert c.get_parameter("unstable_confidence_min").value==1
        view.start_button.invoke()
        until(lambda:len(goals)==1 and view.state=="TO_TABLE")
        assert d.logic.thresholds==(0.0,1.0)
        nav("TO_TABLE","1"*32)
        until(lambda:view.state=="WAIT_LOADING")
        clock[0]+=10
        until(lambda:len(transfers)==1 and view.state=="LOADING")
        assert len(goals)==1 and not inference
        load=transfers[0]
        send("dish_transfer_result",body(stack_id="stack-1",transfer_id=load["transfer_id"],
             operation="LOAD",status="ACK",reason="CI_FIXTURE",entity_ids=["dish-1"],
             location="ON_ROBOT",tray_count=1,table_count=0,receipt_sha256="a"*64,event_sim_ns=1000000100))
        until(lambda:len(captures)==1 and view.state=="CAPTURING")
        cap=captures[0]
        msg=Image()
        msg.header.frame_id="smartdish_tray_optical"
        msg.header.stamp.sec=1
        msg.header.stamp.nanosec=101
        msg.width=640
        msg.height=480
        msg.step=1920
        msg.encoding="rgb8"
        msg.data=RGB
        image_pub.publish(msg)
        send("capture_result",body(stack_id="stack-1",transfer_id=load["transfer_id"],
             capture_id=cap["capture_id"],status="ACK",reason="CI_FIXTURE",
             image_stamp_ns=STAMP,frame_id="smartdish_tray_optical",rgb_sha256=RGB_SHA,
             width=640,height=480,encoding="rgb8",receipt_sha256="b"*64))
        until(lambda:len(inference)==1 and view.photo is not None)
        req=inference[0]
        assert req["rgb_sha256"]==RGB_SHA and req["capture_id"]==cap["capture_id"]
        send("stability",body(stack_id="stack-1",transfer_id=load["transfer_id"],capture_id=cap["capture_id"],
             image_stamp_ns=STAMP,rgb_sha256=RGB_SHA,status="STABLE",confidence=0.2,
             model_version=MODEL,inference_ok=True,raw_status="STABLE",raw_confidence=0.2,
             reason="CI_FIXTURE",stable_confidence_min=0.0,unstable_confidence_min=1.0))
        until(lambda:view.state=="NEEDS_CONFIRMATION" and str(view.approve.cget("state"))=="normal")
        assert len(goals)==1 and str(view.threshold_button.cget("state"))=="disabled"
        view.approve.invoke()
        until(lambda:len(goals)==2 and view.state=="TO_RETURN")
        nav("TO_RETURN","2"*32)
        until(lambda:view.state=="WAIT_UNLOADING")
        clock[0]+=5
        until(lambda:len(transfers)==2 and view.state=="UNLOADING")
        assert len(goals)==2
        send("dish_transfer_result",body(stack_id="stack-1",transfer_id=transfers[1]["transfer_id"],
             operation="UNLOAD",status="ACK",reason="CI_FIXTURE",entity_ids=["dish-1"],
             location="RETURNED",tray_count=0,table_count=0,receipt_sha256="c"*64,event_sim_ns=2000000100))
        until(lambda:len(goals)==3 and view.state=="TO_HOME")
        nav("TO_HOME","3"*32)
        until(lambda:view.state=="COMPLETED")
        assert len(goals)==3 and len(inference)==1 and len(captures)==1
        print("D_L1_DDS_FIXTURE_PASS installed="+product_recovery_fsm.__file__+
              " 3_FIXTURE_GOALS 1_CAPTURE 1_INFERENCE_MESSAGE C_ATOMIC_SET_GET TK_CLICK",flush=True)
    finally:
        root.destroy()
        for node in (ui,c,a,d):
            ex.remove_node(node)
            node.destroy_node()
        ex.shutdown()
        rclpy.shutdown()

if __name__=="__main__": main()
