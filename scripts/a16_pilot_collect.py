#!/usr/bin/env python3
"""A16 actual ROS RGB + same-step Gazebo pose and contact pilot, one scene."""
import argparse,hashlib,json,os,random,subprocess,sys,time,tarfile
from pathlib import Path
from PIL import Image as PILImage
from smartdish_platform.runtime import gui_profile
from a17_production_profile import PROFILES,INHERIT,RETAIN,prepare as prepare_server_profile,observe as observe_server_profile,cleanup_result as production_cleanup_result
from smartdish_platform.lifecycle import stop_owned
from smartdish_platform.evidence import sha256,verify_archive
from a16_pilot_world import generate,SCENES,TRIGGER_NS,END_NS,PLATFORM_SHA,VERSION
from a16_pilot_contract import load_poses,check_initial,check_trigger,metrics,need
from a16_diagnostics import load_native,registration,transport_diagnostic
from a14_production_health_probe import read_ecm
from a14_physics_freshness_contract import evaluate,read_rows
from a14_r02_production_collect import expected_sensors,cross_check
from smartdish_a_tray_live import gz_call
from smartdish_tray_camera import TOPIC,INFO_TOPIC,FRAME
import rclpy
from rclpy.qos import QoSProfile,ReliabilityPolicy,qos_profile_sensor_data
from sensor_msgs.msg import Image,CameraInfo
from rosgraph_msgs.msg import Clock
from ros_gz_interfaces.msg import Contacts

