#!/usr/bin/env python3
"""Actual independent A13 Gazebo camera -> C ROS node, no image republisher.
CI-only predictor double; no private model, real robot tray claim or Nav2.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

CHILD = """
import hashlib, json, os, time
from pathlib import Path
from smartdish_ai import stability_inference_node as node
assert os.environ.get('GITHUB_ACTIONS') == 'true'
out = Path(os.environ['E_CI_EVENT_LOG'])
last = None
def record(row):
    with out.open('a') as f:
        f.write(json.dumps(row) + chr(10))
original = node.InferenceCore.cache_rgb
def cache(self, rgb, width, height, **kwargs):
    global last
    accepted = original(self, rgb, width, height, **kwargs)
    if accepted:
        last = {'stamp_ns': kwargs.get('stamp_ns'), 'rgb_sha256': hashlib.sha256(rgb).hexdigest(),
                'received_at': kwargs.get('received_at'), 'width': width, 'height': height}
        record(dict(last, event='cache'))
    return accepted
def loader(path, *, owner_gazebo_integration=False):
    assert str(path) == 'CI_ONLY_NO_CHECKPOINT' and owner_gazebo_integration is True
    def predict(rgb, width, height):
        digest = hashlib.sha256(rgb).hexdigest()
        assert last and digest == last['rgb_sha256'] and (width,height) == (640,480)
        record(dict(last, event='predict', predictor_sha256=digest))
        return 'STABLE', 0.75
    return predict, 'CI_ONLY_TEST_DOUBLE'
