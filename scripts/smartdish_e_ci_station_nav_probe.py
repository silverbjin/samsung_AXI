#!/usr/bin/env python3
"""Shared witness: actual Nav2 + independent live Gazebo tray station.
CI uses an isolated model double; WSL Owner uses real private C and manual UI/TTY.
Neither mode claims a robot-mounted tray or model quality acceptance.
"""
import argparse
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import time
import yaml

from smartdish_e_ci_live_tray_probe import CHILD as LIVE_CHILD, read_rows, stop
from smartdish_e_ci_staff_dds_probe import CHILD as STAFF_CHILD, FIXTURE_SHA, FIXTURE_VERSION
from smartdish_tray_world import write_trial
from s3_map_contract import validate_s2_map03_candidate
from smartdish_e_nav_velocity_overlay import prepare_overlay

LEGS=["TO_TABLE","TO_RETURN","TO_HOME"]
DEST=["T03","DISH_RETURN","HOME"]
RID="E-CI-STATION-NAV-01"
TOPIC="/smartdish/tray/image_raw"

def main():
    if not __debug__:raise RuntimeError("E_OWNER_WITNESS_ASSERTIONS_REQUIRED")
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ("robot_sdf","params","out"):
        ap.add_argument("--"+k.replace("_","-"),type=Path,required=True)
    ap.add_argument("--pin",required=True)
    ap.add_argument("--owner-checkpoint",type=Path,default=None)
    args=ap.parse_args()
    owner=args.owner_checkpoint is not None
    if owner:
        if (os.environ.get("GITHUB_ACTIONS") or not os.environ.get("WSL_DISTRO_NAME")
                or not sys.stdin.isatty() or "microsoft" not in Path("/proc/sys/kernel/osrelease").read_text().lower()
                or not os.environ.get("DISPLAY") or not os.environ.get("GZ_PARTITION","").startswith("smartdish_e_owner_nav_")
                or not os.environ.get("SMARTDISH_E_C_SITE_PACKAGES")):
            raise RuntimeError("E_OWNER_STATION_WSL_TTY_RUNTIME_REQUIRED_NO_GOAL")
    elif (os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("ROS_DOMAIN_ID")!="191"
        or os.environ.get("WSL_DISTRO_NAME") or not os.environ.get("GZ_PARTITION","").startswith("smartdish_e_nav_")):
        raise RuntimeError("E_R4_CI_ONLY_NO_OWNER_AUTO_APPROVAL")
    root=Path(__file__).resolve().parents[1]
    assert args.pin==os.environ["SMARTDISH_E_SOURCE_SHA" if owner else "GITHUB_SHA"]==subprocess.check_output(
        ["git","-c","safe.directory="+str(root),"-C",str(root),"rev-parse","HEAD"],text=True).strip()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    result={"source_sha":args.pin,"scope":("OWNER_WSL2_ACTUAL_V1_SEPARATE_STATION" if owner else "ACTUAL_NAV2_SEPARATE_LIVE_GAZEBO_STATION_CI_TEST_DOUBLE"),
        "private_model_loaded":False,"robot_mounted_tray_verified":False,"ui_click_verified":False,
        "test4_opened":False,"fixture_model_version":FIXTURE_VERSION,"verdict":"FAIL",
        "events":[],"legs":[],"action_status":{},"cleanup":{}}
    procs={}
    child=fd=node=owner_adapter=None
    rid=None if owner else RID
    expected_version=FIXTURE_VERSION
    handles=[]
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
    from rclpy.action import ActionClient
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient
    from action_msgs.msg import GoalStatusArray
    from lifecycle_msgs.srv import GetState
    from nav2_msgs.action import NavigateToPose
    from nav_msgs.msg import Odometry, OccupancyGrid
    from sensor_msgs.msg import LaserScan, Image
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from rosgraph_msgs.msg import Clock
    from tf2_msgs.msg import TFMessage
    from std_msgs.msg import String
    from smartdish_robot.contract import load_pose_config, resolve_pose
    from smartdish_ai.stability_inference_node import unpack_ros_rgb
    from smartdish_service.product_admission import product_ai_on_authorized
    from smartdish_ai.model_runtime import OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256
    from ament_index_python.packages import get_package_prefix
    assert not product_ai_on_authorized(True)
    if owner:
        expected_version="resnet18-"+OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256[:12]
        result["fixture_model_version"]=None
        result["expected_owner_model_version"]=expected_version
        subprocess.run([sys.executable,str(root/"scripts/smartdish_e_owner_model_preflight.py"),
            "--checkpoint",str(args.owner_checkpoint),"--report",str(out/"checkpoint_receipt.json")],check=True)
    def executable(pkg,name):
        p=Path(get_package_prefix(pkg))/"lib"/pkg/name
        assert p.is_file()
        return str(p)
    def log_text(name):
        path=out/(name+".log")
        return path.read_text(errors="replace") if path.exists() else ""
    def marker_rows(name,marker):
        out_rows=[]
        for line in log_text(name).splitlines():
            if marker in line:
                try:out_rows.append(json.loads(line.split(marker,1)[1]))
                except ValueError:pass
        return out_rows
    state={"clock":False,"odom":None,"scan":0,"odom_n":0,"map":None,"amcl":None,"map_tf":False,"odom_tf":False}
    frames={}
    active=None
    transcript=""
    def launch(name,cmd,env=None):
        h=(out/(name+".log")).open("w"); handles.append(h)
        p=subprocess.Popen(cmd,env=env or os.environ.copy(),stdout=h,stderr=subprocess.STDOUT,start_new_session=True)
        procs[name]=p
        return p
    def record(topic,body):
        item={"topic":topic,"data":body,"t":time.monotonic()}
        result["events"].append(item)
        return item
    def rows(topic):return [x for x in result["events"] if x["topic"]==topic]
    def status(name,reason=None):
        return next((x for x in rows("status") if x["data"]["state"]==name and
                     (reason is None or x["data"]["reason"]==reason)),None)
    def on_odom(m):
        nonlocal active
        xy=(float(m.pose.pose.position.x),float(m.pose.pose.position.y))
        state["odom"]=xy; state["odom_n"]+=1
        if active:
            active["odom_count"]+=1
            active["odom_max_m"]=max(active["odom_max_m"],math.dist(active["start"],xy))
    def on_scan(m):
        if len(m.ranges)>10:
            state["scan"]+=1
            if active:active["scan_count"]+=1
    def on_tf(m):
        for t in m.transforms:
            state["map_tf"]|=t.header.frame_id=="map" and t.child_frame_id=="odom"
            state["odom_tf"]|=t.header.frame_id=="odom" and t.child_frame_id in ("base_link","base_footprint")
    def on_action(m):
        for s in m.status_list:
            uid=bytes(s.goal_info.goal_id.uuid).hex()
            e=result["action_status"].setdefault(uid,{"first_seen":time.monotonic(),"statuses":[]})
            if not e["statuses"] or e["statuses"][-1]["status"]!=s.status:
                e["statuses"].append({"status":s.status,"t":time.monotonic()})
    def on_image(m):
        stamp=int(m.header.stamp.sec)*1000000000+int(m.header.stamp.nanosec)
        if stamp>0:
            rgb,w,h=unpack_ros_rgb(m)
            frames[stamp]={"sha256":hashlib.sha256(rgb).hexdigest(),"width":w,"height":h,"received_at":time.monotonic()}
            # Keep enough history for the 5s AI response bound, not an unbounded bag.
            if len(frames)>600:frames.pop(next(iter(frames)))
    def recv(topic):
        def cb(m):
            nonlocal active,rid
            body=json.loads(m.data)
            identity=body.get("request_id")
            if owner and rid is None:
                assert isinstance(identity,str) and identity.startswith("REQ-")
                rid=identity
            if identity!=rid:
                raise RuntimeError("E_R4_FOREIGN_REQUEST_"+topic)
            item=record(topic,body)
            if topic=="request":
                assert owner and len(rows("request"))==1
                assert body.get("table_id")=="T03" and body.get("ai_enabled") is True
                assert body.get("table_wait_s")==10 and body.get("dropoff_wait_s")==5
                result["request_id"]=rid
            elif topic=="staff_confirm":
                assert owner and body.get("action") in ("APPROVE_CONTINUE","ABORT")
                assert len(rows("staff_confirm"))==1
                if body["action"]=="ABORT":raise RuntimeError("E_OWNER_STAFF_ABORT_NO_PASS")
            elif topic=="status" and body.get("state") in ("ERROR","CANCELED"):
                raise RuntimeError("E_R4_MISSION_"+body["state"]+":"+str(body.get("reason")))
            if topic=="nav_goal":
                if active is not None or len(result["legs"])>=3:raise RuntimeError("E_R4_EXTRA_OR_OVERLAPPING_GOAL")
                i=len(result["legs"])
                assert body["leg"]==LEGS[i] and body["destination_id"]==DEST[i]
                assert state["odom"] is not None
                active={"leg":body["leg"],"destination_id":body["destination_id"],"start":state["odom"],
                    "t_goal":item["t"],"odom_max_m":0.,"odom_count":0,"scan_count":0}
            elif topic=="nav_result":
                assert active is not None and active["leg"]==body["leg"],body
                assert body["result"]=="SUCCEEDED" and body["reason"]=="",body
                target=targets[active["destination_id"]]
                active.update(t_result=item["t"],result=body["result"],amcl=state["amcl"],
                    amcl_error_m=math.dist(state["amcl"],(target.x,target.y)) if state["amcl"] else None)
                assert active["odom_max_m"]>.25 and active["odom_count"]>=3 and active["scan_count"]>=3,active
                assert active["amcl_error_m"] is not None and active["amcl_error_m"]<=.8,active
                result["legs"].append(active)
                print("E_R4_REAL_PHYSICAL_LEG="+json.dumps(active),flush=True)
                active=None
        return cb
    def drain_tty():
        nonlocal transcript
        if fd is not None and select.select([fd],[],[],0)[0]:
            try:data=os.read(fd,16384)
            except OSError as exc:
                if exc.errno==errno.EIO:raise RuntimeError("E_R4_ADAPTER_TTY_CLOSED") from exc
                raise
            if data:
                t=data.decode("utf-8","replace")
                transcript=(transcript+t)[-20000:]
                with (out/"adapter.log").open("a") as f:f.write(t)
    def spin():
        for n,p in procs.items():
            if p.poll() is not None:raise RuntimeError("E_R4_"+n+"_EXIT_"+str(p.returncode))
        if owner_adapter is not None and owner_adapter.poll() is not None:
            raise RuntimeError("E_OWNER_ADAPTER_EXIT_"+str(owner_adapter.returncode))
        if child is not None:
            pid,code=os.waitpid(child,os.WNOHANG)
            if pid:raise RuntimeError("E_R4_ADAPTER_EXIT_"+str(code))
        drain_tty()
        rclpy.spin_once(node,timeout_sec=.05)
    def wait(check,seconds,stage):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            spin()
            v=check()
            if v:return v
        raise RuntimeError("E_R4_TIMEOUT_"+stage)
    def hold(seconds):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:spin()
    try:
        map_contract=validate_s2_map03_candidate(root)
        map_file=root/"maps/candidates/s2_map03/restaurant_map.yaml"
        pose_file=root/"src/smartdish_robot/config/table_poses.yaml"
        poses=load_pose_config(pose_file)
        targets={d:resolve_pose(poses,d) for d in DEST}
        assert math.dist((targets["HOME"].x,targets["HOME"].y),(0.,0.))<.001
        assert math.dist((targets["T03"].x,targets["T03"].y),(5.25,.38))<.001
        result["map_sha256"]=map_contract["pgm_sha256"]
        rclpy.init()
        node=Node("e_ci_station_nav_witness")
        node.create_subscription(Odometry,"/odom",on_odom,qos_profile_sensor_data)
        node.create_subscription(LaserScan,"/scan",on_scan,qos_profile_sensor_data)
        node.create_subscription(Clock,"/clock",lambda m:state.update(clock=m.clock.sec>0),qos_profile_sensor_data)
        node.create_subscription(PoseWithCovarianceStamped,"/amcl_pose",
            lambda m:state.update(amcl=(m.pose.pose.position.x,m.pose.pose.position.y)),10)
        node.create_subscription(TFMessage,"/tf",on_tf,qos_profile_sensor_data)
        durable=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(OccupancyGrid,"/map",lambda m:state.update(map=m),durable)
        node.create_subscription(GoalStatusArray,"/navigate_to_pose/_action/status",on_action,durable)
        node.create_subscription(Image,TOPIC,on_image,QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE))
        for topic in ("nav_goal","nav_result","status","ai_check_request","stability"):
            node.create_subscription(String,"/collection/"+topic,recv(topic),10)
        if owner:
            node.create_subscription(String,"/collection/request",recv("request"),10)
            node.create_subscription(String,"/collection/staff_confirm",recv("staff_confirm"),10)
        else:
            request=node.create_publisher(String,"/collection/request",10)
            staff=node.create_publisher(String,"/collection/staff_confirm",10)
        nav_action=ActionClient(node,NavigateToPose,"/navigate_to_pose")
        cm=node.create_client(GetState,"/collision_monitor/get_state")
        bt=node.create_client(GetState,"/bt_navigator/get_state")
        from ament_index_python.packages import get_package_share_directory
        nav_share=Path(get_package_share_directory("nav2_bringup"))
        restaurant_launch=Path(get_package_share_directory("restaurant_bringup"))/"launch"/"navigation.launch.py"
        generated_launch=prepare_overlay(nav_share,restaurant_launch,out)
        launch("nav2",["ros2","launch",str(generated_launch),"gui:="+("true" if owner else "false"),
            "s6_stagger_nav_start:=true","robot_sdf:="+str(args.robot_sdf.resolve()),
            "map:="+str(map_file),"params_file:="+str(args.params.resolve())])
        wait(lambda:state["clock"] and state["scan"]>=3 and state["odom"] is not None and state["map"] is not None,220,"CLOCK_SCAN_ODOM_MAP")
        m=state["map"]
        assert m.info.width==map_contract["width"] and m.info.height==map_contract["height"] and m.header.frame_id=="map"
        wait(lambda:state["amcl"] is not None and state["map_tf"] and state["odom_tf"]
             and nav_action.wait_for_server(timeout_sec=.05) and cm.wait_for_service(timeout_sec=0) and bt.wait_for_service(timeout_sec=0),170,"AMCL_TF_ACTION_CM")
        assert math.dist(state["amcl"],(0.,0.))<.9
        lifecycle={}
        result["lifecycle_transitions"]=[]
        def lifecycle_state(client,name):
            f=client.call_async(GetState.Request())
            wait(f.done,10,name+"_STATE")
            reply=f.result().current_state
            value={"id":reply.id,"label":reply.label}
            if lifecycle.get(name)!=value:
                lifecycle[name]=value
                item={"node":name,**value,"t":time.monotonic()}
                result["lifecycle_transitions"].append(item)
                print("E_R4_LIFECYCLE="+json.dumps(item),flush=True)
            return reply.id
        def cm_active():
            return lifecycle_state(cm,"collision_monitor")==3
        def all_active():
            a=cm_active()
            b=lifecycle_state(bt,"bt_navigator")==3
            if not (a and b):hold(.25)
            return a and b
        wait(all_active,90,"NAV2_LIFECYCLE_ACTIVE")
        result["cm_active_start"]=True
        result["bt_active_start"]=True
        def graph_endpoints():
            snapshot={}
            for topic in ("/cmd_vel","/cmd_vel_nav","/cmd_vel_smoothed","/cmd_vel_teleop"):
                for direction, query in (("publishers",node.get_publishers_info_by_topic),
                                         ("subscribers",node.get_subscriptions_info_by_topic)):
                    snapshot[topic+"_"+direction]=sorted([
                        {"node":e.node_name,"namespace":e.node_namespace,"type":e.topic_type,
                         "gid":list(e.endpoint_gid)} for e in query(topic)],
                        key=lambda e:(e["namespace"],e["node"],e["gid"]))
            return snapshot
        result["velocity_graph_transitions"]=[]
        def cm_sole():
            g=graph_endpoints()
            if not result["velocity_graph_transitions"] or result["velocity_graph_transitions"][-1]["graph"]!=g:
                result["velocity_graph_transitions"].append({"t":time.monotonic(),"graph":g})
                print("E_R4_VELOCITY_GRAPH="+json.dumps(g),flush=True)
            return ([e["node"] for e in g["/cmd_vel_publishers"]]==["collision_monitor"]
                    and [e["node"] for e in g["/cmd_vel_subscribers"]]==["ros_gz_bridge"]
                    and "docking_server" in [e["node"] for e in g["/cmd_vel_nav_publishers"]]
                    and [e["node"] for e in g["/cmd_vel_nav_subscribers"]]==["velocity_smoother"]
                    and [e["node"] for e in g["/cmd_vel_smoothed_publishers"]]==["velocity_smoother"]
                    and [e["node"] for e in g["/cmd_vel_smoothed_subscribers"]]==["collision_monitor"])
        from ament_index_python.packages import get_package_share_directory
        installed_launch=Path(get_package_share_directory("nav2_bringup"))/"launch"/"navigation_launch.py"
        (out/"installed_nav2_navigation_launch.py").write_bytes(installed_launch.read_bytes())
        wait(cm_sole,15,"CM_SOLE_CMD_VEL")
        result["cm_sole_cmd_vel_start"]=True
        assert not rows("nav_goal") and not result["action_status"]
        # Owner uses actual controlling tty; only CI uses a synthetic PTY.
        if owner:
            h=(out/"adapter.log").open("w"); handles.append(h)
            print("E_OWNER_CHECK_GAZEBO_AND_ENTER_A_TTY_APPROVAL_NO_GOAL",flush=True)
            owner_adapter=subprocess.Popen([executable("smartdish_robot","navigation_adapter"),"--ros-args",
                "-p","goals_enabled:=true","-p","set_initial_home:=false",
                "-p","poses_file:="+str(pose_file)],stdin=subprocess.DEVNULL,
                stdout=h,stderr=subprocess.STDOUT,start_new_session=False)
            wait(lambda:"SMARTDISH_A_READY" in log_text("adapter"),180,"HUMAN_ADAPTER_READY")
            assert "SMARTDISH_A_OPERATOR_APPROVED" in log_text("adapter")
            result["tty_approval"]="ACTUAL_OWNER_CONTROLLING_TTY"
        else:
            # Existing A adapter, exact TTY gate. CI-only explicit synthetic operator action.
            child,fd=pty.fork()
            if child==0:
                os.execvpe("ros2",["ros2","run","smartdish_robot","navigation_adapter","--ros-args",
                    "-p","goals_enabled:=true","-p","set_initial_home:=false",
                    "-p","poses_file:="+str(pose_file)],os.environ.copy())
            os.set_blocking(fd,False)
            wait(lambda:"YES-SMARTDISH-A-GOALS 입력:" in transcript,180,"TTY_PROMPT")
            assert not rows("nav_goal") and not result["action_status"]
            hold(10)
            os.write(fd,b"YES-SMARTDISH-A-GOALS\n")
            wait(lambda:"SMARTDISH_A_READY" in transcript,180,"ADAPTER_READY")
            result["tty_approval"]="CI_ONLY_AFTER_10S_PROMPT"
        # Separate station physics, SAME ROS domain, DIFFERENT Gazebo transport
        # partition; bridge only RGB, never /clock, poses or cmd_vel.
        world=out/"station.sdf"
        write_trial("ST-01",102,world,"E_CI_STATION")
        cfg=yaml.safe_load((root/"config/smartdish_tray_bridge.yaml").read_text())
        selected=[x for x in cfg if x["ros_topic_name"]==TOPIC]
        assert len(selected)==1 and selected[0]["direction"]=="GZ_TO_ROS"
        bridge=out/"station_bridge.yaml";bridge.write_text(yaml.safe_dump(selected))
        station_env={**os.environ,"GZ_PARTITION":"smartdish_e_station_"+(str(os.getpid()) if owner else os.environ["GITHUB_RUN_ID"])}
        assert station_env["GZ_PARTITION"]!=os.environ["GZ_PARTITION"]
        result["station_partition"]=station_env["GZ_PARTITION"]
        result["nav_partition"]=os.environ["GZ_PARTITION"]
        result["station_bridge_topics"]=[TOPIC]
        launch("station",["gz","sim","-s","-r","-v2",str(world)],station_env)
        launch("station_bridge",["ros2","run","ros_gz_bridge","parameter_bridge",
            "--ros-args","-r","__node:=smartdish_e_station_bridge","-p","config_file:="+str(bridge)],station_env)
        event_log=out/"c_events.jsonl"
        if owner:
            c_env={**os.environ,"PYTHONPATH":os.environ["SMARTDISH_E_C_SITE_PACKAGES"]+
                (":"+os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),"PYTHONNOUSERSITE":"1"}
            launch("c_node",[executable("smartdish_ai","stability_inference_node"),"--ros-args",
                "-p","owner_gazebo_integration:=true","-p","model_path:="+str(args.owner_checkpoint)],c_env)
            wait(lambda:"C_MODEL_LOADED version="+expected_version+" scope=OWNER_GAZEBO_INTEGRATION_ONLY" in log_text("c_node"),90,"OWNER_REAL_MODEL_LOAD")
            result["private_model_loaded"]=True
            launch("d_node",[executable("smartdish_service","smartdish_manager"),"--ai-available","true","--owner-gazebo-integration","--owner-station-acceptance"])
        else:
            c_code=LIVE_CHILD.replace("return predict, 'CI_ONLY_TEST_DOUBLE'","return predict, os.environ['E_CI_FIXTURE_VERSION']")
            d_code=STAFF_CHILD.replace("=='190'","=='191'")
            assert c_code!=LIVE_CHILD and d_code!=STAFF_CHILD
            launch("c_node",[sys.executable,"-u","-c",c_code,"--ros-args",
                "-p","owner_gazebo_integration:=true","-p","model_path:=CI_ONLY_NO_CHECKPOINT"],
                {**os.environ,"E_CI_EVENT_LOG":str(event_log),"E_CI_FIXTURE_VERSION":FIXTURE_VERSION})
            launch("d_node",[sys.executable,"-u","-c",d_code,"--ai-available","true","--owner-gazebo-integration"],
                {**os.environ,"E_CI_FIXTURE_SHA":FIXTURE_SHA})
        params=AsyncParameterClient(node,"/smartdish_stability_inference")
        wait(lambda:(owner or (request.get_subscription_count()==1 and staff.get_subscription_count()==1)) and
             node.count_publishers("/collection/nav_goal")==1 and node.count_publishers("/collection/nav_result")==1 and
             node.count_publishers("/collection/stability")==1 and params.wait_for_services(timeout_sec=0),30,"DDS")
        if not owner:
            f=params.set_parameters_atomically([Parameter("stable_confidence_min",value=.65),
                                               Parameter("unstable_confidence_min",value=.90)])
            wait(f.done,5,"PARAMETER_ACK"); assert f.result().result.successful
        def live_cache():
            candidates=marker_rows("c_node","C_OWNER_FRAME_ACCEPTED=") if owner else read_rows(event_log)
            for row in reversed(candidates):
                stamp=row.get("stamp_ns")
                if ((owner or row["event"]=="cache") and stamp in frames and row["rgb_sha256"]==frames[stamp]["sha256"]
                    and 0<=time.monotonic()-row["received_at"]<1.5):return row
            return None
        result["station_live_cache"]=wait(live_cache,75,"STATION_CAMERA")
        eps=node.get_publishers_info_by_topic(TOPIC)
        assert len(eps)==1 and eps[0].node_name=="smartdish_e_station_bridge",repr(eps)
        assert eps[0].qos_profile.reliability==ReliabilityPolicy.RELIABLE
        assert node.count_publishers("/clock")==1,"E_R4_CLOCK_SOURCE_COLLISION"
        assert not rows("nav_goal") and not result["action_status"]
        result["clock_publishers"]=1
        if owner:
            launch("ui",[executable("smartdish_service","smartdish_ui"),"--ai-available","true","--owner-gazebo-integration","--owner-station-acceptance"])
            wait(lambda:"SMARTDISH_D_UI_READY" in log_text("ui"),60,"OWNER_UI_READY")
            print("E_OWNER_UI_READY_CLICK_T03_ENABLE_AI_10S_5S_THEN_STAFF_CONFIRM",flush=True)
            wait(lambda:rows("request"),180,"OWNER_UI_REQUEST")
            assert "SMARTDISH_D_UI_CLICK request_id="+rid+" table_id=T03" in log_text("ui")
            assert [ep.node_name for ep in node.get_publishers_info_by_topic("/collection/request")]==["smartdish_ui"]
        else:
            request.publish(String(data=json.dumps({"request_id":RID,"table_id":"T03","table_wait_s":10,
                                                    "dropoff_wait_s":5,"ai_enabled":True})))
            record("ci_request",{"request_id":RID,"ai_enabled":True})
        wait(lambda:len(result["legs"])==1,465,"TO_TABLE")
        confirmation=wait(lambda:status("NEEDS_CONFIRMATION",None if owner else "AI_STABLE_STAFF_CONFIRM_REQUIRED"),25,"AI_CONFIRM")
        # Wait independently for both DDS topics; confirmation can arrive first.
        wait(lambda:len(rows("ai_check_request"))>=1 and len(rows("stability"))>=1,5,"AI_DDS_CORRELATION")
        ai=rows("ai_check_request"); stability=rows("stability")
        assert len(ai)==len(stability)==1 and stability[0]["data"]["capture_id"]==ai[0]["data"]["capture_id"]
        assert stability[0]["data"]["model_version"]==expected_version
        if owner:
            observed=stability[0]["data"]["status"]
            expected_reason={"STABLE":"AI_STABLE_STAFF_CONFIRM_REQUIRED","UNSTABLE":"AI_UNSTABLE","UNKNOWN":"AI_UNKNOWN"}[observed]
            assert confirmation["data"]["reason"]==expected_reason
        else:
            assert stability[0]["data"]["status"]=="STABLE" and stability[0]["data"]["confidence"]==.75
        assert ai[0]["t"]-result["legs"][0]["t_result"]>=9.7
        def matched_predict():
            candidates=marker_rows("c_node","C_OWNER_INFERENCE_INPUT=") if owner else read_rows(event_log)
            for x in candidates:
                st=x.get("stamp_ns")
                if owner and (x.get("request_id")!=rid or x.get("capture_id")!=ai[0]["data"]["capture_id"]
                              or x.get("model_version")!=expected_version or x.get("result_status")!=stability[0]["data"]["status"]):
                    continue
                if (owner or x["event"]=="predict") and st in frames and frames[st]["sha256"]==x["predictor_sha256"]:
                    return x
            return None
        result["actual_predictor_input"]=wait(matched_predict,5,"LIVE_PREDICTOR")
        if not owner:
            def logged_predict():
                return next((x for x in marker_rows("c_node","C_OWNER_INFERENCE_INPUT=")
                    if x.get("request_id")==RID and x.get("capture_id")==ai[0]["data"]["capture_id"]
                    and x.get("model_version")==FIXTURE_VERSION and x.get("result_status")=="STABLE"
                    and x.get("predictor_sha256")==result["actual_predictor_input"]["predictor_sha256"]),None)
            result["c_prediction_provenance"]=wait(logged_predict,5,"C_PROVENANCE_LOG")
        if owner:
            print("E_OWNER_REAL_INFERENCE_WITNESSED_WAIT_EXPLICIT_UI_APPROVAL",flush=True)
            wait(lambda:rows("staff_confirm"),180,"HUMAN_STAFF_APPROVAL")
            assert rows("staff_confirm")[0]["data"]["action"]=="APPROVE_CONTINUE"
            wait(lambda:"SMARTDISH_D_UI_STAFF_CLICK request_id="+rid+" action=APPROVE_CONTINUE" in log_text("ui"),5,"UI_STAFF_CLICK")
        else:
            assert len(rows("nav_goal"))==1 and active is None
            hold(1.0)
            assert len(rows("nav_goal"))==1 and active is None
            record("ci_staff_confirm",{"request_id":RID,"action":"APPROVE_CONTINUE"})
            staff.publish(String(data=json.dumps({"request_id":RID,"action":"APPROVE_CONTINUE"})))
        wait(lambda:len(result["legs"])==2,465,"TO_RETURN")
        wait(lambda:len(result["legs"])==3,465,"TO_HOME")
        wait(lambda:status("COMPLETED"),15,"COMPLETED")
        wait(lambda:len(result["action_status"])==3 and all(x["statuses"][-1]["status"]==4
             for x in result["action_status"].values()),10,"THREE_UUID_SUCCEEDED")
        assert len(rows("nav_goal"))==3 and len(rows("nav_result"))==3
        # Cross-topic DDS observation order can vary. Verify D causal order
        # using the single process log, not a receipt time heuristic.
        lines=log_text("d_node").splitlines()
        staff_idx=[i for i,l in enumerate(lines) if "SMARTDISH_D_STAFF_CONFIRM_ACCEPTED=" in l and rid in l and "APPROVE_CONTINUE" in l]
        return_idx=[i for i,l in enumerate(lines) if "SMARTDISH_D_EVENT topic=/collection/nav_goal json=" in l and rid in l and "TO_RETURN" in l]
        assert len(staff_idx)==len(return_idx)==1 and staff_idx[0]<return_idx[0]
        result["staff_acceptance_order_verified"]=True
        if owner:
            wait(lambda:"SMARTDISH_D_UI_APPLIED request_id="+rid+" state=COMPLETED" in log_text("ui"),15,"UI_COMPLETED")
            result["ui_click_verified"]=True
        else:
            assert result["legs"][1]["t_goal"]>=rows("ci_staff_confirm")[0]["t"]
        assert result["legs"][2]["t_goal"]-result["legs"][1]["t_result"]>=4.7
        assert all(status(s) for s in ("TO_TABLE","WAIT_LOADING","AI_CHECK","NEEDS_CONFIRMATION",
                                      "TO_RETURN","WAIT_UNLOADING","TO_HOME","COMPLETED"))
        assert cm_active(),"E_R4_CM_NOT_ACTIVE_END"
        result["cm_active_end"]=True
        assert cm_sole(),"E_R4_VELOCITY_CHAIN_DRIFT_END"
        result["cm_cmd_vel_publishers"]=[ep.node_name for ep in node.get_publishers_info_by_topic("/cmd_vel")]
        assert result["cm_cmd_vel_publishers"]==["collision_monitor"],result["cm_cmd_vel_publishers"]
        result["verdict"]=("E_OWNER_WSL2_AI_ON_STATION_L3_PASS" if owner else "E_R4_REAL_NAV2_STATION_CI_TEST_DOUBLE_PASS")
    except BaseException as exc:
        result["first_error"]=repr(exc)
        for name in ("adapter","nav2","station","station_bridge","c_node","d_node"):
            f=out/(name+".log")
            if f.exists():print("E_R4_LOG_TAIL "+name+"\n"+f.read_text(errors="replace")[-3500:],flush=True)
        raise
    finally:
        for n in ("ui","d_node","c_node"):
            if n in procs:result["cleanup"][n]=stop(procs.pop(n))
        if owner_adapter is not None:
            if owner_adapter.poll() is None:
                owner_adapter.send_signal(signal.SIGINT)
                try:owner_adapter.wait(timeout=15)
                except subprocess.TimeoutExpired:owner_adapter.kill();owner_adapter.wait()
            result["cleanup"]["adapter"]=owner_adapter.returncode
        if child is not None:
            try:os.killpg(child,signal.SIGINT)
            except ProcessLookupError:pass
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try:
                    p,code=os.waitpid(child,os.WNOHANG)
                    if p:result["cleanup"]["adapter"]=os.waitstatus_to_exitcode(code);break
                except ChildProcessError:break
                time.sleep(.1)
            else:
                try:os.killpg(child,signal.SIGKILL);os.waitpid(child,0)
                except (ProcessLookupError,ChildProcessError):pass
                result["cleanup"]["adapter"]=-9
        if fd is not None:os.close(fd)
        for n in ("station_bridge","station","nav2"):
            if n in procs:result["cleanup"][n]=stop(procs.pop(n))
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        for h in handles:h.close()
        cleanup_failed=result["verdict"].endswith("_PASS") and any(result["cleanup"].get(n)!=0 for n in ("c_node","d_node"))
        if cleanup_failed:
            result["verdict"]="FAIL"
            result["first_error"]="E_R4_C_D_CLEANUP_FAILED"
        (out/"result.json").write_text(json.dumps(result,indent=2)+"\n")
        (out/"witness_frames.json").write_text(json.dumps(frames,indent=2)+"\n")
        if cleanup_failed:raise RuntimeError("E_R4_C_D_CLEANUP_FAILED")
        print(result["verdict"],flush=True)

if __name__=="__main__":
    main()
