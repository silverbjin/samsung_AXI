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
from smartdish_tray_world import SCENARIOS, WORLD, TRAY_TOP, write_trial
from smartdish_tray_evidence import (
    digest, manifest, pose_from_transform, classify_motion,
    verify_timing, verify_trial,
)


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
    dish_names=[x["name"] for x in config["initial_dishes"]]
    env=os.environ.copy()
    # isolate Gazebo Transport and ROS DDS from current AI-OFF robot session
    env["GZ_PARTITION"]=f"smartdish_tray_{run_id}_{index}"
    env["ROS_DOMAIN_ID"]=str(55+(os.getpid()+index)%40)
    env["LIBGL_ALWAYS_SOFTWARE"]=env.get("LIBGL_ALWAYS_SOFTWARE","1")
    env["GALLIUM_DRIVER"]=env.get("GALLIUM_DRIVER","llvmpipe")
    directory_log=directory.parent/"logs"
    directory_log.mkdir(parents=True,exist_ok=True)
    handles=[]
    procs=[]
    node=None
    initialized=False
    state={"sim_ns":0,"frame":None,"frame_stamps":[],
           "poses":{},"traces":[],"pose_times":{}}
    failure=None

    def image_cb(msg):
        stamp=int(msg.header.stamp.sec)*1_000_000_000+int(msg.header.stamp.nanosec)
        if stamp<=0:
            return
        if state["frame_stamps"] and stamp<=state["frame_stamps"][-1]:
            return
        state["frame_stamps"].append(stamp)
        if state["frame"] is None:
            state["frame"]=msg

    def clock_cb(msg):
        now=int(msg.clock.sec)*1_000_000_000+int(msg.clock.nanosec)
        if now>state["sim_ns"]:
            state["sim_ns"]=now

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

    try:
        for name,cmd in [
            ("gazebo",["gz","sim","-s","-v2",str(sdf.resolve())]),
            ("bridge",["ros2","run","ros_gz_bridge","parameter_bridge",
                       "--ros-args","-p","config_file:="+
                       str((root/"config/smartdish_tray_bridge.yaml").resolve())]),
        ]:
            handle=(directory_log/(directory.name+"_"+name+".log")).open("w")
            handles.append(handle)
            procs.append(subprocess.Popen(cmd,env=env,stdout=handle,
                                          stderr=subprocess.STDOUT,start_new_session=True))
        if gui:
            handle=(directory_log/(directory.name+"_gui.log")).open("w")
            handles.append(handle)
            procs.append(subprocess.Popen(["gz","sim","-g","-v2"],env=env,
                         stdout=handle,stderr=subprocess.STDOUT,start_new_session=True))
        # The ROS node must share the exact DDS domain with the per-trial
        # bridge. A subprocess env alone does NOT change this parent's rclpy.
        rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]))
        initialized=True
        node=rclpy.create_node("smartdish_tray_capture_"+str(os.getpid())+"_"+str(index))
        node.create_subscription(Image,TOPIC,image_cb,qos_profile_sensor_data)
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

        # The first short steps make the sensor render *before* the 10s trial.
        # Do not silently capture an already-fallen after-image.
        # A 5 Hz camera's *first positive* frame commonly appears at t=0.2s.
        # 35 x 5 x 0.001s = 0.175s is insufficient. Step just far enough
        # to see an actual frame, but reject a late/post-fall capture.
        for _ in range(90):
            gz_call(env,WORLD,"pause: true multi_step: 5")
            for _ in range(4):
                spin(.06)
                if (state["frame"] is not None and
                    set(dish_names)<=set(state["poses"]) and
                    state["sim_ns"]>=int(state["frame"].header.stamp.sec)*1_000_000_000+
                                      int(state["frame"].header.stamp.nanosec)):
                    break
            if state["frame"] is not None and set(dish_names)<=set(state["poses"]):
                break
            if state["sim_ns"]>300_000_000:
                break
        if state["frame"] is None:
            topics=subprocess.run(["gz","topic","-l"],env=env,capture_output=True,
                                  text=True,timeout=8)
            seen=TOPIC in topics.stdout
            raise RuntimeError("A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE"
                               + " sim_ns="+str(state["sim_ns"])
                               + " GZ_IMAGE_TOPIC_ADVERTISED="+str(seen)
                               + " poses="+str(sorted(state["poses"])))
        msg=state["frame"]
        stamp=int(msg.header.stamp.sec)*1_000_000_000+int(msg.header.stamp.nanosec)
        if (stamp<=0 or stamp>300_000_000 or state["sim_ns"]>320_000_000):
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

        # Reuse B's *existing* capture / raw PNG converter, not a fake image.
        sys.path.insert(0,str(root/"ai/scripts"))
        from capture_tray_ros import save_unlabelled_frame
        private=root/"ai/data/private"/("A13_"+run_id+"_"+str(index)+".png")
        record=save_unlabelled_frame(msg,private,root,TOPIC)
        dst=directory/"tray_rgb.png"
        shutil.copyfile(private,dst)
        capture=dict(record)
        capture.update({"schema":2,"trial_id":config["trial_id"],
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

        # Only now unpause the actual physics simulation for 10 simulated s.
        observation_start_ns=state["sim_ns"]
        gz_call(env,WORLD,"pause: false")
        deadline=time.monotonic()+190
        while state["sim_ns"]-observation_start_ns<10_000_000_000:
            spin(.15)
            if time.monotonic()>deadline:
                raise RuntimeError("A13_TEN_SIM_SECONDS_OBSERVATION_TIMEOUT")
        gz_call(env,WORLD,"pause: true")
        for _ in range(6):
            spin(.1)
        observation_end_ns=state["sim_ns"]
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
        summary={
            "trial_id":config["trial_id"],"scene_id":scenario,"seed":seed,
            "source_sha":source_sha,"config_world_sha256":config["world_sha256"],
            "source_topic":TOPIC,"frame_id":FRAME,
            "width":msg.width,"height":msg.height,"encoding":msg.encoding,
            "image_sha256":digest(dst)[0],
            "physics_sha256":sha,"physics_size_bytes":sz,
            "pose_sample_count":len(rows),"image_received_count":len(state["frame_stamps"]),
            "motion":motion,"label":"REVIEW_REQUIRED","ground_truth":"NOT_OPERATOR_APPROVED",
            "verdict":"GAZEBO_PHYSICS_OBSERVED_REVIEW_REQUIRED",
            **timing}
        (directory/"trial_summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
        verify_trial(directory)
        return summary
    finally:
        if node is not None:
            node.destroy_node()
        if initialized and rclpy.ok():
            rclpy.shutdown()
        for p in reversed(procs):
            stop_owned(p)
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
    (dest/"source_manifest.json").write_text(json.dumps({
        "source_sha":local,"ros_distro":"jazzy","gz_major":"harmonic",
        "world":"smartdish_tray","ros_image_topic":TOPIC,
        "model_label_approval":"B_OPERATOR_ONLY",
        "scenario_ids":list(SCENARIOS)},indent=2)+"\n")
    print("SMARTDISH_A_TRAY_SOURCE_PIN_OK sha="+local,flush=True)
    scenarios=SCENARIOS if args.mode=="batch" else ("ST-01","UN-01") if args.mode=="demo" else (args.scene,)
    try:
        for i,scenario in enumerate(scenarios,1):
            print("SMARTDISH_A_TRAY_START_SCENARIO="+scenario,flush=True)
            row=run_trial(root,dest/("trial_%04d"%i),scenario,args.seed+i,
                          local,args.gui,i,run_id)
            summary["trials"].append(row)
        result={r["scene_id"]:r["motion"]["observation"] for r in summary["trials"]}
        if args.mode in ("batch","demo"):
            if not all(result.get(s)=="HELD_OBSERVED" for s in
                       (("ST-01","ST-02") if args.mode=="batch" else ("ST-01",))):
                raise RuntimeError("A13_STABLE_PHYSICS_NOT_VERIFIED")
            if not all(result.get(s)=="FALL_OBSERVED" for s in
                       (("UN-01","UN-02") if args.mode=="batch" else ("UN-01",))):
                raise RuntimeError("A13_UNSTABLE_PHYSICS_NOT_VERIFIED")
        summary["verdict"]="GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS"
        print("SMARTDISH_A_TRAY_PHYSICS_OBSERVATION_PASS",flush=True)
    except BaseException as exc:
        summary["verdict"]="FAIL"
        summary["first_error"]=str(exc)
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
    p.add_argument("mode",choices=("demo","single","batch"))
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