def dump(path,obj):Path(path).write_text(json.dumps(obj,sort_keys=True,indent=2)+"\n")
def stamp(s):return int(s.sec)*1_000_000_000+int(s.nanosec)
from a16_archive import scene_package as package
def run(a):
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    report=dict(source_sha=a.sha,scene_id=a.scene,data_verdict="HOLD",gui="NOT_RUN",cleanup="NOT_RUN",ground_truth="UNKNOWN_HOLD",human_approved=False,training_eligible=False,platform_sha=PLATFORM_SHA,producer_version=VERSION,production_contact_health="HOLD",first_error=None)
    procs=[];handles=[];node=None;initialized=False;gui=None;server=None;profile_record=None
    profile=getattr(a,"server_profile",INHERIT)
    if profile!=INHERIT:report["server_runtime_profile"]={"profile":profile,"production_cleanup":"HOLD","runtime_observation":None}
    state=dict(clock=0,frames={},frame_stamps=[],infos={},raw=[],overflow=False)
    env=dict(os.environ,GZ_PARTITION="smartdish_a16_"+str(os.getpid())+"_"+str(random.randrange(1000000)),ROS_DOMAIN_ID=str(random.randrange(40,180)))
    env.setdefault("GZ_SIM_RENDER_ENGINE","ogre2")
    def launch(role,cmd,childenv):
        h=(out/(role+".log")).open("w");handles.append(h)
        p=subprocess.Popen(cmd,env=childenv,stdout=h,stderr=subprocess.STDOUT,start_new_session=True);procs.append((role,p))
        print("A16_LAUNCH="+json.dumps(dict(role=role,pid=p.pid,renderer={k:childenv.get(k) for k in ("GALLIUM_DRIVER","MESA_D3D12_DEFAULT_ADAPTER_NAME","LIBGL_ALWAYS_SOFTWARE","QT_QPA_PLATFORM")})),flush=True)
        return p
    def spin(seconds=.05):
        for role,p in procs:
            if role!="gui" and p.poll() is not None:raise RuntimeError("A16_OWNED_EXIT_"+role+"_"+str(p.returncode))
        rclpy.spin_once(node,timeout_sec=seconds)
    def img(msg):
        t=stamp(msg.header.stamp)
        if t<=0:return
        state["frame_stamps"].append(t)
        if len(state["frame_stamps"])>500:state["overflow"]=True
        if 1_400_000_000<=t<=2_000_000_000:
            state["frames"][t]=msg
    def info(msg):
        t=stamp(msg.header.stamp)
        if 1_200_000_000<=t<=2_200_000_000:
            state["infos"][t]=dict(stamp_ns=t,frame_id=msg.header.frame_id,width=msg.width,height=msg.height,k=list(msg.k),d=list(msg.d),distortion_model=msg.distortion_model)
    def clock(msg):state["clock"]=max(state["clock"],stamp(msg.clock))
    def contact(topic):
        def cb(msg):
            if len(state["raw"])>=100000:state["overflow"]=True;return
            t=stamp(msg.header.stamp)
            state["raw"].append(dict(topic=topic,sim_time_ns=t,receive_monotonic_ns=time.monotonic_ns(),timestamp_source="ROS_CONTACT_HEADER_STAMP" if t>0 else "INVALID_ZERO_STAMP",contacts=[dict(collision1=str(x.collision1.name),collision2=str(x.collision2.name),collision1_id=int(x.collision1.id),collision2_id=int(x.collision2.id)) for x in msg.contacts]))
        return cb
    try:
        # Resolve explicit profile before launching any owned child. Only server receives the new env.
        server_env,profile_record=prepare_server_profile(env,profile,a.source_class)
        if profile_record is not None:report["server_runtime_profile"]=profile_record
        meta=generate(a.scene,out,a.pose_plugin,a.health_plugin);meta["source_sha"]=a.sha;meta["source_class"]=a.source_class;dump(out/"a16_design.json",meta)
        native=launch("native_contact",[str(a.native_tap),str(out/"native_contacts.tsv"),*meta["contact_topics"]],env)
        until=time.monotonic()+8
        while time.monotonic()<until and "A16_NATIVE_SUBSCRIBED" not in (out/"native_contact.log").read_text():
            need(native.poll() is None,"A16_NATIVE_START_FAILED");time.sleep(.05)
        need("A16_NATIVE_SUBSCRIBED" in (out/"native_contact.log").read_text(),"A16_NATIVE_START_TIMEOUT")
        server=launch("server",["gz","sim","-s","-v2",str(out/"scenario.sdf")],server_env)
        root=Path(__file__).resolve().parents[1]
        for role,cfg in (("rgb_bridge",root/"config/smartdish_tray_bridge.yaml"),("contact_bridge",out/"a14_contact_bridge.yaml")):
            launch(role,["ros2","run","ros_gz_bridge","parameter_bridge","--ros-args","-p","config_file:="+str(cfg)],env)
        rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]));initialized=True
        node=rclpy.create_node("smartdish_a16_"+str(os.getpid()))
        qos=QoSProfile(depth=20,reliability=ReliabilityPolicy.RELIABLE)
        node.create_subscription(Image,TOPIC,img,qos);node.create_subscription(CameraInfo,INFO_TOPIC,info,qos_profile_sensor_data)
        node.create_subscription(Clock,"/clock",clock,QoSProfile(depth=50))
        for topic in meta["contact_topics"]:node.create_subscription(Contacts,topic,contact(topic),qos_profile_sensor_data)
        deadline=time.monotonic()+75
        while time.monotonic()<deadline:
            spin()
            r=subprocess.run(["gz","service","-l"],env=env,capture_output=True,text=True,timeout=7)
            if "/world/smartdish_tray/control" in r.stdout and node.count_publishers(TOPIC)>0 and node.count_publishers("/clock")>0 and node.count_publishers(INFO_TOPIC)>0 and all(node.count_publishers(t)>0 for t in meta["contact_topics"]):break
        else:raise RuntimeError("A16_SERVICE_OR_BRIDGE_NOT_READY")
        endpoints={}
        for topic in [TOPIC,INFO_TOPIC,"/clock",*meta["contact_topics"]]:
            pinfo=node.get_publishers_info_by_topic(topic)
            endpoints[topic]=[{"type":e.topic_type,"node":e.node_name,"reliability":str(e.qos_profile.reliability),"durability":str(e.qos_profile.durability),"depth":e.qos_profile.depth} for e in pinfo]
        dump(out/"topic_qos.json",endpoints)
        need(all(any(e["type"]==wanted for e in endpoints[topic]) for topic,wanted in [(TOPIC,"sensor_msgs/msg/Image"),(INFO_TOPIC,"sensor_msgs/msg/CameraInfo"),("/clock","rosgraph_msgs/msg/Clock")]),"A16_L1_RGB_CLOCK_TYPE")
        # Paused, bounded stepping keeps trigger physically impossible until the input passes.
        for target in range(200_000_000,2_000_000_001,200_000_000):
            gz_call(env,"smartdish_tray","pause: true multi_step: 200")
            deadline=time.monotonic()+25
            while state["clock"]<target:
                spin()
                if time.monotonic()>deadline:raise RuntimeError("A16_WARMUP_CLOCK_TIMEOUT")
            until=time.monotonic()+.35
            while time.monotonic()<until:spin(.02)
        # Allow asynchronous rendering and camera_info to drain while paused.
        until=time.monotonic()+3
        while time.monotonic()<until:spin(.03)
        need(bool(state["frames"]) and bool(state["infos"]),"A16_RGB_OR_CAMERA_INFO_MISSING")
        t0=max(state["frames"]);m=state["frames"][t0];ci=min(state["infos"].values(),key=lambda x:abs(x["stamp_ns"]-t0))
        need(m.width==640 and m.height==480 and m.encoding=="rgb8" and m.step==1920 and len(m.data)==640*480*3 and m.header.frame_id==FRAME,"A16_IMAGE_FORMAT")
        PILImage.frombytes("RGB",(640,480),bytes(m.data)).save(out/"tray_rgb_t0.png")
        dump(out/"capture.json",dict(stamp_ns=t0,frame_id=m.header.frame_id,encoding=m.encoding,width=m.width,height=m.height,image_sha256=sha256(out/"tray_rgb_t0.png"),camera_info=ci,source="ACTUAL_ROS_GZ_IMAGE_HEADER",pixel_sha256=hashlib.sha256(bytes(m.data)).hexdigest(),visual_review_required=True))
        tracks=load_poses(out/"poses.tsv",meta);ecm,overflow=read_ecm(out/"ecm_contact_steps.tsv");need(not overflow,"A16_ECM_OVERFLOW")
        initial=check_initial(tracks,meta,t0,ci,ecm);dump(out/"initial_validity.json",initial)
        if profile_record is not None:observe_server_profile(server,profile_record)
        print("A16_INITIAL_VALIDITY_PASS="+str(t0),flush=True)
        if not a.headless:
            try:
                gui=launch("gui",["gz","sim","-g","-v2"],gui_profile(env,"xcb_software"))
                until=time.monotonic()+1.0
                while time.monotonic()<until:spin()
                report["gui"]="FAIL" if gui.poll() is not None else "RUNNING"
            except (OSError,ValueError) as exc:report["gui"]="FAIL";report["gui_error"]=str(exc)
        else:report["gui"]="NOT_REQUESTED"
        # The plugin issues a fixed same-scene-independent pulse only at 2.2s.
        gz_call(env,"smartdish_tray","pause: false")
        deadline=time.monotonic()+210
        while state["clock"]<END_NS:
            spin()
            if gui and gui.poll() is not None:report["gui"]="FAIL"
            if time.monotonic()>deadline:raise RuntimeError("A16_OBSERVATION_TIMEOUT")
        gz_call(env,"smartdish_tray","pause: true")
        until=time.monotonic()+2
        while time.monotonic()<until:spin(.03)
        need(not state["overflow"] and max(state["frame_stamps"])>TRIGGER_NS,"A16_RAW_OVERFLOW_OR_NO_LIVE_RGB")
        tracks=load_poses(out/"poses.tsv",meta)
        report["trigger"]=check_trigger(out/"trigger.tsv")
        report["trigger"]["target_model"]=meta["initial_dishes"][-1]["name"]
        report["metrics"]=metrics(tracks,t0)
        ecm,overflow=read_ecm(out/"ecm_contact_steps.tsv");need(not overflow,"A16_ECM_OVERFLOW")
        expected=expected_sensors(out/"scenario.sdf");need(set(expected)==set(meta["contact_topics"]),"A16_CONTACT_TOPICS")
        refresh=evaluate(read_rows(out/"ecm_contact_steps.tsv"),list(expected),t0,END_NS)
        ok,transport=cross_check(expected,ecm,state["raw"],t0,END_NS)
        report.update(refresh=refresh,transport=transport,raw_ros_callbacks=len(state["raw"]),capture_ns=t0,observation_end_ns=END_NS,actual_clock_ns=state["clock"],observation_after_trigger_s=(END_NS-TRIGGER_NS)/1e9)
        need(refresh["refresh_contract_pass"] and ok,"A16_CONTACT_COMPONENT_OR_POSITIVE_MATCH")
        if gui and report["gui"]=="RUNNING":report["gui"]="PASS" if gui.poll() is None else "FAIL"
        report["registration"]=registration(out/"entity_registry.tsv",ecm,meta,report["trigger"])
        report["contact_diagnostic"]=transport_diagnostic(ecm,state["raw"],load_native(out/"native_contacts.tsv"),meta["contact_topics"],t0,END_NS)
        report["data_verdict"]="PASS"
        if profile_record is not None:observe_server_profile(server,profile_record,"runtime_observation_pre_shutdown")
        print("A16_REAL_CAPTURE_PASS_GT_HOLD="+a.scene,flush=True)
    except Exception as exc:
        report["first_error"]=type(exc).__name__+": "+str(exc)
        print("A16_FIRST_ERROR="+report["first_error"],flush=True)
    finally:
        (out/"ros_contacts.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in state["raw"]))
        dump(out/"clock_rgb_trace.json",dict(last_clock_ns=state["clock"],frame_stamps=state["frame_stamps"],overflow=state["overflow"]))
        if node:node.destroy_node()
        if initialized:rclpy.shutdown()
        rows=[]
        for role,p in reversed(procs):
            started=time.monotonic_ns()
            try:row=stop_owned(p)
            except Exception as exc:row=dict(pid=p.pid,returncode=p.poll(),stopped=p.poll() is not None,error=str(exc))
            row.update(role=role,cleanup_start_monotonic_ns=started,cleanup_end_monotonic_ns=time.monotonic_ns(),timeout_budget_s=18)
            try:os.killpg(p.pid,0);row["process_group_remaining"]=True
            except ProcessLookupError:row["process_group_remaining"]=False
            except PermissionError:row["process_group_remaining"]=True
            rows.append(row)
        for h in handles:h.close()
        report["processes"]=rows
        report["all_owned_stopped"]=bool(rows) and all(x["stopped"] and not x["process_group_remaining"] for x in rows)
        report["cleanup"]="PASS" if report["all_owned_stopped"] and all(x["returncode"]==0 for x in rows if x["role"]!="gui") else "FAIL"
        if report["gui"]=="PASS" and any(x["role"]=="gui" and x["returncode"]!=0 for x in rows):report["gui"]="FAIL"
        if report["gui"]=="RUNNING":report["gui"]="FAIL"
        if profile_record is not None:production_cleanup_result(profile_record,rows,report["data_verdict"],report["all_owned_stopped"])
        dump(out/"verdict.json",report);package(out)
    profile_ok=profile==INHERIT or report["server_runtime_profile"]["production_cleanup"]=="PASS"
    return 0 if report["data_verdict"]=="PASS" and report["all_owned_stopped"] and profile_ok else 2

def main():
    p=argparse.ArgumentParser();p.add_argument("--sha",required=True);p.add_argument("--scene",choices=SCENES,required=True);p.add_argument("--out",required=True,type=Path);p.add_argument("--pose-plugin",required=True,type=Path);p.add_argument("--health-plugin",required=True,type=Path);p.add_argument("--headless",action="store_true");p.add_argument("--native-tap",required=True,type=Path);p.add_argument("--source-class",choices=("CLOUD_CI","OWNER_WSL2"),required=True);p.add_argument("--server-profile",choices=PROFILES,default=INHERIT,help="Explicit A-only server profile; retain is Owner WSL2 only");a=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    need(len(a.sha)==40 and subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()==a.sha,"A16_PIN_MISMATCH")
    need(not subprocess.check_output(["git","-C",str(root),"status","--porcelain","--untracked-files=no"],text=True).strip(),"A16_TRACKED_DIRTY")
    need(a.pose_plugin.is_file() and a.health_plugin.is_file() and a.native_tap.is_file(),"A16_PLUGIN_MISSING")
    return run(a)
if __name__=="__main__":raise SystemExit(main())
