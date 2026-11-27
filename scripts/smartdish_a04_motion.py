"""A04 CI-only moving evidence. Uses real NavigationBoundary and transfer journal.
No alternate cmd_vel publisher, no fabricated UUID or fixed dishes.
"""
import json,math,time
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
import yaml
from PIL import Image
from scipy.spatial.transform import Rotation
from smartdish_a04_clearance import HALF,PADDING,REGISTRATION_MARGIN,NOMINAL,save,sha,require
from smartdish_robot.product_contract import PROFILE
from smartdish_robot.product_navigation import make_nav_client
from smartdish_robot.product_transfer import ProductTransferController
from smartdish_robot.product_gazebo_backend import DISH_NAMES,TRAY_TOP,PLATE_HEIGHT,PLATE_RADIUS,FIXTURE,GazeboEntityServices,relative_xyz
from smartdish_robot.product_physics import ROBOT,POSE_PREFIX

SPEED=.20
ANGULAR=.60
ACCEL=.25
ANGULAR_ACCEL=.60
MAX_POSE_GAP_NS=250_000_000
MAX_SKEW_NS=150_000_000
MIN_CLEARANCE=.05
CENTER_LIMIT=.015
TILT_LIMIT=.035
LEGS=(("TO_TABLE","T03"),("TO_RETURN","DISH_RETURN"),("TO_HOME","HOME"))

def localization_map(g,out):
    """Separate exact scan-plane SDF map for AMCL, not inflated safety map.
    The S7 collision world is unchanged. Cell centers approximate scan surfaces
    within half a cell, not a 100mm buffer or elevated projection.
    """
    out=Path(out);res=.05;ox,oy=-2.55,-2.45;w,h=206,186
    x,y=np.meshgrid(ox+(np.arange(w)+.5)*res+NOMINAL[0],
                    oy+(np.arange(h)+.5)*res+NOMINAL[1])
    f=g["floor"];lo,hi=f["lo"],f["hi"]
    a=np.full((h,w),205,dtype=np.uint8)
    a[(x>=lo[0])&(x<=hi[0])&(y>=lo[1])&(y<=hi[1])]=254
    z=g["lidar_model_z_m"]+.01
    for c in g["obstacles"]:
        lo,hi=c["lo"],c["hi"]
        if not lo[2]<=z<=hi[2]:continue
        if c["shape"]=="cylinder":
            cx,cy=(lo[0]+hi[0])/2,(lo[1]+hi[1])/2
            radius=(hi[0]-lo[0])/2
            mask=np.hypot(np.maximum(abs(x-cx)-res/2,0),np.maximum(abs(y-cy)-res/2,0))<=radius
        else:mask=(x>=lo[0]-res/2)&(x<=hi[0]+res/2)&(y>=lo[1]-res/2)&(y<=hi[1]+res/2)
        a[mask]=0
    pgm=out/"localization.pgm";path=out/"localization.yaml"
    Image.fromarray(a[::-1]).save(pgm)
    path.write_text(yaml.safe_dump(dict(image=pgm.name,mode="trinary",resolution=res,origin=[ox,oy,0],
                                        negate=0,occupied_thresh=.65,free_thresh=.196),sort_keys=False))
    save(out/"localization_manifest.json",dict(scope="SDF_SCAN_PLANE_AMCL_ONLY",scan_z_m=z,
        world_sha256=g["world_sha256"],pgm_sha256=sha(pgm),yaml_sha256=sha(path),
        resolution=res,origin=[ox,oy,0],dimensions=[w,h],registration_buffer_m=0,
        classes={str(k):int(np.sum(a==k)) for k in (0,205,254)},planning_map_separate=True))
    return path

