"""Fail-closed A15 physical evidence contract; no label approval."""
import csv,math
from collections import defaultdict
from pathlib import Path
from smartdish_a14_physics import transform_relative,norm_q,rotate,q_conjugate
from a15_pilot_world import STEP_NS,TRIGGER_NS,DURATION_NS,END_NS,TORQUE_NM

NAMES={"dish_01","dish_02","tray_platform","camera"}
def need(ok,reason):
    if not ok:raise ValueError(reason)
def load_poses(path):
    tracks=defaultdict(dict);ids={}
    with Path(path).open() as f:
        for n,r in enumerate(csv.DictReader(f,delimiter="\t")):
            need(n<80000 and r["sim_ns"]!="OVERFLOW","A15_POSE_LIMIT")
            t=int(r["sim_ns"]);name=r["entity"];eid=int(r["entity_id"])
            need(name in NAMES and eid>0 and t>0 and t%STEP_NS==0 and t not in tracks[name],"A15_POSE_ID_TIME")
            need(ids.setdefault(name,eid)==eid,"A15_POSE_ID_DRIFT")
            p={k:float(r[k]) for k in ("x","y","z","qx","qy","qz","qw")}
            need(all(math.isfinite(v) for v in p.values()),"A15_POSE_NONFINITE")
            norm_q([p[k] for k in ("qx","qy","qz","qw")])
            tracks[name][t]=(int(r["iteration"]),p)
    need(set(tracks)==NAMES and len(set(ids.values()))==len(NAMES),"A15_POSE_ENTITY_SET")
    return tracks
def pose(tracks,name,t):
    return tracks[name][t][1]
def rel(tracks,name,t):
    return transform_relative(pose(tracks,"tray_platform",t),pose(tracks,name,t))
def point(r):
    return tuple(r["translation_m"][k] for k in ("x","y","z"))
def quat(r):
    return tuple(r["quaternion"][k] for k in ("x","y","z","w"))
def angle(a,b):
    return 2*math.acos(min(1.,abs(sum(x*y for x,y in zip(a,b)))))
def grid(tracks,start,end):
    times=range(start,end+1,STEP_NS)
    for t in times:
        need(all(t in tracks[n] for n in NAMES),"A15_POSE_WINDOW_GAP")
        it={tracks[n][t][0] for n in NAMES}
        need(len(it)==1,"A15_POSE_ITERATION_SKEW")
        if t>start:need(tracks["tray_platform"][t][0]==tracks["tray_platform"][t-STEP_NS][0]+1,"A15_POSE_ITERATION_GAP")
    return times
