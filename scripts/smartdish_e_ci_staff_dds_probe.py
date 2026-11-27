#!/usr/bin/env python3
"""CI-only real D ROS DDS contract with explicitly synthetic A/C fixtures.
No Nav2 server, actual robot, private weights or product model authorization.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

FIXTURE_SHA=hashlib.sha256(b"SMARTDISH_E_CI_ONLY_DDS_MODEL_ID_V1").hexdigest()
FIXTURE_VERSION="resnet18-"+FIXTURE_SHA[:12]
CHILD="""
import os
from smartdish_service import manager_node as node
from smartdish_service.product_admission import product_ai_on_authorized
assert os.environ['GITHUB_ACTIONS']=='true' and os.environ['ROS_DOMAIN_ID']=='190'
assert not product_ai_on_authorized(True)
original=node.approved_model_sha256
def fixture(*,owner_gazebo_integration=False):
    if owner_gazebo_integration is True:
        return os.environ['E_CI_FIXTURE_SHA']
    return original(owner_gazebo_integration=False)
node.approved_model_sha256=fixture
node.main()
"""
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pin",required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    if os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("ROS_DOMAIN_ID")!="190" or os.environ.get("WSL_DISTRO_NAME"):
        raise RuntimeError("E_R3C_ISOLATED_CI_ONLY")
    assert args.pin==os.environ["GITHUB_SHA"]
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    result={"source_sha":args.pin,"scope":"REAL_D_DDS_SYNTHETIC_A_C_CONTRACT_ONLY",
            "private_model_loaded":False,"actual_nav2":False,"test4_opened":False,
            "fixture_model_version":FIXTURE_VERSION,"verdict":"FAIL","events":[],"cases":[]}
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String
    proc=node=None
    try:
        rclpy.init()
        # Exact adapter name is needed by D graph heuristic. This CI-only
        # fixture does not implement Nav2 or publish velocity/action commands.
        node=Node("smartdish_navigation_adapter")
        def receive(topic):
            def cb(msg):
                result["events"].append({"topic":topic,"data":json.loads(msg.data),"t":time.monotonic()})
            return cb
        for topic in ("nav_goal","status","ai_check_request"):
            node.create_subscription(String,"/collection/"+topic,receive(topic),10)
        pubs={k:node.create_publisher(String,"/collection/"+k,10)
              for k in ("request","nav_result","stability","staff_confirm")}
        with (out/"d_node.log").open("w") as log:
            proc=subprocess.Popen([sys.executable,"-u","-c",CHILD,
                "--ai-available","true","--owner-gazebo-integration"],
                env={**os.environ,"E_CI_FIXTURE_SHA":FIXTURE_SHA},stdout=log,
                stderr=subprocess.STDOUT,start_new_session=True)
            def spin(seconds=.05):
                until=time.monotonic()+seconds
                while time.monotonic()<until:
                    if proc.poll() is not None:
                        raise RuntimeError("E_R3C_D_EARLY_EXIT")
                    rclpy.spin_once(node,timeout_sec=.05)
            def wait(check,seconds=8,label="EVENT"):
                end=time.monotonic()+seconds
                while time.monotonic()<end:
                    spin()
                    v=check()
                    if v:return v
                raise RuntimeError("E_R3C_TIMEOUT_"+label)
            def publish(topic,body):
                result["events"].append({"topic":"fixture/"+topic,"data":body,"t":time.monotonic()})
                pubs[topic].publish(String(data=json.dumps(body)))
            def rows(rid,topic):
                return [x for x in result["events"] if x["topic"]==topic and x["data"].get("request_id")==rid]
            def state(rid,name,reason=None):
                return next((x for x in reversed(rows(rid,"status"))
                             if x["data"]["state"]==name and (reason is None or x["data"]["reason"]==reason)),None)
            def goal(rid,leg):
                return next((x for x in rows(rid,"nav_goal") if x["data"]["leg"]==leg),None)
            def nav_result(rid,leg):
                publish("nav_result",{"request_id":rid,"leg":leg,"result":"SUCCEEDED","reason":""})
            def confirm(rid,action):
                publish("staff_confirm",{"request_id":rid,"action":action})
            def stability(rid,capture,status,confidence,version=FIXTURE_VERSION):
                publish("stability",{"request_id":rid,"capture_id":capture,"status":status,
                                     "confidence":confidence,"model_version":version})
            wait(lambda:all(p.get_subscription_count()==1 for p in pubs.values())
                 and node.count_publishers("/collection/nav_goal")==1
                 and node.count_publishers("/collection/status")==1
                 and node.count_publishers("/collection/ai_check_request")==1,20,"DDS")
            for rid,kind,action in (("E-CI-STAFF-01","STABLE","APPROVE_CONTINUE"),
                                    ("E-CI-STAFF-02","STABLE","ABORT"),
                                    ("E-CI-STAFF-03","UNSTABLE","ABORT"),
                                    ("E-CI-STAFF-04","UNKNOWN","ABORT"),
                                    ("E-CI-STAFF-05","TIMEOUT","ABORT")):
                publish("request",{"request_id":rid,"table_id":"T03","table_wait_s":1,
                                   "dropoff_wait_s":1,"ai_enabled":True})
                wait(lambda:goal(rid,"TO_TABLE"),label="TO_TABLE")
                nav_result(rid,"TO_TABLE")
                wait(lambda:state(rid,"WAIT_LOADING"),label="WAIT_LOADING")
                capture=wait(lambda:rows(rid,"ai_check_request"),label="AI_CHECK")[0]["data"]["capture_id"]
                # Ignore mismatched capture before valid/timeout case.
                stability(rid,capture+"-wrong","STABLE",.99)
                spin(.3)
                assert not state(rid,"NEEDS_CONFIRMATION") and len(rows(rid,"nav_goal"))==1
                if kind=="TIMEOUT":
                    stability(rid,capture,"STABLE",.99,"resnet18-unapproved")
                    reason="AI_TIMEOUT"
                else:
                    stability(rid,capture,kind,None if kind=="UNKNOWN" else .95)
                    reason="AI_STABLE_STAFF_CONFIRM_REQUIRED" if kind=="STABLE" else "AI_"+kind
                wait(lambda:state(rid,"NEEDS_CONFIRMATION",reason),8,"CONFIRM_"+kind)
                spin(.5)
                assert len(rows(rid,"nav_goal"))==1
                confirm(rid+"-wrong",action)
                spin(.3)
                assert len(rows(rid,"nav_goal"))==1
                confirm(rid,action)
                confirm(rid,action)  # duplicate staff action must not issue another goal
                if action=="APPROVE_CONTINUE":
                    wait(lambda:goal(rid,"TO_RETURN"),label="TO_RETURN")
                    nav_result(rid,"TO_RETURN")
                    wait(lambda:goal(rid,"TO_HOME"),label="TO_HOME")
                    nav_result(rid,"TO_HOME")
                    wait(lambda:state(rid,"COMPLETED"),label="COMPLETED")
                    spin(.5)
                    assert [x["data"]["leg"] for x in rows(rid,"nav_goal")]==["TO_TABLE","TO_RETURN","TO_HOME"]
                else:
                    wait(lambda:state(rid,"CANCELED","STAFF_ABORT"),label="ABORT")
                    spin(.5)
                    assert len(rows(rid,"nav_goal"))==1
                result["cases"].append({"request_id":rid,"kind":kind,"action":action,
                    "goal_messages":len(rows(rid,"nav_goal")),"reason":reason,"pass":True})
                print("E_R3C_CASE_PASS="+rid+" "+kind+" "+action,flush=True)
            assert node.count_publishers("/cmd_vel")==0
            assert node.count_publishers("/navigate_to_pose/_action/status")==0
            result["verdict"]="E_R3C_REAL_D_DDS_STAFF_CONTRACT_PASS"
            print(result["verdict"],flush=True)
    except BaseException as exc:
        result["first_error"]=repr(exc)
        if (out/"d_node.log").exists():print((out/"d_node.log").read_text()[-6000:],flush=True)
        raise
    finally:
        if proc:
            if proc.poll() is None:
                proc.send_signal(signal.SIGINT)
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=5)
            result["d_exit_code"]=proc.returncode
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")

if __name__=="__main__":
    main()
