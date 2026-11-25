#!/usr/bin/env python3
"""A-13 real Gazebo Harmonic trial orchestrator; no fake ROS or dummy result.

World starts paused. Short real-physics steps collect PRE_OBSERVATION RGB and
entity poses. Only after capture+snapshot are valid is physics unpaused for
10 simulated seconds. A slow/late camera fails closed (prevents post-fall
image leakage into B training). Each trial has fresh Gazebo+bridge+ROS domain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import time

from smartdish_tray_camera import TOPIC, FRAME, WIDTH, HEIGHT
from smartdish_tray_world import SCENARIOS, WORLD, TRAY_TOP, write_trial, split_scene_for_sensor_warmup
from smartdish_tray_evidence import (
    digest, manifest, pose_from_transform, classify_motion,
    verify_timing, verify_trial,
)


# A13 DBG-16: warm up an EMPTY tray in 100ms sim chunks, not 5ms
# synchronous Gazebo service RPCs. After dish spawn the existing short
# 5ms stepping and pre-fall capture cutoff remain unchanged.
EMPTY_TRAY_WARMUP_STEP_COUNT=100


def warmup_transport_metrics(state, start_wall, start_sim_ns, gz_probe_path, gz_rc):
    """Evidence only; actual two distinct ROS image stamps remain mandatory."""
    wall=max(0.0,time.monotonic()-start_wall)
    sim=max(0,state["sim_ns"]-start_sim_ns)
    return {
        "schema":1,"phase":"empty_tray_sensor_warmup",
        "step_count_per_request":EMPTY_TRAY_WARMUP_STEP_COUNT,
        "wall_elapsed_seconds":round(wall,3),
        "sim_advanced_ns":sim,
        "wall_seconds_per_sim_second":round(wall/(sim/1e9),3) if sim else None,
        "ros_image_callbacks_total":state["image_callbacks_total"],
        "ros_image_valid_stamps":list(state["frame_stamps"]),
        "ros_image_zero_stamps":state["image_zero_stamp"],
        "ros_image_repeated_stamps":state["image_repeated_stamp"],
        "ros_clock_advanced_total":state["clock_advances_total"],
        "gz_image_probe":image_probe_report(gz_probe_path,gz_rc),
        "requires_two_real_positive_increasing_ros_stamps":True,
    }


def pre_event_ready(frame, clock_ns, pose_names, required_names):
    """Pure guard: real positive Image stamp, all named dishes and ROS clock."""
    if frame is None or not set(required_names)<=set(pose_names):
        return False
    stamp=int(frame.header.stamp.sec)*1_000_000_000+int(frame.header.stamp.nanosec)
    return stamp>0 and int(clock_ns)>=stamp


def image_probe_report(path, returncode):
    """Report actual GZ CLI message bytes; process exit alone proves nothing."""
    p=Path(path)
    size=p.stat().st_size if p.is_file() else 0
    preview=b""
    if size:
        with p.open("rb") as f:
            preview=f.read(min(size,65536))
    # gz topic echo normally emits readable protobuf field names.
    # Keep a diagnostic only; the ROS callback remains the acceptance gate.
    return {"exit_code":returncode,"bytes":size,
            "sha256":digest(p)[0] if size else None,
            "contains_image_dimensions":(b"width:" in preview and
                                          b"height:" in preview),
            "evidence_file":p.name,
            "observed_gz_image_blocks":(p.read_bytes().count(b"\nwidth: ")
                                         if size else 0)}




def bounded_trace(events, entry, limit=128):
    """Keep first startup events and recent events with bounded memory."""
    events.append(entry)
    if len(events)>limit:
        del events[16:len(events)-112]


def diagnostic_boundary_probes(env, timeout_seconds=4):
    """Read-only graph/renderer probes after failure, never a PASS condition."""
    commands={
        "gazebo_image_topic_info":["gz","topic","-i","-t",TOPIC],
        "ros_image_topic_info":["ros2","topic","info","-v",TOPIC],
        "ros_topic_list":["ros2","topic","list","-t"],
    }
    if env.get("DISPLAY") and shutil.which("glxinfo"):
        commands["renderer_glxinfo"]=["glxinfo","-B"]
    rows={}
    for name,cmd in commands.items():
        begin=time.monotonic()
        try:
            result=subprocess.run(cmd,env=env,capture_output=True,text=True,
                                  errors="replace",timeout=timeout_seconds,
                                  stdin=subprocess.DEVNULL)
            rows[name]={"command":cmd,"returncode":result.returncode,
                        "elapsed_wall_seconds":round(time.monotonic()-begin,3),
                        "stdout":result.stdout[-8192:],
                        "stderr":result.stderr[-2048:],"timed_out":False}
        except subprocess.TimeoutExpired as err:
            rows[name]={"command":cmd,"returncode":None,
                        "elapsed_wall_seconds":round(time.monotonic()-begin,3),
                        "stdout":str(err.stdout or b"")[-2048:],
                        "stderr":str(err.stderr or b"")[-2048:],"timed_out":True}
        except Exception as err:
            rows[name]={"command":cmd,"returncode":None,
                        "elapsed_wall_seconds":round(time.monotonic()-begin,3),
                        "error":repr(err),"timed_out":False}
    return {"schema":1,"probe_type":"read_only_failure_boundary",
            "topic_advertisement_does_not_prove_image_receipt":True,
            "probes":rows}


def failure_snapshot(phase, error, state, env, processes, node, probe_path,
                     source_sha, scenario, seed, elapsed_wall_seconds):
    """Diagnostic only. Never treat advertised topics or sample bytes as PASS."""
    publishers = None
    endpoints = []
    endpoint_error = None
    if node is not None:
        try:
            publishers = node.count_publishers(TOPIC)
            for info in node.get_publishers_info_by_topic(TOPIC):
                qos = info.qos_profile
                endpoints.append({
                    "node_name": str(info.node_name),
                    "topic_type": str(info.topic_type),
                    "qos_reliability": str(qos.reliability),
                    "qos_durability": str(qos.durability)})
        except Exception as err:
            endpoint_error = repr(err)
    owned = []
    for proc in processes:
        try:
            code = proc.poll()
            owned.append({"pid": proc.pid, "returncode_at_failure": code,
                          "running_at_failure": code is None})
        except Exception as err:
            owned.append({"pid": getattr(proc, "pid", None),
                          "inspection_error": repr(err)})
    probe = None
    if probe_path is not None:
        try:
            probe = image_probe_report(probe_path, None)
        except Exception as err:
            probe = {"inspection_error": repr(err)}
    return {
        "schema": 1, "verdict": "FAIL", "stage": phase,
        "first_error": type(error).__name__ + ": " + str(error),
        "source_sha": source_sha, "scenario_id": scenario, "seed": seed,
        "wall_elapsed_seconds": round(elapsed_wall_seconds, 3),
        "diagnostic_monotonic_ns": time.monotonic_ns(),
        "diagnostic_utc_ns": time.time_ns(),
        "ros_domain_id": env.get("ROS_DOMAIN_ID"),
        "gz_partition": env.get("GZ_PARTITION"),
        "renderer_env": {k: env.get(k) for k in
            ("DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR",
             "LIBGL_ALWAYS_SOFTWARE", "GALLIUM_DRIVER",
             "MESA_D3D12_DEFAULT_ADAPTER_NAME", "GZ_SIM_RENDER_ENGINE")},
        "sim_ns": state.get("sim_ns"),
        "ros_clock_callbacks_total": state.get("clock_callbacks_total"),
        "ros_clock_advances_total": state.get("clock_advances_total"),
        "ros_clock_nonadvancing_total": state.get("clock_nonadvancing_total"),
        "ros_clock_last_progress_monotonic_ns": state.get("clock_last_progress_monotonic_ns"),
        "ros_clock_trace": list(state.get("clock_events", [])),
        "ros_image_callback_trace": list(state.get("image_events", [])),
        "ros_image_callbacks_total": state.get("image_callbacks_total"),
        "ros_image_zero_stamp": state.get("image_zero_stamp"),
        "ros_image_repeat_stamp": state.get("image_repeated_stamp"),
        "ros_image_before_spawn": state.get("image_before_spawn_count"),
        "ros_image_valid_stamps": list(state.get("frame_stamps", [])),
        "ros_image_last_stamp_ns": state.get("image_last_stamp_ns"),
        "ros_image_first_seen_monotonic": state.get("image_first_seen_wall"),
        "ros_image_publisher_count": publishers,
        "ros_image_publisher_endpoints": endpoints,
        "ros_endpoint_lookup_error": endpoint_error,
        "gz_image_probe": probe,
        "owned_processes_before_cleanup": owned,
    }


def stop_owned(proc):
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGINT)
        proc.wait(timeout=8)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait()


def gz_call(env, world, payload, timeout=15):
    cmd=["gz","service","-s",f"/world/{world}/control",
         "--reqtype","gz.msgs.WorldControl","--reptype","gz.msgs.Boolean",
         "--timeout",str(int(timeout*1000)),"--req",payload]
    r=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=timeout+4)
    if r.returncode!=0 or not re.search(r"(data\s*:\s*true|true)",r.stdout,re.I):
        raise RuntimeError("A13_GAZEBO_CONTROL_SERVICE_FAILED "+
                           (r.stderr.strip() or r.stdout.strip())[:240])
    return r.stdout


def gz_spawn_dynamic(env, world, item, timeout=18):
    """Spawn original dynamic model SDF through real Gazebo UserCommands."""
    from pathlib import Path
    path=Path(item["path"])
    if not path.is_file() or digest(path)[0]!=item["sha256"]:
        raise RuntimeError("A13_SPAWN_DISH_SDF_HASH_MISMATCH")
    req='sdf_filename: "'+str(path.resolve())+'", name: "'+item["name"]+'"'
    cmd=["gz","service","-s",f"/world/{world}/create",
         "--reqtype","gz.msgs.EntityFactory","--reptype","gz.msgs.Boolean",
         "--timeout",str(int(timeout*1000)),"--req",req]
    result=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=timeout+5)
    if result.returncode!=0 or not re.search(r"data\s*:\s*true",result.stdout,re.I):
        raise RuntimeError("A13_GAZEBO_DYNAMIC_ENTITY_SPAWN_REJECTED "
                           +item["name"]+" "+(result.stderr or result.stdout)[:200])
    return True


def run_trial(root:Path, directory:Path, scenario:str, seed:int,
              source_sha:str, gui:bool, index:int, run_id:str):
    import rclpy
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image
    from rosgraph_msgs.msg import Clock
    from tf2_msgs.msg import TFMessage

    directory.mkdir(parents=True,exist_ok=False)
    sdf=directory/"scenario.sdf"
    config=write_trial(scenario,seed,sdf,f"{run_id}_{index:02d}")
    sensor_world_sdf,spawn_manifest=split_scene_for_sensor_warmup(sdf)
    dish_names=[x["name"] for x in config["initial_dishes"]]
    env=os.environ.copy()
    # isolate Gazebo Transport and ROS DDS from current AI-OFF robot session
    env["GZ_PARTITION"]=f"smartdish_tray_{run_id}_{index}"
    env["ROS_DOMAIN_ID"]=str(55+(os.getpid()+index)%40)
    # CI explicitly sets Mesa llvmpipe; WSLg inherits its own GPU/Mesa
    # defaults. Do not unconditionally force slow llvmpipe on user's WSLg.
    # Users may still explicitly set either variable when diagnosing.
    directory_log=directory.parent/"logs"
    directory_log.mkdir(parents=True,exist_ok=True)
    handles=[]
    procs=[]
    node=None
    initialized=False
    state={"sim_ns":0,"frame":None,"frame_stamps":[],
           "min_image_stamp_ns":0,"image_before_spawn_count":0,
           "poses":{},"traces":[],"pose_times":{},
           "image_callbacks_total":0,"image_zero_stamp":0,
           "image_repeated_stamp":0,"image_first_seen_wall":None,
           "image_last_stamp_ns":None,
           "clock_callbacks_total":0,"clock_advances_total":0,
           "clock_nonadvancing_total":0,"clock_last_progress_monotonic_ns":None,
           "image_events":[],"clock_events":[]}
    gui_process=None
    probe_data_path=None
    failure=None
    trial_wall_start=time.monotonic()
    phase="initializing"

    def image_cb(msg):
        state["image_callbacks_total"]+=1
        stamp=int(msg.header.stamp.sec)*1_000_000_000+int(msg.header.stamp.nanosec)
        state["image_last_stamp_ns"]=stamp
        bounded_trace(state["image_events"],{
            "wall_monotonic_ns":time.monotonic_ns(),
            "sim_ns_at_callback":state["sim_ns"],
            "stamp_ns":stamp,"payload_bytes":len(msg.data),
            "width":int(msg.width),"height":int(msg.height),
            "encoding":str(msg.encoding),"frame_id":str(msg.header.frame_id),
            "phase":phase,
        })
        if state["image_first_seen_wall"] is None:
            state["image_first_seen_wall"]=time.monotonic()
        if stamp<=0:
            state["image_zero_stamp"]+=1
            return
        if stamp<=state["min_image_stamp_ns"]:
            state["image_before_spawn_count"]+=1
            return
        if state["frame_stamps"] and stamp<=state["frame_stamps"][-1]:
            state["image_repeated_stamp"]+=1
            return
        state["frame_stamps"].append(stamp)
        if state["frame"] is None:
            state["frame"]=msg

    def clock_cb(msg):
        now=int(msg.clock.sec)*1_000_000_000+int(msg.clock.nanosec)
        previous=state["sim_ns"]
        state["clock_callbacks_total"]+=1
        if now>previous:
            state["sim_ns"]=now
            state["clock_advances_total"]+=1
            state["clock_last_progress_monotonic_ns"]=time.monotonic_ns()
            samples=state["clock_events"]
            if not samples or now-samples[-1]["sim_ns"]>=100_000_000:
                bounded_trace(samples,{"sim_ns":now,
                                      "wall_monotonic_ns":time.monotonic_ns(),
                                      "phase":phase})
        else:
            state["clock_nonadvancing_total"]+=1

    def poses_cb(msg):
        now=state["sim_ns"]
        if now<=0:
            return
        for t in msg.transforms:
            row=pose_from_transform(t)
            if row is None:
                continue
            name,pose=row
            if name not in dish_names:
                continue
            previous=state["pose_times"].get(name,-1)
            if now>previous and (previous<0 or now-previous>=50_000_000):
                state["traces"].append({"sim_ns":now,"entity":name,"pose":pose,
                                        "source":"ROS_BRIDGED_GAZEBO_DYNAMIC_POSE"})
                state["poses"][name]=pose
                state["pose_times"][name]=now

    def spin(seconds=.15):
        if any(p.poll() is not None for p in procs[:2]):
            raise RuntimeError("A13_OWNED_GAZEBO_OR_BRIDGE_EXITED")
        rclpy.spin_once(node,timeout_sec=seconds)

    phase="launch_gazebo_bridge"
    try:
        for name,cmd in [
            ("gazebo",["gz","sim","-s","-v2",str(sensor_world_sdf.resolve())]),
            ("bridge",["ros2","run","ros_gz_bridge","parameter_bridge",
                       "--ros-args","-p","config_file:="+
                       str((root/"config/smartdish_tray_bridge.yaml").resolve())]),
        ]:
            handle=(directory_log/(directory.name+"_"+name+".log")).open("w")
            handles.append(handle)
            procs.append(subprocess.Popen(cmd,env=env,stdout=handle,
                                          stderr=subprocess.STDOUT,start_new_session=True))
        print("A13_RENDER_ENV_DIAGNOSTICS="+json.dumps({
            "gui_requested":gui,
            "display_set":bool(env.get("DISPLAY")),
            "wayland_display_set":bool(env.get("WAYLAND_DISPLAY")),
            "xdg_runtime_dir_set":bool(env.get("XDG_RUNTIME_DIR")),
            "libgl_always_software":env.get("LIBGL_ALWAYS_SOFTWARE"),
            "gallium_driver":env.get("GALLIUM_DRIVER"),
            "gz_sim_render_engine":env.get("GZ_SIM_RENDER_ENGINE"),
            "ros_domain_id":env["ROS_DOMAIN_ID"],
            "gz_partition":env["GZ_PARTITION"]},sort_keys=True),flush=True)
        # GUI deliberately starts AFTER genuine pre-observation RGB capture.
        # It remains active during physics and must receive subsequent frames.
        # WSLg Ogre/Qt UI initialization cannot starve the first sensor frame.
        # The ROS node must share the exact DDS domain with the per-trial
        # bridge. A subprocess env alone does NOT change this parent's rclpy.
        rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]))
        initialized=True
        node=rclpy.create_node("smartdish_tray_capture_"+str(os.getpid())+"_"+str(index))
        # Observed WSLg bridge publishes RELIABLE (DBG-16 original evidence).
        # Request RELIABLE delivery of 640x480 RGB, rather than silently
        # dropping fragmented frames with BEST_EFFORT sensor_data QoS.
        # No synthetic/replayed frames; only new ROS callbacks count.
        image_qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
        node.create_subscription(Image,TOPIC,image_cb,image_qos)
        for name in dish_names:
            node.create_subscription(TFMessage,"/smartdish/tray/pose/"+name,
                                     poses_cb,qos_profile_sensor_data)
        node.create_subscription(Clock,"/clock",clock_cb,QoSProfile(depth=10))
        start=time.monotonic()
        while time.monotonic()-start<75:
            spin()
            r=subprocess.run(["gz","service","-l"],env=env,
                             capture_output=True,text=True,timeout=7)
            if r.returncode==0 and f"/world/{WORLD}/control" in r.stdout:
                break
        else:
            raise RuntimeError("A13_WORLD_CONTROL_NOT_READY_NO_CAPTURE")

        # The renderer, bridge and ROS graph start on wall time; the 5Hz
        # camera is gated by simulation time. Give DDS discovery its own
        # bounded wall-time barrier *before* advancing physical dish poses.
        phase="dds_discovery"
        discovery_deadline=time.monotonic()+12.0
        while node.count_publishers(TOPIC)==0 and time.monotonic()<discovery_deadline:
            spin(.15)
        if node.count_publishers(TOPIC)==0:
            raise RuntimeError("A13_ROS_IMAGE_BRIDGE_PUBLISHER_NOT_READY"
                               " gz_partition="+env["GZ_PARTITION"]
                               +" ros_domain="+env["ROS_DOMAIN_ID"])

        # Independent Gazebo transport probe. This is ONLY diagnostics:
        # exit=0 means one real gz Image was emitted, not a ROS frame.
        # Never synthesize a ROS Image or mark a test PASS from topic adverts.
        gz_probe_log=(directory_log/(directory.name+"_gz_image_probe.log")).open("w")
        handles.append(gz_probe_log)
        probe_data_path=directory_log/(directory.name+"_gz_image_probe_data.txt")
        probe_data=probe_data_path.open("wb")
        handles.append(probe_data)
        probe=subprocess.Popen(
            ["gz","topic","-e","-n","2","-t",TOPIC],
            env=env,stdin=subprocess.DEVNULL,stdout=probe_data,
            stderr=gz_probe_log,start_new_session=True)
        procs.append(probe)

        # Stage 1: PRE-WARM the actual camera and ROS bridge with NO
        # dynamic dishes. Missed first 5Hz frames cannot bias dataset X.
        phase="sensor_warmup"
        warmup_start_wall=time.monotonic()
        warmup_start_sim_ns=state["sim_ns"]
        warmup_deadline=warmup_start_wall+75.0
        for _ in range(100):
            if len(state["frame_stamps"])>=2:
                break
            if time.monotonic()>warmup_deadline:
                break
            gz_call(env,WORLD,
                    "pause: true multi_step: "+str(EMPTY_TRAY_WARMUP_STEP_COUNT))
            # Drain the reliable image transport after stepping; clock and
            # camera callbacks can arrive on different executor cycles.
            for _ in range(6):
                spin(.12)
                if len(state["frame_stamps"])>=2:
                    break
        warmup_metrics=warmup_transport_metrics(
            state,warmup_start_wall,warmup_start_sim_ns,probe_data_path,probe.poll())
        (directory/"warmup_transport_metrics.json").write_text(
            json.dumps(warmup_metrics,indent=2,sort_keys=True)+"\n")
        print("A13_SENSOR_WARMUP_TRANSPORT_METRICS="+
              json.dumps(warmup_metrics,sort_keys=True),flush=True)
        if len(state["frame_stamps"])<2:
            # Fail closed: neither GZ sample count nor a single ROS image
            # substitutes for two NEW, positive, increasing ROS stamps.
            raise RuntimeError("A13_REAL_CAMERA_BRIDGE_WARMUP_NO_TWO_IMAGES")
        print("SMARTDISH_A_TRAY_SENSOR_WARMUP_PASS image_stamps="+
              str(state["frame_stamps"][-2:]),flush=True)

        # Stage 2: spawn the unchanged real physical dishes, then capture
        # a FRESH image/pose. Neither the previous empty-tray RGB nor late
        # duplicate messages can be training X.
        phase="dynamic_dish_spawn"
        stage_start_ns=state["sim_ns"]
        state["min_image_stamp_ns"]=stage_start_ns
        state["frame"]=None
        state["frame_stamps"]=[]
        state["poses"]={}
        state["pose_times"]={}
        state["traces"]=[]
        for item in spawn_manifest["spawned_dynamic_models"]:
            gz_spawn_dynamic(env,WORLD,item)
        print("SMARTDISH_A_TRAY_DYNAMIC_SPAWN_REQUESTS_OK count="+
              str(len(dish_names)),flush=True)
        # Bounded fresh GZ probe AFTER EntityFactory, distinct from warmup.
        # This disambiguates render stalls from bridge/DDS delivery stalls.
        gz_post_log=(directory_log/(directory.name+"_post_spawn_gz_probe.log")).open("w")
        handles.append(gz_post_log)
        gz_post_path=directory_log/(directory.name+"_post_spawn_gz_probe_data.txt")
        gz_post_stream=gz_post_path.open("wb")
        handles.append(gz_post_stream)
        gz_post_proc=subprocess.Popen(
            ["gz","topic","-e","-n","2","-t",TOPIC],env=env,
            stdin=subprocess.DEVNULL,stdout=gz_post_stream,
            stderr=gz_post_log,start_new_session=True)
        procs.append(gz_post_proc)
        state["post_spawn_gz_path"]=str(gz_post_path)

        def camera_ready():
            return pre_event_ready(state["frame"],state["sim_ns"],
                                   state["poses"],dish_names)

        phase="post_spawn_camera_pose"
        capture_deadline=time.monotonic()+50.0
        for _ in range(100):
            if camera_ready():
                break
            if time.monotonic()>capture_deadline:
                break
            gz_call(env,WORLD,"pause: true multi_step: 5")
            for _ in range(4):
                spin(.075)
                if camera_ready():
                    break
            if camera_ready():
                break
            if state["sim_ns"]-stage_start_ns>=180_000_000:
                for _ in range(12):
                    spin(.10)
                    if camera_ready():
                        break
            if camera_ready():
                break
            # At 5Hz allow the second *post-spawn* camera period when
            # Gazebo must rebuild its render scene after EntityFactory.
            # Actual capture-time dish displacement still gates the sample.
            if state["sim_ns"]-stage_start_ns>510_000_000:
                break

        if not camera_ready():
            diagnostics=dict(
                sim_ns=state["sim_ns"],
                gz_image_topic_advertised=TOPIC in subprocess.run(
                    ["gz","topic","-l"],env=env,capture_output=True,
                    text=True,timeout=8).stdout,
                gz_image_frame_probe_exit=probe.poll(),
                gz_probe=image_probe_report(probe_data_path,probe.poll()),
                ros_image_publishers=node.count_publishers(TOPIC),
                ros_image_callbacks=state["image_callbacks_total"],
                ros_zero_stamp_callbacks=state["image_zero_stamp"],
                ros_repeat_stamp_callbacks=state["image_repeated_stamp"],
                ros_first_positive_stamp=state["frame_stamps"][0]
                    if state["frame_stamps"] else None,
                ros_last_image_stamp=state["image_last_stamp_ns"],
                post_spawn_gz_probe=image_probe_report(
                    Path(state["post_spawn_gz_path"]),gz_post_proc.poll()),
                post_spawn_clock_advanced_ns=state["sim_ns"]-stage_start_ns,
                post_spawn_ros_callback_count=sum(
                    x["phase"]=="post_spawn_camera_pose"
                    for x in state["image_events"]),
                poses=sorted(state["poses"]),
                expected_dishes=dish_names)
            print("A13_CAMERA_FIRST_FRAME_DIAGNOSTICS="+
                  json.dumps(diagnostics,sort_keys=True),flush=True)
            if state["frame"] is None:
                post_gz_frames=diagnostics["post_spawn_gz_probe"]["observed_gz_image_blocks"]
                boundary=("A13_POST_SPAWN_GZ_IMAGE_NOT_OBSERVED"
                          if post_gz_frames<1 else "A13_POST_SPAWN_GZ_TO_ROS_NOT_OBSERVED")
                raise RuntimeError("A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE"
                                   " boundary="+boundary+
                                   " evidence="+json.dumps(diagnostics,sort_keys=True))
            raise RuntimeError("A13_PRE_EVENT_IMAGE_POSE_CLOCK_NOT_SYNCHRONIZED"
                               " evidence="+json.dumps(diagnostics,sort_keys=True))
        ready_diag={
            "sim_ns":state["sim_ns"],
            "image_callbacks":state["image_callbacks_total"],
            "image_zero_stamp":state["image_zero_stamp"],
            "image_repeated_stamp":state["image_repeated_stamp"],
            "gz_real_image_probe_exit":probe.poll(),
            "gz_probe":image_probe_report(probe_data_path,probe.poll()),
            "ros_image_publishers":node.count_publishers(TOPIC),
            "pose_names":sorted(state["poses"]),
        }
        print("A13_CAMERA_READY_DIAGNOSTICS="+
              json.dumps(ready_diag,sort_keys=True),flush=True)
        msg=state["frame"]
        stamp=int(msg.header.stamp.sec)*1_000_000_000+int(msg.header.stamp.nanosec)
        if (stamp<=stage_start_ns or stamp-stage_start_ns>500_000_000 or
                state["sim_ns"]-stage_start_ns>520_000_000):
            raise RuntimeError("A13_PRE_EVENT_CAMERA_TOO_LATE_NO_VALID_TRAINING_INPUT")
        if not set(dish_names)<=set(state["poses"]):
            raise RuntimeError("A13_GAZEBO_NAMED_POSE_BRIDGE_NO_DISH"
                               + " actual="+str(sorted(state["poses"]))
                               + " expected="+str(dish_names))
        if (int(msg.width),int(msg.height))!=(WIDTH,HEIGHT) or msg.encoding.lower() not in ("rgb8","bgr8"):
            raise RuntimeError("A13_LIVE_IMAGE_DIMENSION_OR_ENCODING_MISMATCH")
        if msg.header.frame_id!=FRAME:
            raise RuntimeError("A13_LIVE_CAMERA_FRAME_MISMATCH_"+str(msg.header.frame_id))
        snapshot={n:dict(state["poses"][n]) for n in dish_names}
        # An input image after an actual fall is label leakage. The camera
        # startup may advance physics slightly: compare observed capture pose
        # against the configured initial pose, NOT a guessed stable label.
        by_name={x["name"]:x for x in config["initial_dishes"]}
        if any((by_name[n]["z"]-snapshot[n]["z"]>.24 or
                snapshot[n]["z"]<TRAY_TOP-.08) for n in dish_names):
            raise RuntimeError("A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED")
        pose_at_capture_ns=max(state["pose_times"][n] for n in dish_names)
        if abs(pose_at_capture_ns-stamp)>250_000_000:
            raise RuntimeError("A13_IMAGE_POSE_STAMP_MISMATCH")
        print("SMARTDISH_A_TRAY_CAMERA_LIVE_PASS trial="+directory.name+
              " stamp_ns="+str(stamp),flush=True)
        print("A13_POST_SPAWN_RGB_POSE_CLOCK_PASS="+json.dumps({
            "scene_id":scenario,"spawn_sim_ns":stage_start_ns,
            "capture_stamp_ns":stamp,"pose_stamp_ns":pose_at_capture_ns,
            "clock_sim_ns":state["sim_ns"],
            "post_spawn_ros_image_stamps":list(state["frame_stamps"]),
            "post_spawn_gz_probe":image_probe_report(
                Path(state["post_spawn_gz_path"]),gz_post_proc.poll())
        },sort_keys=True),flush=True)

        # Reuse B's *existing* capture / raw PNG converter, not a fake image.
        sys.path.insert(0,str(root/"ai/scripts"))
        from capture_tray_ros import save_unlabelled_frame
        private=root/"ai/data/private"/("A13_"+run_id+"_"+str(index)+".png")
        record=save_unlabelled_frame(msg,private,root,TOPIC)
        dst=directory/"tray_rgb.png"
        shutil.copyfile(private,dst)
        capture=dict(record)
        capture.update({"schema":2,"trial_id":config["trial_id"],
                        "dynamic_spawn_world_manifest": "sensor_preflight_manifest.json",
                        "pre_observation_spawn_sim_ns":stage_start_ns,
                        "image_sha256":digest(dst)[0],
                        "source": "GAZEBO_REAL_SENSOR_NOT_LABELLED",
                        "pre_observation_capture":True,
                        "private_b_capture":str(private)})
        (directory/"capture_metadata.json").write_text(
            json.dumps(capture,indent=2,sort_keys=True)+"\n")
        (directory/"initial_state.json").write_text(
            json.dumps({"stamp_ns":stamp,"pose_stamp_ns":pose_at_capture_ns,
                        "dishes":snapshot,"scenario_sha256":config["world_sha256"]},
                       indent=2,sort_keys=True)+"\n")
        print("SMARTDISH_A_TRAY_RGB_CAPTURE_PASS trial="+directory.name,flush=True)
        # Only the GUI inherits XWayland/XCB changes; user-selected D3D12
        # and NVIDIA adapter remain untouched. ROS/GZ sensor server stays
        # on its original environment/partition.
        from smartdish_a_tray_gui_preflight import gui_profile_env
        gui_env=gui_profile_env(
            env,os.environ.get("SMARTDISH_A_TRAY_GUI_PROFILE","native")) if gui else None
        phase="gui_client_start"
        if gui:
            handle=(directory_log/(directory.name+"_gui.log")).open("w")
            handles.append(handle)
            gui_process=subprocess.Popen(
                ["gz","sim","-g","-v2"],env=gui_env,stdout=handle,
                stderr=subprocess.STDOUT,start_new_session=True)
            procs.append(gui_process)
            # A real GUI client must be alive when physical observation starts.
            # The actual server camera is checked again during the 10-sim-s phase.
            for _ in range(10):
                spin(.10)
                if gui_process.poll() is not None:
                    raise RuntimeError("A13_GAZEBO_GUI_START_FAILED_RC="+
                                       str(gui_process.returncode))
            print("SMARTDISH_A_TRAY_GUI_CLIENT_STARTED",flush=True)

        # Only now unpause the actual physics simulation for 10 simulated s.
        phase="physics_observation"
        observation_start_ns=state["sim_ns"]
        gz_call(env,WORLD,"pause: false")
        deadline=time.monotonic()+190
        gui_failure_reason=None
        gui_failure_sim_ns=None
        while state["sim_ns"]-observation_start_ns<10_000_000_000:
            spin(.15)
            if gui and gui_failure_reason is None and gui_process.poll() is not None:
                # Preserve true camera/physics data even if the GUI dies.
                # Do not promote the combined GUI qualification to PASS.
                gui_failure_reason="A13_GAZEBO_GUI_EARLY_EXIT_RC="+str(gui_process.returncode)
                gui_failure_sim_ns=state["sim_ns"]
                print("A13_GUI_FAILURE_SENSOR_CONTINUES="+gui_failure_reason,flush=True)
            if time.monotonic()>deadline:
                raise RuntimeError("A13_TEN_SIM_SECONDS_OBSERVATION_TIMEOUT")
        gz_call(env,WORLD,"pause: true")
        for _ in range(6):
            spin(.1)
        observation_end_ns=state["sim_ns"]
        if gui:
            if gui_process.poll() is not None and gui_failure_reason is None:
                gui_failure_reason="A13_GAZEBO_GUI_EARLY_EXIT_RC="+str(gui_process.returncode)
                gui_failure_sim_ns=state["sim_ns"]
            if not state["frame_stamps"] or state["frame_stamps"][-1]<=stamp:
                raise RuntimeError("A13_GUI_ACTIVE_BUT_NO_LIVE_RGB_FRAMES")
            if gui_failure_reason is None:
                print("SMARTDISH_A_TRAY_GUI_LIVE_RGB_PASS last_stamp_ns="+
                      str(state["frame_stamps"][-1]),flush=True)
            else:
                print("SMARTDISH_A_TRAY_SENSOR_CONTINUED_AFTER_GUI_EXIT",flush=True)
        final={n:dict(state["poses"][n]) for n in dish_names if n in state["poses"]}
        motion=classify_motion(snapshot,final,dish_names,TRAY_TOP)
        rows=[x for x in state["traces"] if x["entity"] in dish_names]
        physics=directory/"physics_observations.jsonl"
        physics.write_text("".join(json.dumps(x,sort_keys=True)+"\n" for x in rows))
        (directory/"final_state.json").write_text(
            json.dumps({"observation_end_ns":observation_end_ns,
                        "dishes":final,"motion":motion},indent=2,sort_keys=True)+"\n")
        print("SMARTDISH_A_TRAY_PHYSICS_OBSERVED trial="+directory.name+
              " outcome="+motion["observation"],flush=True)
        # Always require frame evolution and genuine pose history; do not
        # substitute scenario hint for observed movement.
        timing=dict(capture_stamp_ns=stamp, observation_start_ns=observation_start_ns,
                    observation_end_ns=observation_end_ns,
                    pose_at_capture_ns=pose_at_capture_ns,
                    image_stamp_samples=state["frame_stamps"])
        # Explicit mapping from *evidence schema* keys to verify_timing()
        # positional API: capture_ns, start_ns, end_ns, pose_ns, frame_ns.
        verify_timing(stamp, observation_start_ns, observation_end_ns,
                      pose_at_capture_ns, state["frame_stamps"])
        sha,sz=digest(physics)
        phase="evidence_verification"
        summary={
            "ros_domain_id":env["ROS_DOMAIN_ID"],
            "gz_partition":env["GZ_PARTITION"],
            "trial_id":config["trial_id"],"scene_id":scenario,"seed":seed,
            "source_sha":source_sha,"config_world_sha256":config["world_sha256"],
            "source_topic":TOPIC,"frame_id":FRAME,
            "width":msg.width,"height":msg.height,"encoding":msg.encoding,
            "image_sha256":digest(dst)[0],
            "physics_sha256":sha,"physics_size_bytes":sz,
            "pose_sample_count":len(rows),"image_received_count":len(state["frame_stamps"]),
            "trial_wall_elapsed_seconds":round(time.monotonic()-trial_wall_start,3),
            "post_spawn_gz_probe":image_probe_report(
                Path(state["post_spawn_gz_path"]),gz_post_proc.poll()),
            "motion":motion,
            "sensor_physics_verdict":"PASS",
            "gui_verdict":("NOT_REQUESTED" if not gui else
                           "FAIL" if gui_failure_reason else "PASS"),
            "gui_failure_reason":gui_failure_reason,
            "gui_exit_sim_ns":gui_failure_sim_ns,
            "gui_profile":os.environ.get("SMARTDISH_A_TRAY_GUI_PROFILE","native") if gui else None,
            "gui_active_during_physics":bool(gui and gui_failure_reason is None),
            "pre_observation_spawn_sim_ns":stage_start_ns,
            "actual_runtime_world_sha256":spawn_manifest["sensor_preflight_sha256"],
            "dynamic_spawn_sha256":{x["name"]:x["sha256"] for x in
                                     spawn_manifest["spawned_dynamic_models"]},
            "gz_probe":image_probe_report(probe_data_path,probe.poll()),
            "label":"REVIEW_REQUIRED","ground_truth":"NOT_OPERATOR_APPROVED",
            "verdict":"GAZEBO_PHYSICS_OBSERVED_REVIEW_REQUIRED",
            **timing}
        (directory/"trial_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        verify_trial(directory)
        if gui_failure_reason is not None:
            # SENSOR_PHYSICS PASS is independently preserved in the real
            # trial_summary, but the GUI-required overall gate remains FAIL.
            raise RuntimeError(gui_failure_reason)
        return summary
    except BaseException as exc:
        try:
            diagnostic=failure_snapshot(
                phase,exc,state,env,procs,node,probe_data_path,
                source_sha,scenario,seed,time.monotonic()-trial_wall_start)
            if state.get("post_spawn_gz_path"):
                diagnostic["post_spawn_gz_probe"]=image_probe_report(
                    Path(state["post_spawn_gz_path"]),None)
            diag_path=directory/"failure_diagnostics.json"
            diag_path.write_text(json.dumps(diagnostic,indent=2,sort_keys=True)+"\n")
            print("A13_FAILURE_DIAGNOSTICS_PATH="+str(diag_path),flush=True)
            try:
                probes=diagnostic_boundary_probes(env)
                (directory/"transport_boundary_probes.json").write_text(
                    json.dumps(probes,indent=2,sort_keys=True)+"\n")
                print("A13_TRANSPORT_BOUNDARY_PROBES_SAVED",flush=True)
            except Exception as probe_error:
                print("A13_TRANSPORT_BOUNDARY_PROBES_FAILED="+repr(probe_error),
                      flush=True)
        except Exception as diagnostic_error:
            print("A13_FAILURE_DIAGNOSTICS_WRITE_FAILED="+repr(diagnostic_error),
                  flush=True)
        raise
    finally:
        if node is not None:
            node.destroy_node()
        if initialized and rclpy.ok():
            rclpy.shutdown()
        cleanup=[]
        for p in reversed(procs):
            stop_owned(p)
            cleanup.append({"pid":p.pid,"returncode_after_cleanup":p.poll(),
                            "stopped":p.poll() is not None})
        (directory/"process_cleanup.json").write_text(
            json.dumps({"source_sha":source_sha,"scenario_id":scenario,
                        "ros_domain_id":env["ROS_DOMAIN_ID"],
                        "gz_partition":env["GZ_PARTITION"],
                        "owned_processes":cleanup,
                        "all_owned_processes_stopped":all(x["stopped"] for x in cleanup)},
                       indent=2,sort_keys=True)+"\n")
        for h in handles:
            h.close()


def run(args):
    root=Path(__file__).resolve().parents[1]
    # CI checkout ownership may differ from container UID; only trust this exact
    # checkout path in a single git invocation, never globally whitelist Git.
    local=subprocess.check_output(
        ["git","-C",str(root),"-c","safe.directory="+str(root),"rev-parse","HEAD"],
        text=True,timeout=8).strip()
    if not re.fullmatch("[0-9a-f]{40}",local) or local!=args.expected_sha:
        raise RuntimeError("A13_SOURCE_SHA_PIN_MISMATCH_NO_GOAL")
    if args.gui and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        raise RuntimeError("A13_WSLG_DISPLAY_MISSING")
    from datetime import datetime,timezone
    utc=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id=utc+"_"+str(os.getpid())
    dest=root/"generated/smartdish_tray"/("run_"+run_id)
    dest.mkdir(parents=True,exist_ok=False)
    summary={"schema":1,"source_sha":local,"mode":args.mode,
             "gui":args.gui,"verdict":"NOT_RUN",
             "ground_truth":"B_HUMAN_REVIEW_REQUIRED","trials":[],
             "first_error":None}
    if os.environ.get("SMARTDISH_A_TRAY_GATE_MANIFEST"):
        gate=json.loads(Path(os.environ["SMARTDISH_A_TRAY_GATE_MANIFEST"]).read_text())
        if (gate.get("source_sha")!=local or
                gate.get("status")!="REAL_WSLG_SMOKE_PASS" or
                args.mode!="batch"):
            raise RuntimeError("A13_DEPLOYMENT_GATE_MANIFEST_NOT_APPROVED")
        (dest/"deployment_gate_manifest.json").write_text(
            json.dumps(gate,indent=2,sort_keys=True)+"\n")
    (dest/"source_manifest.json").write_text(json.dumps({
        "source_sha":local,"ros_distro":"jazzy","gz_major":"harmonic",
        "world":"smartdish_tray","ros_image_topic":TOPIC,
        "model_label_approval":"B_OPERATOR_ONLY",
        "scenario_ids":list(SCENARIOS)},indent=2)+"\n")
    print("SMARTDISH_A_TRAY_SOURCE_PIN_OK sha="+local,flush=True)
    scenarios=SCENARIOS if args.mode=="batch" else ("ST-02","UN-01") if args.mode=="smoke" else ("ST-01","UN-01") if args.mode=="demo" else (args.scene,)
    try:
        for i,scenario in enumerate(scenarios,1):
            print("SMARTDISH_A_TRAY_START_SCENARIO="+scenario,flush=True)
            row=run_trial(root,dest/("trial_%04d"%i),scenario,args.seed+i,
                          local,args.gui,i,run_id)
            summary["trials"].append(row)
        result={r["scene_id"]:r["motion"]["observation"] for r in summary["trials"]}
        if args.mode=="smoke":
            if [r["scene_id"] for r in summary["trials"]]!=["ST-02","UN-01"]:
                raise RuntimeError("A13_SMOKE_SCENARIO_ORDER_INVALID")
            if [r["motion"]["observation"] for r in summary["trials"]]!=[
                    "HELD_OBSERVED","FALL_OBSERVED"]:
                raise RuntimeError("A13_SMOKE_PHYSICS_NOT_VERIFIED")
            summary["verdict"]="ST02_UN01_REAL_CAMERA_SMOKE_PASS"
            print("SMARTDISH_A_TRAY_ST02_UN01_SMOKE_PASS_NO_L3",flush=True)
        if args.mode in ("batch","demo"):
            if not all(result.get(s)=="HELD_OBSERVED" for s in
                       (("ST-01","ST-02") if args.mode=="batch" else ("ST-01",))):
                raise RuntimeError("A13_STABLE_PHYSICS_NOT_VERIFIED")
            if not all(result.get(s)=="FALL_OBSERVED" for s in
                       (("UN-01","UN-02") if args.mode=="batch" else ("UN-01",))):
                raise RuntimeError("A13_UNSTABLE_PHYSICS_NOT_VERIFIED")
        if args.mode!="smoke":
            summary["verdict"]="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS"
            print("SMARTDISH_A_TRAY_PHYSICS_OBSERVATION_PASS",flush=True)
    except BaseException as exc:
        summary["verdict"]="FAIL"
        summary["first_error"]=str(exc)
        import traceback
        partial_dir=dest/("trial_%04d"%i)
        partial_path=partial_dir/"trial_summary.json"
        partial=(json.loads(partial_path.read_text())
                 if partial_path.exists() else None)
        summary["partial_trial_sensor_physics_verdict"]=(
            partial.get("sensor_physics_verdict") if partial else "NOT_VERIFIED")
        summary["partial_trial_gui_verdict"]=(
            partial.get("gui_verdict") if partial else "NOT_VERIFIED")
        (dest/"failure_context.json").write_text(json.dumps({
            "schema":1,"verdict":"FAIL","source_sha":local,
            "sensor_physics_verdict":summary["partial_trial_sensor_physics_verdict"],
            "gui_verdict":summary["partial_trial_gui_verdict"],
            "first_error":str(exc),"traceback":traceback.format_exc(),
            "mode":args.mode,"gui":args.gui,
            "completed_trial_count":len(summary["trials"])},
            ensure_ascii=False,indent=2,sort_keys=True)+"\n")
        print("SMARTDISH_A_TRAY_FIRST_FAILURE="+str(exc),flush=True)
        raise
    finally:
        (dest/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
        rows=manifest(dest)
        (dest/"SHA256SUMS").write_text("".join(
            r["sha256"]+"  "+r["path"]+"\n" for r in rows))
        archive=dest/"smartdish_a_tray_evidence.tar.gz"
        with tarfile.open(archive,"w:gz") as out:
            for item in sorted(dest.rglob("*")):
                if item.is_file() and item!=archive:
                    out.add(item,arcname=item.relative_to(dest))
        print("SMARTDISH_A_TRAY_EVIDENCE_BUNDLE="+str(archive.resolve()),flush=True)
        if summary["verdict"]=="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS":
            print("SMARTDISH_A_TRAY_EVIDENCE_EXPORT_PASS",flush=True)
            if args.mode=="batch" and len(summary["trials"])==4:
                if os.environ.get("WSL_DISTRO_NAME"):
                    print("SMARTDISH_A_TRAY_WSL2_L3_PASS",flush=True)
                else:
                    print("SMARTDISH_A_TRAY_GAZEBO_L2_PASS",flush=True)
            else:
                print("SMARTDISH_A_TRAY_PARTIAL_SCENARIOS_ONLY_NO_L3",flush=True)


def shlex_quote(x):
    import shlex
    return shlex.quote(x)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("demo","single","batch","smoke"))
    p.add_argument("--scene",choices=SCENARIOS,default="ST-01")
    p.add_argument("--seed",type=int,default=101)
    p.add_argument("--expected-sha",required=True)
    group=p.add_mutually_exclusive_group()
    group.add_argument("--gui",dest="gui",action="store_true")
    group.add_argument("--headless",dest="gui",action="store_false")
    p.set_defaults(gui=True)
    args=p.parse_args()
    if args.seed<0 or args.seed>2**31-100:
        p.error("Invalid seed")
    run(args)


if __name__=="__main__":
    main()
