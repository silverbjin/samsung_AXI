#!/usr/bin/env python3
"""Actual Jazzy DDS parameter/runtime check; NO private weights or Nav2.

Uses existing C and D nodes; absence of A subscriber blocks initial request.
This tests the Owner admission boundary but does NOT simulate robot success.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.parameter_client import AsyncParameterClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from std_msgs.msg import String

QOS = QoSProfile(history=HistoryPolicy.KEEP_LAST, depth=10,
                 reliability=ReliabilityPolicy.RELIABLE,
                 durability=DurabilityPolicy.VOLATILE)

def wait(node, seconds, procs=()):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        for proc,_ in procs:
            if proc.poll() is not None:
                raise RuntimeError("E_OWNER_AION_NODE_EARLY_EXIT_"+str(proc.returncode))
        rclpy.spin_once(node, timeout_sec=0.05)

def done(node, future, timeout=5):
    deadline=time.monotonic()+timeout
    while not future.done() and time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=0.05)
    if not future.done():
        raise RuntimeError("E_OWNER_AION_DDS_ACK_TIMEOUT")
    return future.result()

def main():
    rclpy.init()
    checker=Node("smartdish_e_owner_ai_integration_no_nav2_probe")
    status=[]
    goals=[]
    checker.create_subscription(String,"/collection/status",
        lambda m: status.append(json.loads(m.data)),QOS)
    checker.create_subscription(String,"/collection/nav_goal",
        lambda m: goals.append(json.loads(m.data)),QOS)
    requests=checker.create_publisher(String,"/collection/request",QOS)
    params=AsyncParameterClient(checker,"/smartdish_stability_inference")
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
    processes=[]
    try:
        with tempfile.TemporaryDirectory(prefix="smartdish_e_aion_ci_") as temp:
            cmds=[
              [sys.executable,"-m","smartdish_ai.stability_inference_node",
               "--ros-args","-p","owner_gazebo_integration:=true"],
              [sys.executable,"-m","smartdish_service.manager_node",
               "--ai-available","true","--owner-gazebo-integration"]
            ]
            for idx,cmd in enumerate(cmds):
                path=os.path.join(temp,f"node{idx}.log")
                with open(path,"w") as log:
                    proc=subprocess.Popen(cmd,env=env,stdout=log,
                        stderr=subprocess.STDOUT,start_new_session=True)
                processes.append((proc,path))
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                wait(checker,0.1,processes)
                if (params.wait_for_services(timeout_sec=0.0) and
                        requests.get_subscription_count()>=1):
                    break
            else:
                raise RuntimeError("E_OWNER_AION_DDS_DISCOVERY_TIMEOUT")
            vals=done(checker,params.get_parameters(
                ["stable_confidence_min","unstable_confidence_min"]))
            assert [v.double_value for v in vals.values]==[.80,.80],vals

            result=done(checker,params.set_parameters_atomically([
                Parameter("stable_confidence_min",value=.65),
                Parameter("unstable_confidence_min",value=.90)]))
            assert result.result.successful,result
            vals=done(checker,params.get_parameters(
                ["stable_confidence_min","unstable_confidence_min"]))
            assert [v.double_value for v in vals.values]==[.65,.90],vals
            print("E_OWNER_C_RUNTIME_THRESHOLDS_APPLIED stable=.65 unstable=.90",flush=True)

            rejected=done(checker,params.set_parameters_atomically([
                Parameter("stable_confidence_min",value=.49),
                Parameter("unstable_confidence_min",value=.80)]))
            assert not rejected.result.successful,rejected
            vals=done(checker,params.get_parameters(
                ["stable_confidence_min","unstable_confidence_min"]))
            assert [v.double_value for v in vals.values]==[.65,.90],vals
            print("E_OWNER_C_INVALID_THRESHOLD_REJECTED_ATOMIC",flush=True)

            # Explicit Owner D admission should pass product gate but not
            # send a Goal when actual A Adapter is absent.
            msg=String()
            msg.data=json.dumps(dict(request_id="E-AION-L1-01",table_id="T03",
                table_wait_s=10,dropoff_wait_s=5,ai_enabled=True))
            requests.publish(msg)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                wait(checker,0.1,processes)
                if any(s.get("request_id")=="E-AION-L1-01" for s in status):
                    break
            matched=[s for s in status if s.get("request_id")=="E-AION-L1-01"]
            assert matched, status
            assert matched[-1].get("reason")=="ADAPTER_NOT_READY_NO_GOAL",matched
            assert goals==[],goals
            print("E_OWNER_D_ADMISSION_APPROVED_BUT_A_ABSENT_NO_GOAL",flush=True)
    except Exception:
        for _,path in processes:
            try:
                print("E_OWNER_AION_NODE_LOG="+open(path).read()[-1800:],flush=True)
            except OSError:
                pass
        raise
    finally:
        for proc,_ in processes:
            if proc.poll() is None: proc.terminate()
        for proc,_ in processes:
            try: proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        checker.destroy_node()
        if rclpy.ok():rclpy.shutdown()

if __name__=="__main__":
    main()
