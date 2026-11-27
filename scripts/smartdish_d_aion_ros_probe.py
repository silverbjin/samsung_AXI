#!/usr/bin/env python3
"""Real ROS Jazzy DDS smoke; synthetic requests and NO physical/Navigation Goals.

Runs two existing ROS nodes: D Manager with --ai-available true (denied by
product gate) and C inference with NO model. A/Nav2/Gazebo never start.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, HistoryPolicy, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String

QOS = QoSProfile(
    history=HistoryPolicy.KEEP_LAST, depth=10,
    reliability=ReliabilityPolicy.RELIABLE,
    durability=DurabilityPolicy.VOLATILE)

def main():
    env=dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"]="1"
    # D manager may be given CLI true but MUST reject without E/C release.
    cmds=[
        [sys.executable,"-m","smartdish_service.manager_node","--ai-available","true"],
        [sys.executable,"-m","smartdish_ai.stability_inference_node"],
    ]
    processes=[]
    rclpy.init()
    node=Node("smartdish_d_aion_contract_probe_no_goal")
    statuses=[]
    goals=[]
    answers=[]
    node.create_subscription(String,"/collection/status",
                             lambda m: statuses.append(json.loads(m.data)),QOS)
    node.create_subscription(String,"/collection/nav_goal",
                             lambda m: goals.append(json.loads(m.data)),QOS)
    node.create_subscription(String,"/collection/stability",
                             lambda m: answers.append(json.loads(m.data)),QOS)
    pub_req=node.create_publisher(String,"/collection/request",QOS)
    pub_check=node.create_publisher(String,"/collection/ai_check_request",QOS)
    def tick(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            for p,_ in processes:
                if p.poll() is not None:
                    raise RuntimeError("AION_ROS_NODE_EXIT_EARLY")
            rclpy.spin_once(node,timeout_sec=0.05)
    try:
        with tempfile.TemporaryDirectory(prefix="smartdish_d_aion_logs_") as tmp:
            for index,cmd in enumerate(cmds):
                dest=open(os.path.join(tmp,f"node_{index}.log"),"w")
                proc=subprocess.Popen(cmd,env=env,stdout=dest,
                                      stderr=subprocess.STDOUT,start_new_session=True)
                dest.close()
                processes.append((proc,os.path.join(tmp,f"node_{index}.log")))
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                tick(0.1)
                if pub_req.get_subscription_count()>0 and pub_check.get_subscription_count()>0:
                    break
            else:
                raise RuntimeError("D_AION_DDS_DISCOVERY_TIMEOUT")

            def send(pub,payload):
                msg=String()
                msg.data=json.dumps(payload,separators=(",",":"))
                pub.publish(msg)
            req={"request_id":"D-AION-DDS-001","table_id":"T03",
                 "table_wait_s":10,"dropoff_wait_s":5,"ai_enabled":True}
            send(pub_req,req)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and not any(
                x.get("request_id")==req["request_id"] and
                x.get("reason")=="AI_NOT_AVAILABLE" for x in statuses):
                tick(0.1)
            assert any(x.get("reason")=="AI_NOT_AVAILABLE" for x in statuses),statuses
            assert not goals,goals
            print("D_AION_L1_D_MANAGER_CLI_TRUE_DENIED_NO_GOAL",flush=True)

            # Send a SYNTHETIC AI CHECK straight to C. D does not emit this
            # request: its live product gate is closed. No image or model loaded.
            check={"request_id":"D-AION-DDS-002","capture_id":"D-AION-DDS-002-AI-1"}
            send(pub_check,check)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline and not any(
                x.get("request_id")==check["request_id"] for x in answers):
                tick(0.1)
            found=[x for x in answers if x.get("request_id")==check["request_id"]]
            assert len(found)==1,found
            assert found[0]=={**check,"status":"UNKNOWN",
                              "confidence":None,"model_version":"none"},found
            send(pub_check,check)
            tick(0.5)
            assert len([x for x in answers if x.get("request_id")==check["request_id"]])==1
            assert not goals,goals
            print("D_AION_L1_C_MODEL_LESS_UNKNOWN_DUPLICATE_PASS_NO_GOAL",flush=True)
    except Exception:
        for _,logpath in processes:
            try:
                with open(logpath) as stream:
                    print("AION_NODE_LOG_TAIL="+stream.read()[-1800:],flush=True)
            except OSError:
                pass
        raise
    finally:
        for p,_ in processes:
            if p.poll() is None:
                p.terminate()
        for p,_ in processes:
            try:
                p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=2)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__=="__main__":
    main()
