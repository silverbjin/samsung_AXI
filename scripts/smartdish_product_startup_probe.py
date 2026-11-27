#!/usr/bin/env python3
"""CI-only startup witness: actual single restaurant world, NO navigation goal.

A second *read-only table witness camera* exists only in CI copy of the world,
not the product world or AI topic. It is not an independent station.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from xml.etree import ElementTree as ET
import yaml
from smartdish_product_scene import generate as generate_scene
from smartdish_product_robot import generate as generate_robot
from smartdish_tray_camera import add_camera

TABLE_TOPIC = "/smartdish/a_product_ci/table_image"
TRAY_TOPIC = "/smartdish/tray/image_raw"

def scene_models(text):
    """Parse top-level model blocks in Gazebo protobuf text; require live IDs."""
    models = {}
    for match in re.finditer(r"(?m)^model\s*\{\s*$", text):
        start = match.end()
        level = 1
        end = start
        for char in text[start:]:
            end += 1
            if char == "{": level += 1
            elif char == "}": level -= 1
            if level == 0: break
        block = text[start:end-1]
        # Model name/id are fields at indentation two; links deeper.
        name = re.search(r'(?m)^  name: "([^"]+)"', block)
        ident = re.search(r"(?m)^  id: (\d+)", block)
        if not name or not ident or int(ident.group(1)) <= 0:
            raise RuntimeError("SCENE_MODEL_ID_MISSING")
        if name.group(1) in models:
            raise RuntimeError("SCENE_MODEL_DUPLICATE")
        models[name.group(1)] = {"id":int(ident.group(1)), "block":block}
    return models

def ci_world(source, out):
    root = ET.parse(source).getroot()
    w = root.find("./world[@name='restaurant']")
    observer = ET.SubElement(w, "model", name="a_product_ci_table_witness")
    ET.SubElement(observer,"static").text="true"
    ET.SubElement(observer,"pose").text="2.65 -2.91 0 0 0 0"
    link=ET.SubElement(observer,"link",name="witness_link")
    s=add_camera(link)
    s.set("name","a_product_ci_table_camera")
    s.find("topic").text=TABLE_TOPIC
    s.find("gz_frame_id").text="a_product_ci_table_optical"
    s.find("camera/camera_info_topic").text="/smartdish/a_product_ci/table_info"
    ET.ElementTree(root).write(out,encoding="utf-8",xml_declaration=True)

def pack_rgb(m):
    if (m.width,m.height)!=(640,480) or m.encoding not in ("rgb8","bgr8"):
        raise ValueError("IMAGE_CONTRACT")
    data=bytes(m.data)
    if m.step < 1920 or len(data) != m.step*480:
        raise ValueError("IMAGE_STRIDE")
    packed=b"".join(data[y*m.step:y*m.step+1920] for y in range(480))
    if m.encoding=="bgr8":
        b=bytearray(packed)
        b[0::3],b[2::3]=packed[2::3],packed[0::3]
        packed=bytes(b)
    return packed

def stop(proc):
    if proc.poll() is not None: return {"exit":proc.returncode,"forced":False}
    os.killpg(proc.pid,signal.SIGINT)
    try: return {"exit":proc.wait(timeout=20),"forced":False}
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGKILL)
        return {"exit":proc.wait(timeout=10),"forced":True}

def run(a):
    if os.environ.get("GITHUB_ACTIONS")!="true" or os.environ.get("CI")!="true" or os.environ.get("WSL_DISTRO_NAME") or not os.environ.get("GZ_PARTITION","").startswith("smartdish_a_product_"):
        raise RuntimeError("CI_ONLY")
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy
    from sensor_msgs.msg import Image
    from rosgraph_msgs.msg import Clock
    from PIL import Image as PillowImage
    out=a.out
    out.mkdir(parents=True,exist_ok=False)
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    scene=generate_scene(a.world,out/"world.sdf",a.scenario,os.environ["GITHUB_RUN_ID"]+"-"+a.scenario)
    robot=generate_robot(a.robot,a.bridge,out/"overlay")
    ci_world(out/"world.sdf",out/"witness_world.sdf")
    bridge=yaml.safe_load((out/"overlay/bridge.yaml").read_text())
    bridge.append(dict(ros_topic_name=TABLE_TOPIC,gz_topic_name=TABLE_TOPIC,
                       ros_type_name="sensor_msgs/msg/Image",gz_type_name="gz.msgs.Image",direction="GZ_TO_ROS"))
    (out/"witness_bridge.yaml").write_text(yaml.safe_dump(bridge,sort_keys=False))
    evidence={"source_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
              "run_id":os.environ["GITHUB_RUN_ID"],"scenario":a.scenario,
              "world_id":"restaurant","generated_world_sha256":scene["world_sha256"],
              "ci_world_sha256":sha(out/"witness_world.sdf"),"robot_sha256":robot["robot_sha256"],
              "bridge_sha256":sha(out/"witness_bridge.yaml"),"stack_id":scene["stack_id"],
              "scope":"ACTUAL_NO_GOAL_STARTUP_WITH_SAME_WORLD_CI_TABLE_WITNESS",
              "verdict":"NOT_RUN","first_error":None}
    procs=[]; files=[]; node=None
    frames={TRAY_TOPIC:{},TABLE_TOPIC:{}}; clock=[]
    def spawn(name,args):
        log=(out/(name+".log")).open("w")
        files.append(log)
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        procs.append((name,p))
        return p
    def scene_query():
        p=subprocess.run(["gz","service","-s","/world/restaurant/scene/info","--reqtype","gz.msgs.Empty","--reptype","gz.msgs.Scene","--timeout","3000","--req",""],text=True,capture_output=True,timeout=8)
        if p.returncode: return {}
        (out/"scene_info.txt").write_text(p.stdout)
        return scene_models(p.stdout)
    def image_cb(topic,m):
        try:
            frame="smartdish_tray_optical" if topic==TRAY_TOPIC else "a_product_ci_table_optical"
            if m.header.frame_id != frame: return
            stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
            if stamp<=0 or stamp in frames[topic]:return
            data=pack_rgb(m)
            if len(set(data)) < 8:return
            if len(frames[topic]) < 4:frames[topic][stamp]=data
        except ValueError: return
    try:
        gz=spawn("gazebo",["gz","sim","-r","-s","-v","4",str(out/"witness_world.sdf")])
        until=time.monotonic()+100
        while time.monotonic()<until:
            if gz.poll() is not None: raise RuntimeError("GAZEBO_EARLY_EXIT")
            models=scene_query()
            if "table_3" in models: break
            time.sleep(.5)
        else: raise RuntimeError("RESTAURANT_SCENE_NOT_READY")
        want=a.scenario=="stacked"
        if ("s6_stacked_dishes" in models)!=want:raise RuntimeError("STARTUP_ENTITY_COUNT")
        if want:
            evidence["fixture_entity_id"]=models["s6_stacked_dishes"]["id"]
        evidence["initial_fixture_count"]=int(want)
        sp=spawn("robot_spawn",["ros2","run","ros_gz_sim","create","-world","restaurant","-name","waffle_pi","-file",str(out/"overlay/robot.sdf"),"-x","-2.60","-y","-2.20","-z","0.02"])
        if sp.wait(timeout=90)!=0:raise RuntimeError("ROBOT_SPAWN_FAILED")
        bridge_proc=spawn("bridge",["ros2","run","ros_gz_bridge","parameter_bridge","--ros-args","-p","config_file:="+str((out/"witness_bridge.yaml").resolve())])
        rclpy.init()
        node=rclpy.create_node("a_product_startup_witness")
        qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
        for topic in frames:node.create_subscription(Image,topic,lambda m,t=topic:image_cb(t,m),qos)
        node.create_subscription(Clock,"/clock",lambda m:clock.append(m.clock.sec*10**9+m.clock.nanosec),qos)
        until=time.monotonic()+150
        while time.monotonic()<until:
            if gz.poll() is not None or bridge_proc.poll() is not None:raise RuntimeError("RUNTIME_EARLY_EXIT")
            rclpy.spin_once(node,timeout_sec=.2)
            if all(len(x)>=3 for x in frames.values()) and len(set(clock))>=3:break
        else:raise RuntimeError("ACTUAL_RGB_OR_CLOCK_TIMEOUT")
        if node.count_publishers("/clock")!=1 or node.count_publishers(TRAY_TOPIC)!=1:
            raise RuntimeError("DUPLICATE_CLOCK_OR_TRAY_PUBLISHER")
        models=scene_query()
        if "waffle_pi" not in models or "smartdish_product_tray" not in models["waffle_pi"]["block"]:
            raise RuntimeError("ROBOT_TRAY_ENTITY_NOT_OBSERVED")
        if ("s6_stacked_dishes" in models)!=want:raise RuntimeError("FIXTURE_CHANGED_DURING_STARTUP")
        evidence["robot_entity_id"]=models["waffle_pi"]["id"]
        evidence["clock_publishers"]=node.count_publishers("/clock")
        evidence["tray_publishers"]=node.count_publishers(TRAY_TOPIC)
        evidence["frames"]={}
        for topic,name in ((TRAY_TOPIC,"tray"),(TABLE_TOPIC,"table")):
            stamps=sorted(frames[topic])
            data=frames[topic][stamps[-1]]
            png=out/(name+".png")
            PillowImage.frombytes("RGB",(640,480),data).save(png)
            evidence["frames"][name]={"stamp_ns":stamps[-1],"stamps":stamps,
                "rgb_sha256":hashlib.sha256(data).hexdigest(),"png_sha256":sha(png),
                "width":640,"height":480}
        evidence["verdict"]="ACTUAL_STARTUP_AND_ROBOT_RGB_NO_GOAL_PASS"
    except BaseException as exc:
        evidence["first_error"]=repr(exc)
        evidence["verdict"]="FAIL"
        raise
    finally:
        if node:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
        evidence["cleanup"]={name:stop(p) for name,p in reversed(procs)}
        for f in files:f.close()
        if any(x["forced"] for x in evidence["cleanup"].values()):
            evidence["verdict"]="FAIL"
            evidence["first_error"]=evidence["first_error"] or "FORCED_CLEANUP"
        (out/"evidence.json").write_text(json.dumps(evidence,sort_keys=True,indent=2)+"\n")
    if evidence["verdict"]!="ACTUAL_STARTUP_AND_ROBOT_RGB_NO_GOAL_PASS":
        raise RuntimeError(evidence["first_error"])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("world","robot","bridge","out"):p.add_argument("--"+key,type=Path,required=True)
    p.add_argument("--scenario",choices=["stacked","empty"],required=True)
    run(p.parse_args())

if __name__=="__main__":main()