node.InferenceCore.cache_rgb = cache
node.load_predictor = loader
node.main()
"""

def read_rows(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass  # writer may be between writes; bounded observer will re-read
    return rows

def stop(proc):
    if proc is None:
        return None
    if proc.poll() is None:
        os.killpg(proc.pid, signal.SIGINT)
        try:
            return proc.wait(timeout=25)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
    return proc.wait(timeout=5)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pin", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("WSL_DISTRO_NAME"):
        raise RuntimeError("E_R3B_CI_ONLY")
    root = Path(__file__).resolve().parents[1]
    pin = subprocess.check_output(["git", "-c", "safe.directory="+str(root),
                                   "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    assert pin == args.pin
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    result = {"source_sha": pin, "scope": "INDEPENDENT_TRAY_LIVE_CI_TEST_DOUBLE",
              "private_model_loaded": False, "robot_mounted_tray_verified": False,
              "test4_opened": False, "image_republished": False, "verdict": "FAIL"}
    a = c = node = None
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient
    from sensor_msgs.msg import Image
    from std_msgs.msg import String
    from smartdish_ai.stability_inference_node import unpack_ros_rgb
    try:
        with (out/"a_runner.log").open("w") as a_log:
            a = subprocess.Popen([sys.executable,"-u",str(root/"scripts/smartdish_a_tray_live.py"),
                "single","--headless","--scene","ST-01","--seed","101","--expected-sha",pin],
                stdout=a_log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic()+30
            while time.monotonic()<deadline:
                lines=(out/"a_runner.log").read_text().splitlines()
                found=[l for l in lines if l.startswith("A13_RENDER_ENV_DIAGNOSTICS=")]
                if found:
                    domain=int(json.loads(found[0].split("=",1)[1])["ros_domain_id"])
                    break
                if a.poll() is not None:
                    raise RuntimeError("E_R3B_A_EARLY_EXIT")
                time.sleep(.05)
            else:
                raise RuntimeError("E_R3B_A_DOMAIN_NOT_OBSERVED")
            assert 55<=domain<95
            result["ros_domain_id"]=domain
            rclpy.init(domain_id=domain)
            node=Node("e_ci_live_tray_witness")
            frames={}
            responses=[]
            def image(msg):
                stamp=int(msg.header.stamp.sec)*1000000000+int(msg.header.stamp.nanosec)
                if stamp>0:
                    rgb,w,h=unpack_ros_rgb(msg)
                    frames[stamp]={"rgb_sha256":hashlib.sha256(rgb).hexdigest(),
                                   "width":w,"height":h,"frame_id":msg.header.frame_id}
            node.create_subscription(Image,"/smartdish/tray/image_raw",image,
                                     QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE))
            node.create_subscription(String,"/collection/stability",
                                     lambda m:responses.append(json.loads(m.data)),10)
            req=node.create_publisher(String,"/collection/ai_check_request",10)
            client=AsyncParameterClient(node,"/smartdish_stability_inference")
            events=out/"c_events.jsonl"
            with (out/"c_node.log").open("w") as c_log:
                c=subprocess.Popen([sys.executable,"-u","-c",CHILD,"--ros-args",
                    "-p","owner_gazebo_integration:=true","-p","model_path:=CI_ONLY_NO_CHECKPOINT"],
                    env={**os.environ,"ROS_DOMAIN_ID":str(domain),"E_CI_EVENT_LOG":str(events)},
                    stdout=c_log,stderr=subprocess.STDOUT,start_new_session=True)
                def until(check,seconds,stage,require_a=True):
                    deadline=time.monotonic()+seconds
                    while time.monotonic()<deadline:
                        if c.poll() is not None:
                            raise RuntimeError("E_R3B_C_EARLY_EXIT_"+stage)
                        if require_a and a.poll() is not None:
                            raise RuntimeError("E_R3B_A_EARLY_EXIT_"+stage)
                        rclpy.spin_once(node,timeout_sec=.05)
                        value=check()
                        if value:
                            return value
                    raise RuntimeError("E_R3B_TIMEOUT_"+stage)
                until(lambda:req.get_subscription_count()==1 and
                      node.count_publishers("/collection/stability")==1 and
                      client.wait_for_services(timeout_sec=0.0),20,"DDS")
                f=client.set_parameters_atomically([
                    Parameter("stable_confidence_min",value=.65),
                    Parameter("unstable_confidence_min",value=.90)])
                until(f.done,5,"PARAMETER")
                assert f.result().result.successful
                def post_spawn_stamp():
                    text=(out/"a_runner.log").read_text()
                    m=re.search(r"SMARTDISH_A_TRAY_CAMERA_LIVE_PASS trial=\S+ stamp_ns=(\d+)",text)
                    return int(m.group(1)) if m else None
                capture=until(post_spawn_stamp,90,"POST_SPAWN_CAPTURE")
                def matching_cache():
                    for row in reversed(read_rows(events)):
                        stamp=row.get("stamp_ns")
                        if (row["event"]=="cache" and stamp is not None and stamp>=capture
                                and stamp in frames and row["rgb_sha256"]==frames[stamp]["rgb_sha256"]
                                and 0<=time.monotonic()-row["received_at"]<1.0):
                            return row
                    return None
                result["pre_request_cache"]=until(matching_cache,20,"LIVE_C_CACHE")
                eps=node.get_publishers_info_by_topic("/smartdish/tray/image_raw")
                assert len(eps)==1 and "bridge" in eps[0].node_name.lower(),repr(eps)
                assert eps[0].qos_profile.reliability==ReliabilityPolicy.RELIABLE
                result["image_publisher"]=eps[0].node_name
                msg=String(data=json.dumps({"request_id":"E-CI-R3B","capture_id":"LIVE-1"}))
                req.publish(msg)
                until(lambda:responses,5,"C_RESPONSE")
                assert len(responses)==1 and responses[0]=={"request_id":"E-CI-R3B",
                    "capture_id":"LIVE-1","status":"STABLE","confidence":.75,
                    "model_version":"CI_ONLY_TEST_DOUBLE"},responses
                result["response"]=responses[0]
                def predictor_match():
                    rows=[x for x in read_rows(events) if x["event"]=="predict"]
                    if len(rows)!=1:
                        return None
                    x=rows[0]; stamp=x["stamp_ns"]
                    if stamp in frames and stamp>=capture and frames[stamp]["rgb_sha256"]==x["predictor_sha256"]:
                        return x
                    return None
                result["actual_predictor_input"]=until(predictor_match,5,"PREDICTOR_WITNESS")
                assert node.count_publishers("/collection/nav_goal")==0
                assert node.count_publishers("/cmd_vel")==0
                result["nav_goal_publishers"]=0
                result["cmd_vel_publishers"]=0
                print("E_R3B_LIVE_IMAGE_PREDICTOR_BYTES_MATCH",flush=True)
                # Complete the already-running real A physics observation once.
                until(lambda:a.poll() is not None,240,"A_COMPLETE",require_a=False)
                assert a.returncode==0,a.returncode
                summaries=list((root/"generated/smartdish_tray").glob("run_*/summary.json"))
                assert len(summaries)==1
                summary=json.loads(summaries[0].read_text())
                trial=summary["trials"][0]
                assert summary["source_sha"]==pin and summary["verdict"]=="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS"
                assert trial["capture_stamp_ns"]==capture and trial["ros_domain_id"]==str(domain)
                assert trial["motion"]["observation"]=="HELD_OBSERVED"
                result["a_capture_stamp_ns"]=capture
                result["a_image_callbacks"]=trial["image_received_count"]
                result["independent_witness_frames"]=len(frames)
                result["c_exit_code"]=stop(c)
                assert result["c_exit_code"]==0,"E_R3B_C_CLEAN_SHUTDOWN_REQUIRED"
                result["verdict"]="E_R3B_LIVE_GAZEBO_C_DDS_TEST_DOUBLE_PASS"
                print(result["verdict"],flush=True)
    except BaseException as exc:
        result["first_error"]=repr(exc)
        for name in ("a_runner.log","c_node.log"):
            if (out/name).exists():
                print((out/name).read_text()[-6000:],flush=True)
        raise
    finally:
        result["a_cleanup_rc"]=stop(a)
        result["c_cleanup_rc"]=stop(c)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
        if 'frames' in locals():
            (out/"witness_frames.json").write_text(json.dumps(frames,indent=2)+"\n")

if __name__=="__main__":
    main()