def moving_params(p):
    cp=p["controller_server"]["ros__parameters"]
    fp=cp["FollowPath"]
    require("MPPIController" in fp["plugin"],"UNREVIEWED_CONTROLLER")
    fp.update(vx_max=SPEED,vx_min=-.08,wz_max=ANGULAR,ax_max=ACCEL,ax_min=-ACCEL,az_max=ANGULAR_ACCEL,
              visualize=False,vx_std=.10,wz_std=.20)
    fp["CostCritic"]["consider_footprint"]=True
    p["global_costmap"]["global_costmap"]["ros__parameters"]["static_layer"]["map_topic"]="/a04/clearance_map"
    # Preserve position/yaw tolerance; enforce controller and smoother limits.
    sm=p["velocity_smoother"]["ros__parameters"]
    sm.update(max_velocity=[SPEED,0.,ANGULAR],min_velocity=[-.08,0.,-ANGULAR],
              max_accel=[ACCEL,0.,ANGULAR_ACCEL],max_decel=[-ACCEL,0.,-ANGULAR_ACCEL])
    behavior=p["behavior_server"]["ros__parameters"]
    behavior.update(max_rotational_vel=ANGULAR,min_rotational_vel=.15,rotational_acc_lim=ANGULAR_ACCEL)
    return p

def instrument(world_path,robot_path,bridge,scene,observer_plugin):
    """Add observation sensors only; retain originals and generated diff provenance."""
    roots=[ET.parse(world_path),ET.parse(robot_path)]
    world=roots[0].getroot().find("world")
    ET.SubElement(world,"plugin",filename="gz-sim-contact-system",name="gz::sim::systems::Contact")
    require(observer_plugin is not None and Path(observer_plugin).is_file(),"ECM_OBSERVER_PLUGIN_MISSING")
    observer=ET.SubElement(world,"plugin",filename=str(Path(observer_plugin).resolve()),name="smartdish::A04Observer")
    ET.SubElement(observer,"output").text=str((world_path.parent.parent/"ecm").resolve())
    sources={}
    for root,models in ((roots[0],world.findall("model")),(roots[1],roots[1].getroot().findall("model"))):
        for model in models:
            for link in model.findall("link"):
                for col in link.findall("collision"):
                    # The floor and every static obstacle already observe
                    # wheel/caster pairs. Avoid redundant high-rate streams
                    # (actual RED: 4 duplicate support topics ~2600 callbacks).
                    if model.get("name")=="turtlebot3_waffle_pi" and link.get("name") in (
                        "wheel_left_link","wheel_right_link","caster_back_left_link","caster_back_right_link"):
                        continue
                    key="c%03d"%len(sources)
                    topic="/smartdish/a04/contact/"+key
                    sensor=ET.SubElement(link,"sensor",name="a04_"+key,type="contact")
                    ET.SubElement(sensor,"always_on").text="true"
                    ET.SubElement(sensor,"update_rate").text="50"
                    contact=ET.SubElement(sensor,"contact")
                    ET.SubElement(contact,"collision").text=col.get("name")
                    ET.SubElement(contact,"topic").text=topic
                    sources[topic]={"model":model.get("name"),"link":link.get("name"),"collision":col.get("name")}
                    bridge.append(dict(ros_topic_name=topic,gz_topic_name=topic,
                          ros_type_name="ros_gz_interfaces/msg/Contacts",gz_type_name="gz.msgs.Contacts",direction="GZ_TO_ROS"))
    for path,root in zip((world_path,robot_path),roots):
        path.with_suffix(".before_contact.sdf").write_bytes(path.read_bytes())
        root.write(path,encoding="utf-8",xml_declaration=True)
    scene["world_sha256"]=sha(world_path)
    scene["observer_only_overlay"]=True
    save(world_path.with_suffix(".manifest.json"),scene)
    save(world_path.parent/"contact_sources.json",sources)
    return sources

def clearance_world(geom,xy,tilt):
    """Conservative all-yaw envelope, extra tip projection for actual robot tilt."""
    x,y=xy
    f=geom["floor"]
    bounds=[("floor_boundary",min(x-f["lo"][0],f["hi"][0]-x,y-f["lo"][1],f["hi"][1]-y))]
    for c in geom["obstacles"]:
        lo,hi=c["lo"],c["hi"]
        bounds.append((c["model"]+"/"+c["collision"],math.hypot(max(lo[0]-x,x-hi[0],0),max(lo[1]-y,y-hi[1],0))))
    name,d=min(bounds,key=lambda v:v[1])
    # 1.15m vertical envelope plus 50mm between samples allowance (0.25m/s × 0.25s / 2 plus margin).
    return name,d-math.sqrt(2)*(HALF+PADDING)-1.15*math.sin(abs(tilt))-.05

