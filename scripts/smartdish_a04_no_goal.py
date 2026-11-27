#!/usr/bin/env python3
"""A04 actual restaurant Nav2 ComputePathToPose diagnostic, NO NavigateToPose.
No velocity publisher. Generated candidate maps are diagnostic only.
"""
import argparse, json, math, os, subprocess, time, sys
from pathlib import Path
from collections import deque
import numpy as np
import yaml
from scipy.ndimage import distance_transform_edt
from scipy.spatial.transform import Rotation
from smartdish_a04_clearance import (
    ROOT, HALF, PADDING, REGISTRATION_MARGIN, NOMINAL, TARGETS,
    prepare, read_map, sha, save, require,
)
from prepare_nav2_params import build
from smartdish_a04_launch_overlay import prepare_launch_overlay
from smartdish_product_startup_probe import stop, quiesce_world
from smartdish_robot.product_physics import PhysicalOperations, ROBOT
from smartdish_robot.product_gazebo_backend import GazeboEntityServices, FIXTURE

def overlay(source,dst):
    base=dst.with_suffix(".s7.yaml")
    build(source,base,auto_initial_pose=True,s6_bt_ack_ms=200)
    p=yaml.safe_load(base.read_text())
    footprint=json.dumps([[-HALF,-HALF],[HALF,-HALF],[HALF,HALF],[-HALF,HALF]])
    for name in ("local_costmap","global_costmap"):
        n=p[name][name]["ros__parameters"]
        n["footprint"]=footprint;n["footprint_padding"]=PADDING;n.pop("robot_radius",None)
        if name=="global_costmap":n["track_unknown_space"]=True
    cm=p["collision_monitor"]["ros__parameters"]
    require(cm["cmd_vel_in_topic"]=="cmd_vel_smoothed" and cm["cmd_vel_out_topic"]=="cmd_vel","CM_CHAIN")
    require("FootprintApproach" in cm["polygons"] and "S4ForwardStop" in cm["polygons"],"CM_POLYGON")
    cm["S4ForwardStop"]["points"]="[[0.10,0.30],[0.58,0.30],[0.58,-0.30],[0.10,-0.30]]"
    planners=p["planner_server"]["ros__parameters"]
    for name in planners["planner_plugins"]:
        require("NavfnPlanner" in planners[name]["plugin"],"UNREVIEWED_PLANNER")
        planners[name]["allow_unknown"]=False
        planners[name]["tolerance"]=.05
    dst.write_text(yaml.safe_dump(p,sort_keys=False))
    return p

def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def stamp(m):return m.sec*10**9+m.nanosec

def transform_map_to_world(gt,map_pose):
    r=math.atan2(math.sin(gt[2]-map_pose[2]),math.cos(gt[2]-map_pose[2]))
    c,s=math.cos(r),math.sin(r)
    return [gt[0]-c*map_pose[0]+s*map_pose[1],gt[1]-s*map_pose[0]-c*map_pose[1],r]
def world_xy(tf,x,y):
    c,s=math.cos(tf[2]),math.sin(tf[2])
    return np.array([tf[0]+c*x-s*y,tf[1]+s*x+c*y])
def points_dense(points,step=.025):
    require(len(points)>=2,"PATH_EMPTY")
    out=[]
    for a,b in zip(points,points[1:]):
        d=math.dist(a[:2],b[:2]);n=max(1,math.ceil(d/step))
        for i in range(n):
            out.append((a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n))
    return np.array(out+[tuple(points[-1][:2])])
def map_disk_clearance(cfg,a,points):
    res=cfg["resolution"];ox,oy=cfg["origin"][:2]
    dist=distance_transform_edt(np.pad(a==0,1,constant_values=False))[1:-1,1:-1]*res
    i=np.floor((points[:,1]-oy)/res).astype(int);j=np.floor((points[:,0]-ox)/res).astype(int)
    if not ((i>=0)&(i<a.shape[0])&(j>=0)&(j<a.shape[1])).all():return -1.
    # center-to-cell quantization + cell half-diagonal + path interpolation
    return float(np.min(dist[i,j])-math.sqrt(2)*(HALF+PADDING)-math.sqrt(2)*res-.0125)
