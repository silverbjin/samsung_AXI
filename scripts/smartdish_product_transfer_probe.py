#!/usr/bin/env python3
"""Actual isolated no-goal LOAD/capture/removal witness for A-PROD-03.

This is NOT a production transfer controller or ACK publisher. The robot stays
stationary; virtual staff acts through real Gazebo services. E/D must approve
the Nav2 UUID/terminal/stop handshake before product requests are connected.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
from xml.etree import ElementTree as ET
from smartdish_product_startup_probe import TRAY_TOPIC

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_robot.product_contract import FrameCache,StopMonitor,ContractError,verify_transfer_observation
from smartdish_robot.product_gazebo_backend import (
    DISH_NAMES,FIXTURE,PLATE_HEIGHT,TRAY_TOP,GazeboEntityServices,
    add_pose_publisher,build_dish_sdf,relative_xyz,
)

ROBOT="waffle_pi"
POSE_PREFIX="/smartdish/product/gz_pose/"

class TransferProbe:
    def __init__(self):
        self.poses={}
        self.stop=StopMonitor()
        self.cache=FrameCache()
        self.callback_error=None
        self.last_odom_stamp=None

    def prepare(self,out,robot_path,bridge):
        root=ET.parse(robot_path).getroot()
        model=root.find("./model[@name='turtlebot3_waffle_pi']")
        if model is None:raise RuntimeError("TRANSFER_ROBOT_MODEL_MISSING")
        add_pose_publisher(model,POSE_PREFIX+ROBOT)
        target=out/"transfer_robot.sdf"
        ET.ElementTree(root).write(target,encoding="utf-8",xml_declaration=True)
        for name in (ROBOT,*DISH_NAMES):
            topic=POSE_PREFIX+name
            bridge.append(dict(ros_topic_name=topic,gz_topic_name=topic,
                               ros_type_name="tf2_msgs/msg/TFMessage",
                               gz_type_name="gz.msgs.Pose_V",direction="GZ_TO_ROS"))
        return target,bridge

    def attach(self,node,clock):
        from rclpy.qos import QoSProfile,ReliabilityPolicy,qos_profile_sensor_data
        from tf2_msgs.msg import TFMessage
        from sensor_msgs.msg import Image
        from nav_msgs.msg import Odometry
        self.clock=clock
        self.node=node
        self.subs=[]
        def odom(m):
            try:
                stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
                if stamp==self.last_odom_stamp:return
                self.last_odom_stamp=stamp
                v=m.twist.twist.linear;w=m.twist.twist.angular
                self.stop.observe(stamp,time.monotonic(),math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z),
                                  math.sqrt(w.x*w.x+w.y*w.y+w.z*w.z))
            except (ContractError,ValueError) as exc:self.callback_error=str(exc)
        def image(m):
            try:
                stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
                if stamp<=0:return
                self.cache.observe(stamp,m.header.frame_id,m.width,m.height,m.encoding,m.step,m.data,time.monotonic())
            except ContractError as exc:self.callback_error=str(exc)
        def pose(m,name):
            if not clock or clock[-1]<=0:return
            for t in m.transforms:
                # Never use TF array index as identity.
                if not re.search(r"(^|[/:\s])"+re.escape(name)+r"($|[/:\s])",t.child_frame_id):continue
                p=t.transform.translation;q=t.transform.rotation
                xyz=(p.x,p.y,p.z);quat=(q.x,q.y,q.z,q.w)
                if not all(math.isfinite(v) for v in (*xyz,*quat)):
                    self.callback_error="NONFINITE_POSE";return
                stamp=t.header.stamp.sec*10**9+t.header.stamp.nanosec
                # Match A12: sim clock at callback if PosePublisher omits stamp.
                stamp=stamp if stamp>0 else clock[-1]
                last=self.poses.get(name)
                if last and stamp<last["sim_ns"]:
                    self.callback_error="POSE_EPOCH_REVERSED";return
                if last and stamp==last["sim_ns"]:continue
                self.poses[name]={"xyz":xyz,"q":quat,"sim_ns":stamp,"at":time.monotonic(),
                                  "frame_id":t.child_frame_id}
        self.subs.append(node.create_subscription(Odometry,"/odom",odom,qos_profile_sensor_data))
        self.subs.append(node.create_subscription(Image,TRAY_TOPIC,image,QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)))
        for name in (ROBOT,*DISH_NAMES):
            self.subs.append(node.create_subscription(TFMessage,POSE_PREFIX+name,lambda m,n=name:pose(m,n),qos_profile_sensor_data))

    def spin(self):
        import rclpy
        rclpy.spin_once(self.node,timeout_sec=.1)
        if self.callback_error:raise RuntimeError(self.callback_error)

    def until(self,check,seconds,reason):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.spin()
            value=check()
            if value:return value
        raise RuntimeError(reason)

    def fresh_pose(self,name):
        p=self.poses.get(name)
        return p if p and 0<=time.monotonic()-p["at"]<=.5 else None

    def wait_stop(self):
        self.until(lambda:self.stop.verified(time.monotonic()) and self.fresh_pose(ROBOT),10,"CI_ACTUAL_ROBOT_STOP_NOT_PROVEN")
        return self.fresh_pose(ROBOT)

    def wait_scene(self,services,predicate,seconds=8):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            self.spin()
            models=services.scene()
            if predicate(models):return models
        raise RuntimeError("LIVE_ENTITY_STATE_NOT_PROVEN")

    def observe_loaded(self,ids,stack_id):
        stable=[];previous=None
        deadline=time.monotonic()+25
        while time.monotonic()<deadline:
            self.spin()
            robot=self.fresh_pose(ROBOT)
            dishes=[self.fresh_pose(n) for n in DISH_NAMES]
            if not robot or not all(dishes):continue
            stamp=min([robot["sim_ns"]]+[p["sim_ns"] for p in dishes])
            if max([robot["sim_ns"]]+[p["sim_ns"] for p in dishes])-stamp>200_000_000:continue
            if previous and stamp-previous[0]<150_000_000:continue
            rel=[relative_xyz(robot["xyz"],robot["q"],p["xyz"]) for p in dishes]
            if previous:
                dt=(stamp-previous[0])/1e9
                speeds=[math.dist(a,b)/dt for a,b in zip(rel,previous[1])]
                xy=[math.hypot(p[0],p[1]) for p in rel]
                z=[abs(p[2]-(TRAY_TOP+PLATE_HEIGHT*(i+.5))) for i,p in enumerate(rel)]
                row={"sim_ns":stamp,"entity_ids":ids,"relative_xy_m":xy,
                     "relative_z_error_m":z,"relative_speed_mps":speeds,
                     "robot_world":robot,"dish_world":dishes,"relative_xyz":rel}
                if max(xy)<=.015 and max(z)<=.02 and max(speeds)<=.02 and self.stop.verified(time.monotonic()):
                    stable.append(row)
                    if len(stable)>=3 and stable[-1]["sim_ns"]-stable[0]["sim_ns"]>=10**9:
                        return {"stack_id":stack_id,"location":"ON_ROBOT","entity_ids":ids,
                                "table_count":0,"tray_count":3,"event_sim_ns":stamp,"samples":stable}
                else:stable=[]
            previous=(stamp,rel)
        raise RuntimeError("ACTUAL_LOADED_RELATIVE_POSE_DWELL_NOT_PROVEN")

    def execute(self,out,scene):
        from PIL import Image
        ev={"scope":"CI_NO_GOAL_PHYSICAL_TRANSFER_WITNESS_NOT_PRODUCT_ACK",
            "stack_id":scene["stack_id"],"verdict":"NOT_RUN","first_error":None}
        d=out/"transfer";d.mkdir()
        services=GazeboEntityServices(d,timeout_s=2.)
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        try:
            models=services.scene()
            if scene["scenario"]=="empty":
                if FIXTURE in models or any(n in models for n in DISH_NAMES):
                    raise RuntimeError("EMPTY_TABLE_ENTITY_CONFLICT")
                ev.update(verdict="ACTUAL_EMPTY_TABLE_NO_MUTATION",reason="EMPTY_TABLE")
                return ev
            if FIXTURE not in models or any(n in models for n in DISH_NAMES):
                raise RuntimeError("INITIAL_ENTITY_CONFLICT")
            robot=self.wait_stop()
            fixture=ET.parse(out/"world.sdf").find(f".//world/model[@name='{FIXTURE}']")
            if fixture is None or sha(out/"world.sdf")!=scene["world_sha256"]:
                raise RuntimeError("SOURCE_FIXTURE_HASH_MISMATCH")
            q=robot["q"]
            if abs(q[0])+abs(q[1])>.03:raise RuntimeError("ROBOT_NOT_LEVEL")
            yaw=math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2))
            ev["initial_fixture_entity_id"]=models[FIXTURE]
            # Real UserCommands; no fake UUID, no production ACK, no retry.
            started=time.monotonic()
            services.remove(models[FIXTURE])
            self.wait_scene(services,lambda m:FIXTURE not in m)
            for i,name in enumerate(DISH_NAMES):
                robot=self.wait_stop()
                xyz=(robot["xyz"][0],robot["xyz"][1],
                     robot["xyz"][2]+TRAY_TOP+PLATE_HEIGHT*(i+.5)+.002)
                path=d/(name+".sdf")
                path.write_text(build_dish_sdf(fixture,i,xyz,yaw))
                services.create(path,name)
                self.wait_scene(services,lambda m,n=name:n in m and FIXTURE not in m)
            models=services.scene()
            ids=[models[n] for n in DISH_NAMES]
            obs=self.observe_loaded(ids,scene["stack_id"])
            verify_transfer_observation({"operation":"LOAD","stack_id":scene["stack_id"]},obs,3)
            ev["load"]=obs
            ev["load_wall_s"]=time.monotonic()-started
            frame=self.until(lambda:self.cache.select(obs["event_sim_ns"],time.monotonic()),8,"POST_LOAD_RGB_TIMEOUT")
            png=d/"captured.png";raw=d/"captured.rgb"
            Image.frombytes("RGB",(640,480),frame.rgb).save(png);raw.write_bytes(frame.rgb)
            ev["capture"]={"image_stamp_ns":frame.stamp_ns,"frame_id":frame.frame_id,
                           "rgb_sha256":frame.rgb_sha256,"png_sha256":sha(png),
                           "width":640,"height":480,"encoding":frame.encoding,
                           "min_sim_stamp_ns":obs["event_sim_ns"]}
            if sha(raw)!=frame.rgb_sha256:raise RuntimeError("CAPTURE_HASH_DRIFT")
            # The removal receipt is the permitted simulated handover method;
            # this isolated test has no actual DISH_RETURN arrival.
            self.wait_stop()
            started=time.monotonic()
            for name,ident in zip(DISH_NAMES,ids):
                models=services.scene()
                if models.get(name)!=ident:raise RuntimeError("UNLOAD_ENTITY_ID_DRIFT")
                self.wait_stop()
                services.remove(ident)
                self.wait_scene(services,lambda m,n=name:n not in m)
            models=services.scene()
            if FIXTURE in models or any(n in models for n in DISH_NAMES):raise RuntimeError("UNLOAD_TRAY_NOT_EMPTY")
            ev["unload"]={"method":"ACTUAL_REMOVE_RECEIPT","removed_entity_ids":ids,
                          "tray_count":0,"table_count":0,"event_sim_ns":self.clock[-1]}
            ev["unload_wall_s"]=time.monotonic()-started
            ev["verdict"]="ACTUAL_STATIONARY_LOAD_CAPTURE_REMOVE_OBSERVED"
            return ev
        except BaseException as exc:
            ev["first_error"]=repr(exc);ev["verdict"]="FAIL"
            raise
        finally:
            log=d/"gazebo_service_calls.jsonl"
            if log.exists():ev["service_calls_sha256"]=sha(log)
            (d/"transfer_evidence.json").write_text(json.dumps(ev,sort_keys=True,indent=2)+"\n")