def tilt(q):
    r=Rotation.from_quat(q)
    return float(math.acos(max(-1.,min(1.,r.as_matrix()[2,2]))))

def dish_measure(robot,dish,i):
    rel=relative_xyz(robot["xyz"],robot["q"],dish["xyz"])
    orientation=(Rotation.from_quat(robot["q"]).inv()*Rotation.from_quat(dish["q"])).as_quat()
    angle=tilt(orientation)
    return {"xyz":rel,"q":orientation.tolist(),"center_m":math.hypot(rel[0],rel[1]),
            "z_error_m":abs(rel[2]-(TRAY_TOP+PLATE_HEIGHT*(i+.5))),"tilt_rad":angle,
            "edge_bound_m":math.hypot(rel[0],rel[1])+PLATE_RADIUS+PLATE_HEIGHT/2*math.sin(angle)}

def contact_category(source,a,b):
    names=(a,b)
    dish=lambda s:s in {n+"::body::envelope" for n in DISH_NAMES}
    robot=lambda s:"waffle_pi" in s or "turtlebot3_waffle_pi" in s
    if not a or not b:return "UNIDENTIFIED"
    if all(dish(s) for s in names):return "DISH_DISH"
    if any(dish(s) for s in names) and "waffle_pi::smartdish_product_tray::platform_collision" in names:return "TRAY_DISH"
    # Contact messages from floor and wheel/caster sensors describe the same
    # physical pair in reverse order. Match exact scoped identities, not topic.
    floor="floor::body::floor_collision"
    support={
        "waffle_pi::wheel_left_link::wheel_left_collision",
        "waffle_pi::wheel_right_link::wheel_right_collision",
        "waffle_pi::caster_back_right_link::collision",
        "waffle_pi::caster_back_left_link::collision",
    }
    if floor in names and any(s in support for s in names):return "GROUND_SUPPORT"
    if all(robot(s) for s in names):return "ROBOT_INTERNAL"
    if any(dish(s) or robot(s) for s in names):return "UNEXPECTED"
    return "ENVIRONMENT_OTHER"

def gate_paths(e):
    require(len(e["paths"])==3 and all(p["status"]==4 and p["error_code"]==0 and
            p["start_error_m"]<=.05 and p["end_error_m"]<=.05 and p["map_all_yaw_clearance_m"]>MIN_CLEARANCE and
            p["live_costmap_all_yaw_clearance_m"]>MIN_CLEARANCE and
            p["physical_swept_bound"]["registration_margin_remaining_m"]>MIN_CLEARANCE and
            p["max_nominal_registration_difference_m"]<=REGISTRATION_MARGIN for p in e["paths"]),"ACTUAL_PATH_CLEARANCE_GATE")
    require(e["stationary"]["stop_verified"] and e["stationary"]["cmd_nonzero_count"]==0,"STATIONARY_GATE")
    require(any(p["name"]=="docking_server" for p in e["publishers"]["/cmd_vel_nav"]),"DOCKING_ROUTE")
    require(any(p["name"]=="velocity_smoother" for p in e["subscribers"]["/cmd_vel_nav"]) and
            any(p["name"]=="collision_monitor" for p in e["subscribers"]["/cmd_vel_smoothed"]) and
            any(p["name"]=="ros_gz_bridge" for p in e["subscribers"]["/cmd_vel"]),"CHAIN_SUBSCRIBERS")