def physical_disk_clearance(g,points,tf):
    wp=np.array([world_xy(tf,*p) for p in points]);x,y=wp[:,0],wp[:,1]
    distances=[]
    f=g["floor"]
    distances.append(("floor_boundary",np.min(np.stack([x-f["lo"][0],f["hi"][0]-x,y-f["lo"][1],f["hi"][1]-y]))))
    for c in g["obstacles"]:
        lo,hi=c["lo"],c["hi"]
        dx=np.maximum(np.maximum(lo[0]-x,x-hi[0]),0)
        dy=np.maximum(np.maximum(lo[1]-y,y-hi[1]),0)
        distances.append((c["model"]+"/"+c["collision"],np.min(np.hypot(dx,dy))))
    name,d=min(distances,key=lambda z:z[1])
    return {"obstacle":name,"all_yaw_clearance_m":float(d-math.sqrt(2)*(HALF+PADDING)-.0125),
            "registration_margin_remaining_m":float(d-math.sqrt(2)*(HALF+PADDING)-.0125-REGISTRATION_MARGIN)}
def endpoints(node,topic):
    return [{"name":x.node_name,"namespace":x.node_namespace} for x in node.get_publishers_info_by_topic(topic)]
def run(a):
    require(os.environ.get("CI")=="true" and os.environ.get("GITHUB_ACTIONS")=="true" and
            os.environ.get("GZ_PARTITION","").startswith("smartdish_a04_") and not os.environ.get("WSL_DISTRO_NAME"),"CI_ONLY")
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    evidence={"scope":"ACTUAL_NAV2_COMPUTE_PATH_ONLY_NO_MOTION","mode":a.mode,
              "source_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
              "run_id":os.environ["GITHUB_RUN_ID"],"navigate_to_pose_goals_sent":0,
              "velocity_commands_published":0,"first_error":None,"motion_authorized":False,"paths":[]}
    proc=node=None;log=None;initialized=False;clock=deque(maxlen=4096)
    import rclpy
    from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy,qos_profile_sensor_data
    from rclpy.parameter import Parameter
    from rclpy.parameter_client import AsyncParameterClient
    from rclpy.action import ActionClient
    from rclpy.time import Time
    from tf2_ros import Buffer,TransformListener
    from geometry_msgs.msg import PolygonStamped,PoseStamped,PoseWithCovarianceStamped,Twist
    from nav_msgs.msg import Odometry,OccupancyGrid
    from nav2_msgs.action import ComputePathToPose
    from nav2_msgs.srv import GetCostmap
    from sensor_msgs.msg import LaserScan
    from rosgraph_msgs.msg import Clock
    from lifecycle_msgs.srv import GetState
    from lifecycle_msgs.msg import State
    from PIL import Image
    try:
        scene,g,audit=prepare(out/"static",a.robot_source,a.bridge_source,a.world_source,a.map,a.poses,
                              "a04-"+evidence["run_id"]+"-"+a.mode)
        phys=PhysicalOperations()
        static=out/"static"
        robot,bridge=phys.prepare(static,static/"overlay/robot.sdf",yaml.safe_load((static/"overlay/bridge.yaml").read_text()))
        sources=None
        if a.motion:
            from smartdish_a04_motion import instrument,moving_params
            require(a.mode=="candidate","MOTION_REQUIRES_CANDIDATE")
            sources=instrument(static/"world.sdf",robot,bridge,scene)
        bridgefile=static/"live_bridge.yaml";bridgefile.write_text(yaml.safe_dump(bridge,sort_keys=False))
        params=static/"live_nav2.yaml";config=overlay(a.params,params)
        if a.motion:
            config=moving_params(config);params.write_text(yaml.safe_dump(config,sort_keys=False))
        map_path=a.map.resolve() if a.mode=="original" else static/"candidate.yaml"
        cfg,grid=read_map(map_path)
        evidence.update(world_sha256=sha(static/"world.sdf"),robot_sha256=sha(robot),bridge_sha256=sha(bridgefile),
                        map_sha256=sha(map_path.parent/cfg["image"]),params_sha256=sha(params),
                        map_static_screen=audit["original" if a.mode=="original" else "candidate"])
        log=(out/"launch.log").open("w")
        launch_file,launch_manifest=prepare_launch_overlay(static/"launch_overlay")
        evidence["launch_overlay"]=launch_manifest
        cmd=["ros2","launch",str(launch_file),"gui:=false",
             "robot_sdf:="+str(robot),"world_file:="+str(static/"world.sdf"),"bridge_config:="+str(bridgefile),
             "map:="+str(map_path),"params_file:="+str(params),"s6_stagger_nav_start:=true"]
        evidence["launch_argv"]=cmd
        proc=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        rclpy.init(domain_id=int(os.environ["ROS_DOMAIN_ID"]));initialized=True
        node=rclpy.create_node("smartdish_a04_no_goal",parameter_overrides=[Parameter("use_sim_time",value=True)])
        phys.attach(node,clock)
        qos=QoSProfile(depth=10,reliability=ReliabilityPolicy.RELIABLE)
        latched=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        state={"scan":0,"odom":0,"amcl":None,"footprints":{},"map":None,"odom_first":None,"odom_max":0.,"cmd_nonzero":0,"times":{}}
        def clk(m):
            ns=stamp(m.clock)
            if clock and ns<clock[-1]:raise RuntimeError("CLOCK_REVERSED")
            if not clock or ns>clock[-1]:clock.append(ns)
        def odom(m):
            xy=(m.pose.pose.position.x,m.pose.pose.position.y)
            if state["odom_first"] is None:state["odom_first"]=xy
            state["odom_max"]=max(state["odom_max"],math.dist(xy,state["odom_first"]))
            state["odom"]+=1;state["times"]["odom"]=time.monotonic();state["odom_msg"]=m
        def scan(m):
            if len(m.ranges)>10 and any(math.isfinite(x) for x in m.ranges):
                state["scan"]+=1;state["times"]["scan"]=time.monotonic();state["scan_msg"]=m
        def amcl(m):state.update(amcl=m);state["times"]["amcl"]=time.monotonic()
        def footprint(m,n):state["footprints"][n]=m;state["times"][n]=time.monotonic()
        def cmdvel(m):
            if max(abs(m.linear.x),abs(m.linear.y),abs(m.angular.z))>1e-5:state["cmd_nonzero"]+=1
        subs=[node.create_subscription(Clock,"/clock",clk,qos),
              node.create_subscription(Odometry,"/odom",odom,qos_profile_sensor_data),
              node.create_subscription(LaserScan,"/scan",scan,qos_profile_sensor_data),
              node.create_subscription(PoseWithCovarianceStamped,"/amcl_pose",amcl,qos),
              node.create_subscription(OccupancyGrid,"/map",lambda m:state.update(map=m),latched),
              node.create_subscription(Twist,"/cmd_vel",cmdvel,qos)]
        for n in ("global_costmap","local_costmap"):
            subs.append(node.create_subscription(PolygonStamped,"/"+n+"/published_footprint",lambda m,n=n:footprint(m,n),qos_profile_sensor_data))
        buffer=Buffer();listener=TransformListener(buffer,node,spin_thread=False)
        action=ActionClient(node,ComputePathToPose,"/compute_path_to_pose")
        def spin():
            require(proc.poll() is None,"LAUNCH_EARLY_EXIT")
            rclpy.spin_once(node,timeout_sec=.10)
            require(not phys.callback_error,"PHYS_CALLBACK:"+str(phys.callback_error))
            if not evidence.get("motion_authorized"):require(state["odom_max"]<=.03 and state["cmd_nonzero"]==0,"NO_GOAL_MOTION_DETECTED")
        def wait(check,seconds,label):
            until=time.monotonic()+seconds
            while time.monotonic()<until:
                spin()
                if check():return
            raise RuntimeError("TIMEOUT_"+label)
        def future(f,seconds,label):
            wait(f.done,seconds,label);return f.result()
        def tf_ready():
            return all(buffer.can_transform("map",n,Time()) for n in ("odom","base_footprint","base_link"))
        def ready():
            return (len(clock)>=3 and state["scan"]>=3 and state["odom"]>=3 and state["amcl"] is not None and
                    state["map"] is not None and len(state["footprints"])==2 and tf_ready() and
                    phys.fresh_pose(ROBOT) and phys.stop.verified(time.monotonic()) and
                    phys.cache.select(0,time.monotonic()) is not None and action.server_is_ready())
        wait(ready,200,"CLOCK_SCAN_ODOM_AMCL_TF_FOOTPRINT_RGB")
        # A planner action endpoint and published footprint may be available
        # before lifecycle_manager activates CM (observed RED 45955271845).
        names=("collision_monitor","planner_server","controller_server","velocity_smoother","amcl",
               "local_costmap/local_costmap","global_costmap/global_costmap")
        clients={n:node.create_client(GetState,"/"+n+"/get_state") for n in names}
        evidence["lifecycle_history"]=[]
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            all_states={}
            for name,client in clients.items():
                if not client.service_is_ready():
                    all_states[name]="SERVICE_NOT_READY";continue
                result=future(client.call_async(GetState.Request()),5,"LIFECYCLE_"+name)
                all_states[name]=result.current_state.label
            evidence["lifecycle_history"].append({"steady_s":time.monotonic(),"states":all_states})
            if all(all_states.get(n)=="active" for n in names):break
            spin()
        else:raise RuntimeError("TIMEOUT_ALL_LIFECYCLES_ACTIVE")
        evidence["lifecycle"]=all_states
        for name in ("global_costmap","local_costmap"):
            client=AsyncParameterClient(node,"/"+name+"/"+name)
            wait(client.services_are_ready,10,"PARAM_"+name)
            ps=future(client.get_parameters(["footprint","footprint_padding"]),8,"PARAM_"+name).values
            fp=json.loads(ps[0].string_value);pad=ps[1].double_value
            require(len(fp)==4 and all(abs(abs(v)-HALF)<1e-6 for pt in fp for v in pt) and abs(pad-PADDING)<1e-6,"LIVE_FOOTPRINT_PARAM")
            m=state["footprints"][name];pts=[(v.x,v.y) for v in m.polygon.points]
            require(len(pts)==4,"LIVE_FOOTPRINT_POINT_COUNT")
            sides=[math.dist(x,y) for x,y in zip(pts,pts[1:]+pts[:1])]
            require(all(abs(v-2*(HALF+PADDING))<.02 for v in sides),"LIVE_PADDED_FOOTPRINT_SIZE")
            evidence.setdefault("footprints",{})[name]={"parameter":fp,"padding":pad,"published_frame":m.header.frame_id,
                "published_stamp_ns":stamp(m.header.stamp),"published_points":pts,"edge_m":sides}
        # Preserve the failing graph before asserting; discovery can lag lifecycle.
        topics=("/clock","/cmd_vel","/cmd_vel_smoothed","/cmd_vel_nav","/smartdish/tray/image_raw")
        evidence["graph_history"]=[]
        deadline=time.monotonic()+20
        stable_since=None
        while time.monotonic()<deadline:
            graph={k:endpoints(node,k) for k in topics}
            evidence["publishers"]=graph
            evidence["subscribers"]={k:[{"name":x.node_name,"namespace":x.node_namespace,"type":x.topic_type}
                for x in node.get_subscriptions_info_by_topic(k)] for k in topics}
            evidence["graph_history"].append({"steady_s":time.monotonic(),"publishers":graph})
            valid=(all(len(graph[k])==1 for k in ("/clock","/cmd_vel","/cmd_vel_smoothed","/smartdish/tray/image_raw"))
                and graph["/cmd_vel"][0]["name"]=="collision_monitor"
                and graph["/cmd_vel_smoothed"][0]["name"]=="velocity_smoother")
            stable_since=(stable_since or time.monotonic()) if valid else None
            if stable_since is not None and time.monotonic()-stable_since>=3.:break
            spin()
            time.sleep(.1)
        else:raise RuntimeError("GRAPH_PUBLISHER_OR_CHAIN:"+json.dumps(graph,sort_keys=True))
        service=GazeboEntityServices(out/"actual_scene",timeout_s=2.)
        models=service.scene()
        require(FIXTURE in models and ROBOT in models and not any(n.startswith("smartdish_product_dish_") for n in models),"INITIAL_ENTITIES")
        evidence["initial_entities"]={"fixture_id":models[FIXTURE],"robot_id":models[ROBOT],"tray_dynamic_count":0}
        wait(ready,10,"FRESH_PREPATH")
        frame=phys.cache.select(0,time.monotonic())
        (out/"tray.rgb").write_bytes(frame.rgb)
        Image.frombytes("RGB",(640,480),frame.rgb).save(out/"tray.png")
        evidence["rgb"]={"stamp_ns":frame.stamp_ns,"frame_id":frame.frame_id,"rgb_sha256":sha(out/"tray.rgb"),"png_sha256":sha(out/"tray.png")}
        m=state["map"]
        require(m.header.frame_id=="map" and (m.info.height,m.info.width)==grid.shape,"LIVE_MAP_SHAPE")
        actual=np.array(m.data).reshape(grid.shape);require(np.array_equal(actual,grid),"LIVE_MAP_PIXEL_DRIFT")
        tf={}
        for name in ("odom","base_footprint","base_link"):
            t=buffer.lookup_transform("map",name,Time())
            p=t.transform.translation;q=t.transform.rotation
            tf[name]={"xy_yaw":[p.x,p.y,yaw(q)],"stamp_ns":stamp(t.header.stamp),"z":p.z}
        evidence["tf_map"]=tf
        gt=phys.fresh_pose(ROBOT);require(gt is not None,"LIVE_GT_STALE")
        q=gt["q"];gtyaw=math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2))
        live=transform_map_to_world([*gt["xyz"][:2],gtyaw],tf["base_footprint"]["xy_yaw"])
        evidence["registration"]={"nominal":NOMINAL,"actual_map_to_world":live,"actual_robot_world":gt,
            "translation_difference_m":math.dist(live[:2],NOMINAL[:2]),"yaw_difference_rad":abs(live[2]),
            "single_station_only":True}
        # ComputePathToPose explicit start for each leg; no robot teleportation.
        # Subsequent starts are hypothetical poses, not observed arrivals.
        target=yaml.safe_load(a.poses.read_text())["poses"]
        def msg(p):
            v=PoseStamped();v.header.frame_id="map";v.header.stamp=node.get_clock().now().to_msg()
            v.pose.position.x=p["x"];v.pose.position.y=p["y"]
            v.pose.orientation.z=math.sin(p["yaw"]/2);v.pose.orientation.w=math.cos(p["yaw"]/2)
            return v
        for u,v in zip(TARGETS,(*TARGETS[1:],TARGETS[0])):
            row={"from":u,"to":v,"start_kind":"EXPLICIT_CONFIGURED_POSE","status":"NOT_RUN"}
            evidence["paths"].append(row)
            req=ComputePathToPose.Goal();req.start=msg(target[u]);req.goal=msg(target[v]);req.use_start=True
            req.planner_id=config["planner_server"]["ros__parameters"]["planner_plugins"][0]
            handle=future(action.send_goal_async(req),10,"PLAN_ACCEPT_"+u)
            require(handle.accepted,"PLAN_REJECTED_"+u)
            row["planning_uuid"]=bytes(handle.goal_id.uuid).hex()
            result=future(handle.get_result_async(),25,"PLAN_RESULT_"+u)
            row["status"]=int(result.status);row["error_code"]=int(result.result.error_code)
            if result.status!=4:continue
            path=result.result.path
            require(path.header.frame_id=="map","PLAN_FRAME")
            pts=[[p.pose.position.x,p.pose.position.y,yaw(p.pose.orientation)] for p in path.poses]
            row["path_file"]="path_"+u+"_"+v+".json";save(out/row["path_file"],pts)
            if len(pts)<2:continue
            dense=points_dense(pts)
            row["path_length_m"]=float(np.sum(np.linalg.norm(np.diff(np.array(pts)[:,:2],axis=0),axis=1)))
            row["start_error_m"]=math.dist(pts[0][:2],[target[u]["x"],target[u]["y"]])
            row["end_error_m"]=math.dist(pts[-1][:2],[target[v]["x"],target[v]["y"]])
            row["map_all_yaw_clearance_m"]=map_disk_clearance(cfg,grid,dense)
            row["physical_swept_bound"]=physical_disk_clearance(g,dense,live)
            row["max_nominal_registration_difference_m"]=float(max(math.dist(world_xy(live,*p),world_xy(NOMINAL,*p)) for p in dense))
            gc=node.create_client(GetCostmap,"/global_costmap/get_costmap")
            wait(gc.service_is_ready,8,"LIVE_GLOBAL_COSTMAP")
            raw=future(gc.call_async(GetCostmap.Request()),10,"LIVE_GLOBAL_COSTMAP").map
            meta=raw.metadata
            cgrid=np.array(raw.data).reshape((meta.size_y,meta.size_x))
            cc={"resolution":meta.resolution,"origin":[meta.origin.position.x,meta.origin.position.y,0]}
            # Lethal/unknown cells forbidden; inflation values are not physical obstacles.
            row["live_costmap_all_yaw_clearance_m"]=map_disk_clearance(cc,np.where(cgrid>=254,100,0),dense)
            np.save(out/("global_costmap_"+u+".npy"),cgrid)
            row["live_costmap_geometry"]=cc
        evidence["stationary"]={"odom_count":state["odom"],"scan_count":state["scan"],"max_displacement_m":state["odom_max"],
            "cmd_nonzero_count":state["cmd_nonzero"],"stop_verified":phys.stop.verified(time.monotonic())}
        require(evidence["stationary"]["stop_verified"],"FINAL_STOP_NOT_PROVEN")
        evidence["verdict"]="ACTUAL_NO_GOAL_DIAGNOSTIC_COMPLETE"
        evidence["clearance_gate"]="HOLD" # product approval remains E-owned
        if a.motion:
            from smartdish_a04_motion import run_missions
            run_missions(node,out,phys,g,sources,buffer,state,clock,evidence,scene,static,target,spin,wait)
            evidence["scope"]="ACTUAL_CI_MOTION_ONLY_NOT_PRODUCT_INTEGRATION"
            evidence["verdict"]="ACTUAL_A_MOTION_DIAGNOSTIC_COMPLETE"
    except BaseException as exc:
        evidence["first_error"]=repr(exc);evidence["verdict"]="FAIL";raise
    finally:
        if "state" in locals():
            evidence["observed_at_exit"]={"scan_count":state["scan"],"odom_count":state["odom"],
                "amcl_received":state["amcl"] is not None,"map_received":state["map"] is not None,
                "footprint_topics":list(state["footprints"]),"clock_samples":len(clock),
                "odom_max_displacement_m":state["odom_max"],"nonzero_cmd_count":state["cmd_nonzero"],
                "physics_callback_error":phys.callback_error}
        if proc:
            # Keep subscriptions alive until Gazebo is quiescent and launch exits.
            try:evidence["quiescence"]=quiesce_world(proc,node,rclpy,clock)
            except Exception as exc:evidence["quiescence"]={"error":repr(exc)}
            evidence["cleanup"]=stop(proc)
            if evidence["cleanup"]["forced"] or evidence["cleanup"]["exit"]!=0:
                evidence["first_error"]=evidence["first_error"] or "LAUNCH_CLEANUP_FAILED";evidence["verdict"]="FAIL"
        if node:node.destroy_node()
        if initialized and rclpy.ok():rclpy.shutdown()
        if log:log.close()
        save(out/"evidence.json",evidence)
    require(evidence["verdict"]==("ACTUAL_A_MOTION_DIAGNOSTIC_COMPLETE" if a.motion else "ACTUAL_NO_GOAL_DIAGNOSTIC_COMPLETE"),evidence["first_error"])
def main():
    p=argparse.ArgumentParser()
    for k in ("out","robot-source","bridge-source","world-source","map","poses","params"):
        p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--mode",choices=("original","candidate"),required=True)
    p.add_argument("--motion",action="store_true",help="explicit isolated CI only, real same-session preflight required")
    run(p.parse_args())
if __name__=="__main__":main()