def check_initial(tracks,meta,t0,info,ecm):
    need(1_400_000_000<=t0<=2_000_000_000 and t0<TRIGGER_NS and t0%STEP_NS==0,"A15_CAPTURE_TIME")
    begin=t0-200_000_000
    times=grid(tracks,begin,t0)
    need(info["width"]==640 and info["height"]==480 and len(info["k"])==9 and all(math.isfinite(x) for x in info["k"]) and info["k"][0]>0 and info["k"][4]>0 and abs(info["stamp_ns"]-t0)<=200_000_000,"A15_CAMERA_INFO")
    camera=pose(tracks,"camera",t0);cq=norm_q([camera[k] for k in ("qx","qy","qz","qw")]);origin=tuple(camera[k] for k in ("x","y","z"))
    fx,fy,cx,cy=info["k"][0],info["k"][4],info["k"][2],info["k"][5]
    result={}
    for d in meta["initial_dishes"]:
        n=d["name"];r=rel(tracks,n,t0);p=point(r);q=quat(r)
        displacement=max(math.dist(point(rel(tracks,n,t)),p) for t in times)
        rotation=max(angle(quat(rel(tracks,n,t)),q) for t in times)
        need(displacement<=.002 and rotation<=.05,"A15_PRE_T0_NOT_SETTLED_"+n)
        rad=math.hypot(d["radius_m"],d["thickness_m"]/2)
        need(abs(p[0])+rad<=meta["platform"]["width_m"]/2 and abs(p[1])+rad<=meta["platform"]["depth_m"]/2,"A15_INITIAL_OUTSIDE_TRAY_"+n)
        # Conservative 3D bounding cube projection, not an occlusion mask.
        world=pose(tracks,n,t0);pixels=[]
        for dx in (-rad,rad):
            for dy in (-rad,rad):
                for dz in (-rad,rad):
                    local=rotate(q_conjugate(cq),tuple(world[k]+v-o for k,v,o in zip(("x","y","z"),(dx,dy,dz),origin)))
                    need(local[0]>.05,"A15_CAMERA_DEPTH")
                    pixels.append((cx-fx*local[1]/local[0],cy-fy*local[2]/local[0]))
        bbox=[min(x for x,y in pixels),min(y for x,y in pixels),max(x for x,y in pixels),max(y for x,y in pixels)]
        need(0<=bbox[0]<=bbox[2]<640 and 0<=bbox[1]<=bbox[3]<480,"A15_CAMERA_FOV_"+n)
        result[n]={"relative_pose":r,"settle_max_displacement_m":displacement,"settle_max_rotation_rad":rotation,"conservative_projected_bbox_px":bbox}
    relevant=[r for r in ecm if t0-50_000_000<=r["sim_ns"]<=t0]
    ids={}
    for row in relevant:
        need(row["present"] and row["collision_id"]>0,"A15_SUPPORT_COMPONENT")
        need(ids.setdefault(row["model"],row["collision_id"])==row["collision_id"],"A15_SUPPORT_ID_DRIFT")
    need({"tray_platform","dish_01","dish_02"}<=set(ids),"A15_SUPPORT_IDS_MISSING")
    wanted=[("tray_platform","dish_01"),("dish_01","dish_02")]
    support={}
    for a,b in wanted:
        pair={ids[a],ids[b]}
        stamps=sorted({r["sim_ns"] for r in relevant if any(set(p)==pair for p in r["pairs"])})
        need(bool(stamps),"A15_INITIAL_SUPPORT_UNOBSERVED_"+a+"_"+b)
        support[a+"__"+b]={"last_positive_ns":stamps[-1],"exact_t0_positive":t0 in stamps}
    return {"capture_ns":t0,"settle_window_ns":[begin,t0],"dishes":result,"support":support,"camera_world_pose":camera,"camera_info_stamp_ns":info["stamp_ns"],"camera_info_skew_ns":abs(info["stamp_ns"]-t0),"occlusion_review_required":True}
def check_trigger(path):
    with Path(path).open() as f:rows=list(csv.DictReader(f,delimiter="\t"))
    expected=list(range(TRIGGER_NS,TRIGGER_NS+DURATION_NS,STEP_NS))
    need([int(r["sim_ns"]) for r in rows]==expected and len({int(r["link_id"]) for r in rows})==1 and all(int(r["link_id"])>0 and abs(float(r["torque_y_nm"])-TORQUE_NM)<1e-12 for r in rows),"A15_TRIGGER_COMMAND_TRACE")
    need(all(int(b["iteration"])==int(a["iteration"])+1 for a,b in zip(rows,rows[1:])),"A15_TRIGGER_ITERATION")
    return {"command_steps":len(rows),"first_ns":expected[0],"last_ns":expected[-1],"torque_nm":[0,TORQUE_NM,0],"target_link_id":int(rows[0]["link_id"]),"scope":"COMMAND_NOT_MEASURED_WRENCH"}
def metrics(tracks,t0,end=END_NS):
    times=grid(tracks,t0,end);out={}
    tray0=pose(tracks,"tray_platform",t0)
    for t in times:
        need(all(abs(pose(tracks,"tray_platform",t)[k]-v)<1e-8 for k,v in tray0.items()),"A15_TRAY_MOVED")
    for n in ("dish_01","dish_02"):
        rows=[rel(tracks,n,t) for t in times];points=[point(r) for r in rows];q0=quat(rows[0])
        out[n]={"samples":len(rows),"first_ns":t0,"last_ns":end,"cumulative_relative_path_m":sum(math.dist(a,b) for a,b in zip(points,points[1:])),"net_relative_displacement_m":math.dist(points[0],points[-1]),"max_relative_displacement_m":max(math.dist(points[0],p) for p in points),"max_rotation_rad":max(angle(q0,quat(r)) for r in rows),"min_z_m":min(p[2] for p in points),"final_relative_pose":rows[-1]}
    return out