class Witness:
    def __init__(self,node,out,phys,geom,sources,buffer,state,clock):
        from rclpy.qos import qos_profile_sensor_data
        from ros_gz_interfaces.msg import Contacts
        from tf2_msgs.msg import TFMessage
        self.node=node;self.out=out;self.phys=phys;self.geom=geom;self.sources=sources
        self.buffer=buffer;self.state=state;self.clock=clock;self.raw={};self.bad=None;self.phase="startup"
        self.counts=dict.fromkeys(sources,0);self.categories={};self.last=None;self.last_dishes=None
        self.trace=(out/"motion_pose.jsonl").open("w");self.contacts=(out/"contacts.jsonl").open("w")
        self.contact_health={};self.subs=[];self.active=False
        self.summary={}
        def pose(m,name):
            for t in m.transforms:
                if t.child_frame_id.split("::")[-1].split("/")[-1]!=name:continue
                stamp=t.header.stamp.sec*10**9+t.header.stamp.nanosec
                if stamp<=0:continue # never replace physical header with clock
                p=t.transform.translation;q=t.transform.rotation
                v={"xyz":[p.x,p.y,p.z],"q":[q.x,q.y,q.z,q.w],"sim_ns":stamp,"steady_s":time.monotonic(),"name":name}
                if not all(math.isfinite(x) for x in v["xyz"]+v["q"]):self.bad="NONFINITE_RAW_POSE";continue
                last=self.raw.get(name)
                if last and stamp<last["sim_ns"]:self.bad="POSE_EPOCH_REVERSED"
                if not last or stamp>last["sim_ns"]:self.raw[name]=v
        def cb(m,topic):
            stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
            self.counts[topic]+=1
            self.contact_health[topic]=stamp
            for hit in m.contacts:
                a,b=str(hit.collision1.name),str(hit.collision2.name)
                cat=contact_category(sources[topic],a,b)
                self.categories[cat]=self.categories.get(cat,0)+1
                row={"phase":self.phase,"topic":topic,"sim_ns":stamp,"category":cat,"collision1":a,"collision2":b,
                     "collision1_id":int(hit.collision1.id),"collision2_id":int(hit.collision2.id)}
                self.contacts.write(json.dumps(row)+"\n")
                if self.active and (stamp<=0 or cat in ("UNEXPECTED","UNIDENTIFIED")):self.bad="CONTACT_"+cat
        for n in (ROBOT,*DISH_NAMES):
            self.subs.append(node.create_subscription(TFMessage,POSE_PREFIX+n,lambda m,n=n:pose(m,n),qos_profile_sensor_data))
        for topic in sources:
            self.subs.append(node.create_subscription(Contacts,topic,lambda m,t=topic:cb(m,t),qos_profile_sensor_data))
    def begin(self,phase,loaded_ids):
        self.phase=phase;self.active=True;self.loaded_ids=loaded_ids;self.last=None;self.last_dishes=None
        self.summary[phase]={"samples":0,"min_clearance_m":None,"max_registration_error_m":0.,"max_pose_gap_ns":0,
                             "max_center_m":0.,"max_z_error_m":0.,"max_tilt_rad":0.,"max_dish_gap_ns":0,
                             "max_odom_linear_mps":0.,"max_odom_angular_radps":0.}
    def sample(self):
        from rclpy.time import Time
        require(self.bad is None,self.bad)
        now=time.monotonic()
        robot=self.raw.get(ROBOT)
        require(robot and now-robot["steady_s"]<=.5,"RAW_ROBOT_POSE_STALE")
        if self.last and robot["sim_ns"]<=self.last["sim_ns"]:return
        dishes=[self.raw.get(n) for n in DISH_NAMES] if self.loaded_ids else []
        if dishes:
            require(all(p and now-p["steady_s"]<=.5 for p in dishes),"RAW_DISH_POSE_STALE")
            if max(abs(p["sim_ns"]-robot["sim_ns"]) for p in dishes)>MAX_SKEW_NS:
                require(not self.last or robot["sim_ns"]-self.last["sim_ns"]<=MAX_POSE_GAP_NS,"DISH_POSE_SKEW")
                return
            if self.last_dishes and not all(p["sim_ns"]>q["sim_ns"] for p,q in zip(dishes,self.last_dishes)):
                require(not self.last or robot["sim_ns"]-self.last["sim_ns"]<=MAX_POSE_GAP_NS,"DISH_POSE_GAP")
                return
        s=self.summary[self.phase]
        gap=robot["sim_ns"]-self.last["sim_ns"] if self.last else 0
        require(gap<=MAX_POSE_GAP_NS,"ROBOT_POSE_GAP")
        s["max_pose_gap_ns"]=max(s["max_pose_gap_ns"],gap)
        if dishes and self.last_dishes:
            dg=max(p["sim_ns"]-q["sim_ns"] for p,q in zip(dishes,self.last_dishes))
            s["max_dish_gap_ns"]=max(s["max_dish_gap_ns"],dg)
            require(dg<=MAX_POSE_GAP_NS,"DISH_POSE_GAP")
        query=Time(nanoseconds=robot["sim_ns"])
        if not self.buffer.can_transform("map","base_footprint",query):
            require(not self.last or robot["sim_ns"]-self.last["sim_ns"]<=MAX_POSE_GAP_NS,"POSE_TF_SYNC_GAP")
            return
        t=self.buffer.lookup_transform("map","base_footprint",query)
        mapxy=[t.transform.translation.x,t.transform.translation.y]
        reg=math.dist(robot["xyz"][:2],[mapxy[0]+NOMINAL[0],mapxy[1]+NOMINAL[1]])
        rt=tilt(robot["q"]);obstacle,clear=clearance_world(self.geom,robot["xyz"][:2],rt)
        measures=[dish_measure(robot,p,i) for i,p in enumerate(dishes)]
        od=self.state.get("odom_msg")
        require(od is not None,"ODOM_MISSING")
        v=od.twist.twist.linear;w=od.twist.twist.angular
        linear=math.sqrt(v.x*v.x+v.y*v.y+v.z*v.z);angular=math.sqrt(w.x*w.x+w.y*w.y+w.z*w.z)
        row={"phase":self.phase,"robot_world":robot,"dish_world":dishes,"entity_ids":self.loaded_ids,
             "relative":measures,"map_xy":mapxy,"registration_error_m":reg,"clearance_m":clear,
             "nearest_obstacle":obstacle,"robot_tilt_rad":rt,"odom_linear_mps":linear,"odom_angular_radps":angular,
             "odom_stamp_ns":od.header.stamp.sec*10**9+od.header.stamp.nanosec}
        self.trace.write(json.dumps(row,allow_nan=False)+"\n")
        self.trace.flush()
        s["samples"]+=1;s["min_clearance_m"]=clear if s["min_clearance_m"] is None else min(clear,s["min_clearance_m"])
        s["max_registration_error_m"]=max(reg,s["max_registration_error_m"])
        s["max_odom_linear_mps"]=max(linear,s["max_odom_linear_mps"]);s["max_odom_angular_radps"]=max(angular,s["max_odom_angular_radps"])
        for m in measures:
            for k,v in (("max_center_m",m["center_m"]),("max_z_error_m",m["z_error_m"]),("max_tilt_rad",m["tilt_rad"])):
                s[k]=max(s[k],v)
        self.last=robot;self.last_dishes=dishes
        require(clear>MIN_CLEARANCE,"ACTUAL_MOVING_CLEARANCE")
        require(reg<=REGISTRATION_MARGIN,"ACTUAL_MOVING_REGISTRATION")
        require(rt<=.05,"ACTUAL_ROBOT_TILT")
        require(linear<=SPEED+.05 and angular<=ANGULAR+.10,"ACTUAL_VELOCITY_LIMIT")
        require(all(m["center_m"]<=CENTER_LIMIT and m["z_error_m"]<=.02 and m["tilt_rad"]<=TILT_LIMIT and
                    m["edge_bound_m"]<=.27 for m in measures),"DISH_RELATIVE_POSE_LIMIT")
    def end(self):
        self.active=False
        require(self.summary[self.phase]["samples"]>=5,"MOVING_POSE_COVERAGE")
    def close(self):
        self.trace.close();self.contacts.close()
        return {"phase_summary":self.summary,"contact_callback_counts":self.counts,"contact_categories":self.categories,
                "contact_last_header_ns":self.contact_health,
                "contact_absence_proven":False,"contact_silence_policy":"EVENT_ONLY_NOT_NEGATIVE_EVIDENCE"}

def run_missions(node,out,phys,g,sources,buffer,state,clock,e,scene,static,target,spin,wait):
    """First empty then actual load/unload. Both use actual accepted Nav2 UUID."""
    from smartdish_a04_no_goal import endpoints
    gate_paths(e)
    e["motion_authorized"]="CI_ISOLATED_DIAGNOSTIC_ONLY"
    e["moving"]={"legs":[],"transfers":[],"accepted":[],"cancel_results":[]}
    result=[];accepted=e["moving"]["accepted"];cancel=e["moving"]["cancel_results"]
    witness=Witness(node,out,phys,g,sources,buffer,state,clock)
    nav=None;start_xy=None
    def current_xy():
        o=state["odom_msg"];return (o.pose.pose.position.x,o.pose.pose.position.y)
    def check_graph():
        return ([p["name"] for p in endpoints(node,"/cmd_vel")]==["collision_monitor"] and
                [p["name"] for p in endpoints(node,"/cmd_vel_smoothed")]==["velocity_smoother"] and
                len(endpoints(node,"/clock"))==1)
    def arrival(req):
        p=state["amcl"].pose.pose.position;d=target[req["destination_id"]]
        return math.dist((p.x,p.y),(d["x"],d["y"]))<=.8 and math.dist(current_xy(),start_xy)>.25
    def onaccepted(r,l,u):
        accepted.append({"request_id":r,"leg":l,"goal_uuid":u,"steady_s":time.monotonic()});return True
    nav=make_nav_client(node,target,phys.stop,onaccepted,result.append,cancel.append,check_graph,arrival)
    nav.timeout=240.
    ctl=ProductTransferController(nav,phys,scene,static,out/"product_receipts",e["source_sha"],timeout_s=20.)
    def pulse():
        spin();nav.tick()
    def guard():
        require(check_graph() and not phys.callback_error,"MOVING_GRAPH_OR_SENSOR_ERROR")
        require(time.monotonic()-state["times"].get("scan",0)<=.8 and time.monotonic()-state["times"].get("odom",0)<=.3,"MOVING_SENSOR_STALE")
    def leg(mission,label,dest,ids):
        nonlocal start_xy
        request={"schema_version":2,"profile":PROFILE,"request_id":mission,"leg":label,"destination_id":dest}
        require(nav.active is None and not nav.locked,"NAV_LOCKED")
        wait(lambda:witness.raw.get(ROBOT) and time.monotonic()-witness.raw[ROBOT]["steady_s"]<=.5 and
             (not ids or all(witness.raw.get(n) and time.monotonic()-witness.raw[n]["steady_s"]<=.5 for n in DISH_NAMES)),10,"RAW_POSE_READY")
        start_xy=current_xy();start_scan=state["scan"];start_odom=state["odom"];result.clear()
        row={"mission":mission,"leg":label,"destination_id":dest,"loaded_entity_ids":ids,"status":"STARTED","start_sim_ns":clock[-1]}
        e["moving"]["legs"].append(row);witness.begin(mission+"_"+label,ids)
        guard();nav.start(request);e["navigate_to_pose_goals_sent"]+=1
        deadline=time.monotonic()+260;maxmove=0.
        while time.monotonic()<deadline:
            before=nav.active
            pulse();guard();witness.sample();maxmove=max(maxmove,math.dist(current_xy(),start_xy))
            if before and before.terminal_at is not None:
                row["terminal_steady_s"]=before.terminal_at
                if phys.stop.start is not None and phys.stop.last_at is not None:
                    row["post_terminal_stop_dwell_s"]=max(0.,phys.stop.last_at-max(phys.stop.start,before.terminal_at))
            if nav.active is None:break
        else:raise RuntimeError("LEG_TIMEOUT")
        witness.end()
        require(len(result)==1 and result[0]["result"]=="SUCCEEDED" and result[0]["terminal_status"]=="SUCCEEDED" and result[0]["stop_verified"],"NAV_TERMINAL_STOP:"+str(result))
        p=state["amcl"].pose.pose.position;d=target[dest]
        row.update(result[0],status="SUCCEEDED",end_sim_ns=clock[-1],odom_displacement_m=maxmove,odom_samples=state["odom"]-start_odom,
                   scan_samples=state["scan"]-start_scan,amcl_error_m=math.dist((p.x,p.y),(d["x"],d["y"])))
        require(maxmove>.25 and row["amcl_error_m"]<=.8 and row["scan_samples"]>=3 and row["odom_samples"]>=3 and row.get("post_terminal_stop_dwell_s",0)>=1.-1e-9,"ARRIVAL_EVIDENCE")
        save(out/"moving_progress.json",e["moving"])
    def transfer(mission,op,dest,seconds):
        receipt=ctl.note_arrival()
        while time.monotonic()-receipt["stop_steady_s"]<seconds:
            pulse();guard();require(phys.stop.verified(time.monotonic()),"WAIT_NOT_STOPPED")
        witness.phase=op
        req={"schema_version":2,"profile":PROFILE,"request_id":mission,"stack_id":scene["stack_id"],
             "transfer_id":mission+"-"+op,"operation":op,"destination_id":dest}
        t=time.monotonic();ack=ctl.run(req);elapsed=time.monotonic()-t
        e["moving"]["transfers"].append({"request":req,"ack":ack,"elapsed_wall_s":elapsed})
        require(ack["status"]=="ACK" and elapsed<=20.,"ACTUAL_TRANSFER_FAILED:"+str(ack))
        save(out/"moving_progress.json",e["moving"]);return ack
    try:
        ctl.arm_verified()
        for label,dest in LEGS:leg("a04-empty",label,dest,None)
        # New request_id, same actual world/fixture and empty tray.
        mission="a04-loaded"
        leg(mission,"TO_TABLE","T03",None)
        load=transfer(mission,"LOAD","T03",10.)
        ids=ctl.loaded_ids
        require(ids and len(ids)==3,"LOAD_IDS")
        actual=GazeboEntityServices(out/"loaded_scene",timeout_s=2.).scene()
        require([actual.get(n) for n in DISH_NAMES]==ids,"LOADED_SCENE_ID_DRIFT")
        # Save actual loaded RGB strictly after physical load.
        frame=phys.until(lambda:phys.cache.select(load["event_sim_ns"],time.monotonic()),5,"POST_LOAD_RGB")
        (out/"loaded.rgb").write_bytes(frame.rgb)
        from PIL import Image
        Image.frombytes("RGB",(640,480),frame.rgb).save(out/"loaded.png")
        e["moving"]["loaded_rgb"]={"stamp_ns":frame.stamp_ns,"rgb_sha256":sha(out/"loaded.rgb"),"png_sha256":sha(out/"loaded.png")}
        leg(mission,"TO_RETURN","DISH_RETURN",ids)
        actual=GazeboEntityServices(out/"arrival_scene",timeout_s=2.).scene()
        require([actual.get(n) for n in DISH_NAMES]==ids,"ARRIVAL_SCENE_ID_DRIFT")
        unload=transfer(mission,"UNLOAD","DISH_RETURN",5.)
        require(unload["entity_ids"]==load["entity_ids"],"UNLOAD_IDS")
        leg(mission,"TO_HOME","HOME",None)
        e["moving"]["verdict"]="ACTUAL_SIX_LEGS_AND_TRANSFER_COMPLETE_PENDING_ECM_REVIEW"
    except BaseException:
        witness.active=False
        if nav and nav.active:
            nav.abort_pending()
            until=time.monotonic()+15.
            while nav.active and time.monotonic()<until:
                try:pulse()
                except Exception:break
            e["moving"]["cancel_drained"]=nav.active is None
        raise
    finally:
        e["moving"]["witness"]=witness.close()
        save(out/"moving_progress.json",e["moving"])
