#!/usr/bin/env python3
"""B independent offline replay; never imports A or registers training data."""
import argparse, csv, hashlib, io, json, math, re, tarfile, tempfile, zipfile
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation
from scipy.ndimage import distance_transform_edt, label
from PIL import Image
import yaml

# (run, artifact, source, zip digest, tar digest, internal file count)
PINS=[
(45954975000,15178590920,"489d2014fbb532c4c285f61869761428c3abf26b","dd0aefc3f007f4574b5a69e4d7b0efa0969bae0d9b9c758c8b58153c422f00c0","d7054598dfe83dfad47e513ec172e7baf4242e57af032900e6e9ce4c125649a9",12),
(45956739176,15178773153,"870262c8c8fc2c509a25d74d6f8ff28c0133db8e","d1ef0f5b8086cea1c13e21395e0cc47ded136e237590621552b57ccaafb1cdc3","3e4089a08f85f301cd2fe083029e75354bc8e576b63d4b90e28a14becf9d35e3",40),
(45967974937,15184188608,"e48778e6825a022c8fd249a5c501095b7daa83e3","b36312e517b072b3e6d9d99084d67df6971afc4219a3bdc0d414a01418ea51f7","50dd17ad17061ababe1624bb7f92441e8eff1855ff6810721ccbdbf4fd179b89",70),
(45970380453,15185112687,"247db79e239d7694406a23e77d5c9e5e9acc58fb","d8c41b262b35738f01f0ac0042485c6bc078d0a36a9cd9edc2fda9b674d96140","c79f6e56d2638aeee84bc2945fd400714bc229024b5480ff4486769ff0cdbaf9",72),
(45972717341,15185567891,"7d8bf9ec30f88c79ed1035b485a40aa3e7c3b688","75b5529c69098f8ef2d4c0c2e4945514f93d4bd468740880ecc7fa6ef99b2286","b1f9ca5867bd986b6e85a453ac35c55c153fc0ac5669844a0ab8191ba7fbfefc",60)]
UPSTREAM="45633014a14e8f438495b532a723e4ad45cbbd31"
IDS=[159,164,169]
class QAError(ValueError): pass
def need(ok,code):
    if not ok: raise QAError(code)
def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+"\n")
def safe_name(n):
    return bool(n and not PurePosixPath(n).is_absolute() and all(v not in ("",".","..") for v in n.split("/")) and "\\" not in n and ":" not in n)
def intake(zpath,dst,pin):
    run,aid,source,zh,th,count=pin
    need(sha(zpath)==zh,"ZIP_SHA")
    with zipfile.ZipFile(zpath) as z:
        names=z.namelist(); tar=[x for x in names if x.endswith(".tar.gz")]
        need(len(tar)==1 and len(names)==2 and all(safe_name(x) for x in names),"ZIP_SET")
        n=tar[0]; need(n+".sha256" in names and z.getinfo(n).file_size<100_000_000,"ZIP_SIZE")
        body=z.read(n);need(hashlib.sha256(body).hexdigest()==th,"TAR_SHA")
        need(z.read(n+".sha256").decode().split()[0]==th,"TAR_SIDECAR")
    with tarfile.open(fileobj=io.BytesIO(body),mode="r:gz") as t:
        seen=set();total=0;root=None
        for m in t:
            need(safe_name(m.name) and m.name not in seen and (m.isfile() or m.isdir()) and not m.issparse(),"TAR_MEMBER")
            seen.add(m.name); total+=m.size
            need(total<500_000_000 and len(seen)<200 and m.size<=200_000_000,"TAR_LIMIT")
            top=m.name.split("/")[0]
            if root is None:root=top
            need(root==top and root in ("a04","a04_live"),"TAR_ROOT")
            dest=dst/m.name
            if m.isdir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open("xb") as f:
                    import shutil
                    shutil.copyfileobj(t.extractfile(m),f)
                need(dest.stat().st_size==m.size,"TAR_SIZE")
    root=dst/root
    indexed={}
    for line in (root/"SHA256SUMS").read_text().splitlines():
        h,n=line.split("  ",1);n=n.removeprefix("./")
        need(safe_name(n) and n not in indexed and re.fullmatch("[0-9a-f]{64}",h),"INDEX_FORMAT")
        need(sha(root/n)==h,"INNER_SHA");indexed[n]=h
    actual={x.relative_to(root).as_posix() for x in root.rglob("*") if x.is_file()}-{"SHA256SUMS"}
    need(set(indexed)==actual and len(actual)==count,"INDEX_SET")
    need((root/"source_sha.txt").read_text().strip()==source and (root/"upstream_sha.txt").read_text().strip()==UPSTREAM,"SOURCE_PIN")
    return root,dict(run_id=run,artifact_id=aid,source_sha=source,zip_sha256=zh,tar_sha256=th,internal_files=count,upstream_sha=UPSTREAM,verdict="PASS")
def pose(e):
    vals=np.fromstring(e.findtext("pose","0 0 0 0 0 0"),sep=" ")
    need(len(vals)==6 and np.isfinite(vals).all() and not (e.find("pose") is not None and e.find("pose").attrib),"SDF_POSE")
    t=np.eye(4);t[:3,:3]=Rotation.from_euler("xyz",vals[3:]).as_matrix();t[:3,3]=vals[:3];return t
def extent(g):
    if g.find("box") is not None:return np.fromstring(g.findtext("box/size"),sep=" ")/2
    if g.find("cylinder") is not None:return np.array([float(g.findtext("cylinder/radius"))]*2+[float(g.findtext("cylinder/length"))/2])
    if g.find("sphere") is not None:return np.repeat(float(g.findtext("sphere/radius")),3)
    raise QAError("SDF_SHAPE")
def model_data(m):
    corners=np.array([[a,b,c] for a in (-1,1) for b in (-1,1) for c in (-1,1)])
    boxes=[];parts=[]
    for l in m.findall("link"):
        base=pose(m)@pose(l)
        for c in l.findall("collision"):
            t=base@pose(c); v=(corners*extent(c.find("geometry")))@t[:3,:3].T+t[:3,3]
            boxes.append((m.get("name"),l.get("name"),c.get("name"),v.min(axis=0),v.max(axis=0)))
        i=l.find("inertial")
        if i is not None:
            t=base@pose(i);mass=float(i.findtext("mass"))
            a,b,c,d,e,f=[float(i.findtext("inertia/"+k)) for k in ("ixx","iyy","izz","ixy","ixz","iyz")]
            I=np.array([[a,d,e],[d,b,f],[e,f,c]])
            need(mass>0 and np.linalg.eigvalsh(I).min()>0,"INERTIA")
            parts.append((mass,t[:3,3],t[:3,:3]@I@t[:3,:3].T))
    return boxes,parts
def mass_summary(parts):
    m=sum(x[0] for x in parts);c=sum(x[0]*x[1] for x in parts)/m
    I=sum(x[2]+x[0]*(np.dot(x[1]-c,x[1]-c)*np.eye(3)-np.outer(x[1]-c,x[1]-c)) for x in parts)
    return dict(mass_kg=m,com_m=c.tolist(),inertia_kg_m2=I.tolist())
def geometry(static,loaded=None):
    world=static/("world.before_contact.sdf" if (static/"world.before_contact.sdf").exists() else "world.sdf")
    robot=static/("transfer_robot.before_contact.sdf" if (static/"transfer_robot.before_contact.sdf").exists() else "overlay/robot.sdf")
    model=ET.parse(robot).getroot().find("model");rc,parts=model_data(model)
    wc=[x for m in ET.parse(world).getroot().find("world").findall("model") for x in model_data(m)[0]]
    floor=next(x for x in wc if x[0]=="floor");obs=[x for x in wc if x[0]!="floor"]
    tray=next(x for x in rc if x[2]=="platform_collision")
    lateral=max(np.max(np.abs(np.r_[x[3][:2],x[4][:2]])) for x in rc)
    need(lateral<=.28 and .245+.015<=.28,"FOOTPRINT")
    lidar=next((l,s) for l in model.findall("link") for s in l.findall("sensor") if s.get("type")=="gpu_lidar")
    z=float((pose(model)@pose(lidar[0])@pose(lidar[1]))[2,3])
    result=dict(robot=mass_summary(parts),robot_half_extent_m=float(lateral),tray_bounds=[tray[3].tolist(),tray[4].tolist()],lidar_model_z_m=z,scan_blind_collision_count=sum(not x[3][2]<=z+.02<=x[4][2] for x in obs),footprint_m=.56,padding_m=.01)
    if loaded:
        pp=[]
        for i,f in enumerate(sorted((loaded/"product_receipts/physical").rglob("*.sdf"))):
            m=ET.parse(f).getroot().find("model");c,p=model_data(m)
            need(len(p)==1 and len(c)==1,"DISH_SDF")
            g=m.find(".//collision/geometry/cylinder");r=float(g.findtext("radius"));h=float(g.findtext("length"))
            need(abs(r-.245)<1e-9 and abs(h-.037)<1e-9,"DISH_GEOMETRY")
            pp.append((p[0][0],np.array([0.,0.,tray[4][2]+h*(i+.5)]),p[0][2]))
        need(len(pp)==3,"DISH_SDF_COUNT")
        result["nominal_loaded"]=mass_summary(parts+pp);result["dish_mass_kg"]=[x[0] for x in pp]
    return result,rc,floor,obs
def map_check(static,repo,floor,obs):
    cfg=yaml.safe_load((static/"candidate.yaml").read_text());orig=repo/"maps/restaurant_map.pgm"
    a=js(static/"map_audit.json");need(sha(orig)==a["source_map_sha256"],"ORIGINAL_MAP_PIN")
    def classes(p):
        x=(255-np.asarray(Image.open(p).convert("L"),dtype=float)[::-1])/255
        return np.where(x>cfg["occupied_thresh"],100,np.where(x<cfg["free_thresh"],0,-1))
    old,new=classes(orig),classes(static/"candidate.pgm")
    need(old.shape==new.shape and np.all(new[old==100]==100),"ORIGINAL_OCCUPIED")
    res=cfg["resolution"];ox,oy=cfg["origin"][:2]
    xx,yy=np.meshgrid(ox+(np.arange(new.shape[1])+.5)*res-2.6,oy+(np.arange(new.shape[0])+.5)*res-2.2)
    margin=.1+res/2;lo,hi=floor[3:]
    inside=(xx>=lo[0]+margin)&(xx<=hi[0]-margin)&(yy>=lo[1]+margin)&(yy<=hi[1]-margin)
    for o in obs:
        lo,hi=o[3:];inside &= ~((xx>=lo[0]-margin)&(xx<=hi[0]+margin)&(yy>=lo[1]-margin)&(yy<=hi[1]+margin))
    need(np.all(inside[new==0]),"MAP_FREE_GEOMETRY")
    d=distance_transform_edt(np.pad(new==0,1))[1:-1,1:-1]*res
    lab,_=label(d>math.sqrt(2)*.29+res/math.sqrt(2))
    cells=[lab[math.floor((y-oy)/res),math.floor((x-ox)/res)] for x,y in [(0,0),(5.25,.38),(-1.15,1.6)]]
    need(cells[0]>0 and len(set(cells))==1,"MAP_CONNECTIVITY")
    return dict(occupied_preserved=int(np.sum(old==100)),unknown_to_free=int(np.sum((old==-1)&(new==0))),candidate_connected=True,classes={str(v):int(np.sum(new==v)) for v in (-1,0,100)})
def relative(rp,rq,dp,dq):
    r=Rotation.from_quat(rq);d=Rotation.from_quat(dq);rel=r.inv()*d
    xyz=r.inv().apply(dp-rp);e=rel.as_euler("xyz")
    up=rel.apply(np.broadcast_to([0,0,1],xyz.shape))
    tilt=np.arctan2(np.linalg.norm(up[:,:2],axis=1),up[:,2])
    return xyz,np.c_[e[:,:2],tilt]
def check_clock(t,it,dt):
    need(len(t)>1 and np.all(dt==1_000_000) and np.all(np.diff(t)==1_000_000) and np.all(np.diff(it)==1),"ECM_STEP_GAP")
def pair_kind(a,b):
    a,b=sorted((a,b))
    if a=="floor::body::floor_collision" and (b.startswith("waffle_pi::wheel_") or b.startswith("waffle_pi::caster_")):return "ground"
    if (a.startswith("smartdish_product_dish_") and b=="waffle_pi::smartdish_product_tray::platform_collision"):return "dish"
    if a.startswith("smartdish_product_dish_") and b.startswith("smartdish_product_dish_"):return "dish_dish"
    return "unexpected"
def require_session(e,source,run):
    need(e["source_sha"]==source and str(e["run_id"])==str(run),"SESSION_MISMATCH")
def verify_transfer(a,ids,count):
    need(a["status"]=="ACK" and [int(x) for x in a["entity_ids"]]==ids and a["tray_count"]==count,"TRANSFER_ID_COUNT")
def stats(x,t):
    i=int(np.argmax(x))
    return dict(min=float(np.min(x)),max=float(x[i]),mean=float(np.mean(x)),median=float(np.median(x)),p95=float(np.percentile(x,95)),p99=float(np.percentile(x,99)),max_sim_ns=int(t[i]))
def separation(xy,floor,obs):
    x,y=xy.T;lo,hi=floor[3:]
    d=np.minimum.reduce([x-lo[0],hi[0]-x,y-lo[1],hi[1]-y])
    for o in obs:
        lo,hi=o[3:];d=np.minimum(d,np.hypot(np.maximum.reduce([lo[0]-x,x-hi[0],np.zeros_like(x)]),np.maximum.reduce([lo[1]-y,y-hi[1],np.zeros_like(y)])))
    return d
def check_dish(center,tilt,zerr,edge,mast):
    need(np.max(center)<=.015 and np.max(tilt)<=.035 and np.max(zerr)<=.02 and np.min(edge)>0 and np.min(mast)>0,"DISH_POSE")
def check_clearance(clear):
    need(np.min(clear)>.05,"ENV_CLEARANCE")
def check_rgb_order(frame,event):
    need(type(frame) is int and type(event) is int and frame>event,"RGB_STALE")
def scene_ids(raw):
    # Gazebo scene/info protobuf text: only top-level model records.
    models=re.findall(r'^model \{\n  name: "([^"]+)"\n  id: (\d+)',raw,re.M)
    need(len(models)==len({x[0] for x in models}),"DUPLICATE_SCENE_MODEL")
    return {n:int(i) for n,i in models}
def service_review(log,op,ids=IDS):
    rows=[json.loads(x) for x in Path(log).open()]
    need(rows and all(x["exit"]==0 for x in rows),"SERVICE_EXIT")
    scenes=[scene_ids(x["stdout"]) for x in rows if x["service"]=="scene/info"]
    need(len(scenes)>=2,"SERVICE_SCENE")
    names=[f"smartdish_product_dish_{i:02d}" for i in range(3)]
    first,last=scenes[0],scenes[-1]
    calls=[x for x in rows if x["service"] in ("create","remove")]
    need(all(re.search(r'data:\s*true',x["stdout"]) for x in calls),"SERVICE_RESPONSE")
    removed=[int(re.search(r'id:\s*(\d+)',x["request"]).group(1)) for x in calls if x["service"]=="remove"]
    created=[re.search(r'\bname:\s*"([^"]+)"',x["request"]).group(1) for x in calls if x["service"]=="create"]
    if op=="LOAD":
        need("s6_stacked_dishes" in first and not any(n in first for n in names),"INITIAL_FIXTURE")
        need(removed==[first["s6_stacked_dishes"]] and created==names,"LOAD_CREATE_REMOVE")
        need("s6_stacked_dishes" not in last and [last.get(n) for n in names]==ids,"LOAD_SCENE_IDS")
        # Each new dynamic name must keep its ID until end of LOAD.
        need(all(s[n]==ids[i] for s in scenes for i,n in enumerate(names) if n in s),"LOAD_ID_DRIFT")
    else:
        need([first.get(n) for n in names]==ids and removed==ids and not created and not any(n in last for n in names),"UNLOAD_SCENE_IDS")
    return dict(initial_fixture_id=first.get("s6_stacked_dishes"),initial_dynamic_ids=[first[n] for n in names if n in first],
                final_dynamic_ids=[last[n] for n in names if n in last],created_names=created,removed_ids=removed,scene_snapshots=len(scenes))
def rgb(p,r,stem):
    raw=(p/(stem+".rgb")).read_bytes();png=p/(stem+".png")
    with Image.open(png) as im:need(im.mode=="RGB" and im.size==(640,480) and im.tobytes()==raw,"PNG_RGB")
    need(sha(png)==r["png_sha256"] and hashlib.sha256(raw).hexdigest()==r["rgb_sha256"],"RGB_HASH")
def graph(e):
    for g in e["graph_history"]:
        p=g["publishers"];need([x["name"] for x in p["/cmd_vel"]]==["collision_monitor"] and len(p["/clock"])==1,"GRAPH")
def no_goal(p,e,floor,obs):
    graph(e);rgb(p,e["rgb"],"tray");need(e["stationary"]["stop_verified"] and e["stationary"]["cmd_nonzero_count"]==0,"NO_GOAL_STOP")
    for f in e["footprints"].values():need(np.allclose(f["edge_m"],.58,atol=1e-6) and f["padding"]==.01,"LIVE_FOOTPRINT")
    out=[]
    for row in e["paths"]:
        a=np.array(js(p/row["path_file"]))[:,:2]
        # Segment endpoints plus half max spacing gives a conservative continuous bound.
        step=np.linalg.norm(np.diff(a,axis=0),axis=1)
        tf=e["registration"]["actual_map_to_world"];w=Rotation.from_euler("z",tf[2]).apply(np.c_[a,np.zeros(len(a))])[:,:2]+tf[:2]
        clearance=float(separation(w,floor,obs).min()-math.sqrt(2)*.29-step.max()/2-.1)
        need(row["status"]==4 and clearance>.05,"PLAN_CLEARANCE")
        out.append(dict(path=row["path_file"],length_m=float(step.sum()),clearance_lower_bound_m=clearance))
    need(len(out)==3,"PLAN_COUNT");return out
def replay(p,e,rc,floor,obs,out,aid):
    a=pd.read_csv(p/"ecm_ticks.tsv",sep="\t",low_memory=False)
    t=a.sim_ns.to_numpy();need(np.all(np.diff(t)>0) and np.all(np.diff(a.iteration)>0),"ECM_ORDER")
    pair={}
    for x in csv.DictReader((p/"ecm_pairs.tsv").open(),delimiter="\t"):
        k=x["id1"]+":"+x["id2"];need(k not in pair,"PAIR_DUPLICATE");pair[k]=pair_kind(x["name1"],x["name2"])
    rec=[];series=[];paths=[];legs=e["moving"]["legs"];accepted={x["goal_uuid"] for x in e["moving"]["accepted"]}
    need(len(accepted)==len(e["moving"]["accepted"]),"DUPLICATE_UUID")
    for leg in legs:
        need(leg["goal_uuid"] in accepted and leg["terminal_status"]=="SUCCEEDED" and leg["post_terminal_stop_dwell_s"]>=1 and leg["stop_verified"],"TERMINAL")
        phase=leg["mission"]+"_"+leg["leg"];f=a[(a.sim_ns>=leg["start_sim_ns"])&(a.sim_ns<=leg["end_sim_ns"])]
        tt=f.sim_ns.to_numpy();check_clock(tt,f.iteration.to_numpy(),f.dt_ns.to_numpy())
        need(tt[0]==leg["start_sim_ns"] and tt[-1]==leg["end_sim_ns"],"WINDOW")
        rp=f[["waffle_pi_"+x for x in "x y z".split()]].to_numpy()
        rq=f[["waffle_pi_"+x for x in "qx qy qz qw".split()]].to_numpy()
        need(f.waffle_pi_id.nunique()==1 and f.waffle_pi_id.iloc[0]>0,"ROBOT_ID")
        up=Rotation.from_quat(rq).apply(np.broadcast_to([0,0,1],rp.shape))
        rt=np.arctan2(np.linalg.norm(up[:,:2],axis=1),up[:,2])
        clear=separation(rp[:,:2],floor,obs)-math.sqrt(2)*.29-1.15*np.sin(rt)-.01
        check_clearance(clear)
        wanted=leg["loaded_entity_ids"] or []
        rr=dict(phase=phase,samples=len(f),start_sim_ns=int(tt[0]),end_sim_ns=int(tt[-1]),minimum_clearance_m=float(clear.min()),clearance_min_sim_ns=int(tt[np.argmin(clear)]),robot_tilt_rad=stats(rt,tt),dishes=[])
        for i in range(3):
            n=f"smartdish_product_dish_{i:02d}_";idcol=f[n+"id"].to_numpy()
            need(np.all(idcol==(wanted[i] if wanted else 0)),"DISH_ID")
            if not wanted:continue
            xyz,angle=relative(rp,rq,f[[n+x for x in "x y z".split()]].to_numpy(),f[[n+x for x in "qx qy qz qw".split()]].to_numpy())
            center=np.linalg.norm(xyz[:,:2],axis=1);tilt=angle[:,2];zerr=np.abs(xyz[:,2]-(.445+.037*(i+.5)))
            edge=.27-np.maximum(np.abs(xyz[:,0]),np.abs(xyz[:,1]))-.245-.0185*np.sin(tilt)
            mast=np.full(len(f),np.inf)
            for c in rc:
                if c[2]=="platform_collision":continue
                lo,hi=c[3:];zext=.0185+.245*np.sin(tilt);mask=(xyz[:,2]+zext>=lo[2])&(xyz[:,2]-zext<=hi[2])
                d=np.hypot(np.maximum.reduce([lo[0]-xyz[:,0],xyz[:,0]-hi[0],np.zeros(len(f))]),np.maximum.reduce([lo[1]-xyz[:,1],xyz[:,1]-hi[1],np.zeros(len(f))]))-.245-.0185*np.sin(tilt)
                mast[mask]=np.minimum(mast[mask],d[mask])
            check_dish(center,tilt,zerr,edge,mast)
            relspeed=np.linalg.norm(np.diff(xyz,axis=0),axis=1)*1000
            rr["dishes"].append(dict(id=wanted[i],center_m=stats(center,tt),tilt_rad=stats(tilt,tt),z_error_m=stats(zerr,tt),roll_abs_rad=stats(np.abs(angle[:,0]),tt),pitch_abs_rad=stats(np.abs(angle[:,1]),tt),relative_speed_mps=stats(relspeed,tt[1:]),min_edge_m=float(edge.min()),min_mast_m=float(mast.min()),x_m=stats(xyz[:,0],tt),y_m=stats(xyz[:,1],tt),z_m=stats(xyz[:,2],tt)))
            series.append(pd.DataFrame(dict(sim_ns=tt[::20],phase=phase,dish=wanted[i],center_m=center[::20],tilt_rad=tilt[::20],clearance_m=clear[::20],x=rp[::20,0],y=rp[::20,1])))
        combos={}
        for k in f.pairs.unique():
            keys=[] if k=="-" else k.split(";")
            need(len(keys)==len(set(keys)) and all(x in pair for x in keys),"CONTACT_KEY")
            combos[k]=[pair[x] for x in keys]
        need(np.all(f.pair_count.to_numpy()==f.pairs.map(lambda x:len(combos[x])).to_numpy()) and np.all(f.contact_components>0),"CONTACT_COUNT")
        need(not any("unexpected" in v for v in combos.values()),"UNEXPECTED_CONTACT")
        ground=int(f.pairs.map(lambda x:"ground" in combos[x]).sum());dish=int(f.pairs.map(lambda x:"dish" in combos[x]).sum())
        need(ground==len(f) and (not wanted or dish==len(f)),"POSITIVE_SUPPORT")
        rr.update(ground_steps=ground,tray_steps=dish,goal_uuid=leg["goal_uuid"],stop_dwell_s=leg["post_terminal_stop_dwell_s"])
        paths.append(pd.DataFrame(dict(sim_ns=tt[::20],phase=phase,x=rp[::20,0],y=rp[::20,1],clearance_m=clear[::20])))
        rec.append(rr)
    # DDS pose sample registration uses nominal map origin, independent of A reported scalar.
    rows=[json.loads(x) for x in (p/"motion_pose.jsonl").open()]
    for rr in rec:
        rs=[x for x in rows if x["phase"]==rr["phase"]]
        need(len(rs)>1,"ROS_POSE")
        reg=np.linalg.norm(np.array([x["robot_world"]["xyz"][:2] for x in rs])-(np.array([x["map_xy"] for x in rs])+[-2.6,-2.2]),axis=1)
        need(reg.max()<=.10,"REGISTRATION")
        rr["max_registration_m"]=float(reg.max())
        ts=np.array([x["robot_world"]["sim_ns"] for x in rs]);rr["registration_samples"]=len(rs)
        rr["max_pose_odom_skew_ns"]=int(max(abs(x["robot_world"]["sim_ns"]-x["odom_stamp_ns"]) for x in rs))
        scans=[x for x in rs if "scan" in x]
        need(scans,"SCAN_SAMPLE_MISSING")
        rr["scan_snapshot_count"]=len(scans)
        rr["pose_rows_without_scan"]=len(rs)-len(scans)
        rr["max_pose_scan_skew_ns"]=int(max(abs(x["robot_world"]["sim_ns"]-x["scan"]["stamp_ns"]) for x in scans))
        rr["scan_coverage_scope"]="SAMPLED_ONLY_NOT_FULL_DDS_TRACE"
        errors=[]
        for x in rs:
            m,o,z=x["map_to_odom"],x["odom_to_base"],x["map_to_base"]
            if m["stamp_ns"]!=o["stamp_ns"] or o["stamp_ns"]!=z["stamp_ns"]:continue
            pred=Rotation.from_quat(m["q"]).apply(o["xyz"])+m["xyz"]
            errors.append(float(np.linalg.norm(pred-z["xyz"])))
        rr["tf_same_stamp_samples"]=len(errors)
        rr["tf_translation_residual_max_m"]=max(errors) if errors else None
        leg=next(l for l in legs if l["mission"]+"_"+l["leg"]==rr["phase"])
        post=[x for x in rs if x["robot_world"]["steady_s"]>=leg["terminal_steady_s"]]
        bad=max((i for i,x in enumerate(post) if abs(x["odom_linear_mps"])>.01 or abs(x["odom_angular_radps"])>.02),default=-1)
        tail=post[bad+1:]
        rr["sampled_stop_tail_s"]=tail[-1]["robot_world"]["steady_s"]-tail[0]["robot_world"]["steady_s"] if tail else 0.
        rr["stop_scope"]="RECEIPT_PLUS_DECIMATED_ODOM_NOT_CONTINUOUS_RAW_DWELL"
        pd.DataFrame(dict(sim_ns=ts,registration_m=reg,phase=rr["phase"],
                          linear_mps=[x["odom_linear_mps"] for x in rs],
                          angular_radps=[x["odom_angular_radps"] for x in rs],
                          clearance_m=[x["clearance_m"] for x in rs])).to_csv(out/f"{aid}_{rr['phase']}_ros.csv",index=False)
        vel=np.array([[x["odom_stamp_ns"],x["odom_linear_mps"],x["odom_angular_radps"]] for x in rs]);keep=np.r_[True,np.diff(vel[:,0])>0];vel=vel[keep]
        rr["max_linear_mps"]=float(vel[:,1].max());rr["max_angular_radps"]=float(vel[:,2].max());rr["max_linear_accel_mps2"]=float(np.max(np.abs(np.diff(vel[:,1])/np.diff(vel[:,0])*1e9)))
        rr["max_angular_accel_radps2"]=float(np.max(np.abs(np.diff(vel[:,2])/np.diff(vel[:,0])*1e9)))
    if series:
        s=pd.concat(series);s.to_csv(out/f"{aid}_dish_timeseries.csv",index=False)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        for metric,limit,unit in [("center_m",.015,"m"),("tilt_rad",.035,"rad"),("clearance_m",.05,"m")]:
            fig,ax=plt.subplots()
            for ident,g in s.groupby("dish"):ax.plot(g.sim_ns/1e9,g[metric],label=str(ident))
            ax.axhline(limit,linestyle="--",label="contract");ax.set(xlabel="simulation seconds",ylabel=unit,title=f"{aid} {metric} / {e['source_sha'][:12]}")
            ax.legend();fig.savefig(out/f"{aid}_{metric}.png",dpi=140);plt.close(fig)
    pd.concat(paths).to_csv(out/f"{aid}_world_path.csv",index=False)
    # ROS journal exact-stamp matches are a positive subset, not full DDS coverage.
    from collections import Counter
    contact_counts=Counter(); matched=Counter(); unknown=Counter()
    pair_strings=a.pairs.to_numpy()
    for line in (p/"contacts.jsonl").open():
        x=json.loads(line)
        phase=x["phase"]; t0=x["sim_ns"]; category=pair_kind(x["collision1"],x["collision2"])
        contact_counts[(phase,category)]+=1
        ix=int(np.searchsorted(t,t0))
        if ix<len(t) and t[ix]==t0:
            key=":".join(map(str,sorted((x["collision1_id"],x["collision2_id"]))))
            if key in str(pair_strings[ix]).split(";"):matched[(phase,category)]+=1
            else:unknown[(phase,category)]+=1
    for rr in rec:
        phase=rr["phase"]
        rr["ros_contact_events"]={c:v for (p0,c),v in contact_counts.items() if p0==phase}
        rr["ros_contact_exact_ecm_matches"]={c:v for (p0,c),v in matched.items() if p0==phase}
        rr["ros_contact_exact_stamp_unmatched"]={c:v for (p0,c),v in unknown.items() if p0==phase}
    return rec
def transfers(p,e,full):
    m=e["moving"];j=js(p/"product_receipts/transfers/transfer_journal.json");need(j["locked"] is False,"JOURNAL_LOCK")
    out=[]
    for x in m["transfers"]:
        a=x["ack"];op=a["operation"];verify_transfer(a,IDS,3 if op=="LOAD" else 0)
        need(x["elapsed_wall_s"]<=20 and a["table_count"]==0,"TRANSFER_DEADLINE")
        entry=j["entries"][a["transfer_id"]];need(entry["result"]==a and entry["request"]==x["request"],"JOURNAL_MISMATCH")
        h=a["receipt_sha256"];f=p/"product_receipts/transfers"/(h+".json");need(sha(f)==h,"RECEIPT_SHA")
        receipt=js(f);v=receipt["evidence"];need(receipt["result"]=={k:v for k,v in a.items() if k!="receipt_sha256"},"RECEIPT_RESULT")
        require_session(v,e["source_sha"],a["stack_id"].split(":")[0])
        need(v["event_sim_ns"]==a["event_sim_ns"] if "event_sim_ns" in v else v["observation"]["event_sim_ns"]==a["event_sim_ns"],"TRANSFER_TIME")
        log=p/"product_receipts"/v["service_receipt_dir"]/"gazebo_service_calls.jsonl"
        need(sha(log)==v["service_calls_sha256"],"SERVICE_HASH")
        service=service_review(log,op)
        wait=next((w for w in m.get("transfer_waits",[]) if w["operation"]==op),None)
        if full or wait is not None:
            need(wait is not None and wait["continuous_wait_s"]>=(10 if op=="LOAD" else 5) and wait["goal_uuid"]==v["navigation"]["goal_uuid"],"WAIT")
        if op=="UNLOAD":need(v["observation"]["method"]=="ACTUAL_REMOVE_RECEIPT" and v["observation"]["removed_entity_ids"]==IDS,"REMOVE")
        else:
            rgb(p,m["loaded_rgb"],"loaded");check_rgb_order(m["loaded_rgb"]["stamp_ns"],a["event_sim_ns"])
        out.append(dict(operation=op,elapsed_s=x["elapsed_wall_s"],wait_s=wait["continuous_wait_s"] if wait is not None else None,sim_ns=a["event_sim_ns"],ids=IDS,receipt_sha256=h,method=v["observation"].get("method","REMOVE_STATIC_FIXTURE_CREATE_DYNAMIC"),service=service))
    need([x["operation"] for x in out]==(["LOAD","UNLOAD"] if full else ["LOAD"]),"TRANSFER_SEQUENCE")
    return out
def shutdown(p,e):
    d=e["lifecycle_shutdown_detail"];need(len(d)==3 and set(e["lifecycle_shutdown"].values())=={"ACK"},"ACK_MISSING")
    for name,x in d.items():
        need(e["manager_startup"][name]["success"] is True and x["before"]["success"] is True and x["command"]==4 and x["response"]["success"] is True and x["after"]["success"] is False,"ACK_DETAIL")
    need(e["quiescence"]["paused"] and e["quiescence"]["clock_quiescent"] and e["cleanup"]=={"exit":0,"forced":False},"CLEANUP")
    log=(p/"launch.log").read_text();need("SIGKILL" not in log and "exit code -9" not in log,"FORCED_KILL")
    clean=re.sub(r"\x1b\[[0-9;]*m","",log)
    nav=[l for l in clean.splitlines() if "[lifecycle_manager_navigation]:" in l]
    transition={k:sum(k in l for l in nav) for k in ("Deactivating ","Cleaning up ","Shutting down ")}
    need(transition["Deactivating "]==10 and transition["Cleaning up "]==10 and transition["Shutting down "]>=10,"NODE_TRANSITIONS")
    return dict(manager_ack=3,detail=d,transitions=transition,child_sigint_exit_count=log.count("exit code -2"),parent_exit=0)
def plots(out,session,aid):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    label_text=f"Run {session['run_id']} | {session['source_sha'][:12]}"
    d=pd.read_csv(out/f"{aid}_world_path.csv")
    fig,ax=plt.subplots(figsize=(8,6))
    for name,g in d.groupby("phase",sort=False):
        ax.plot(g.x,g.y,label=name)
    ax.set(xlabel="world x (m)",ylabel="world y (m)",title="Observed world trajectory | "+label_text)
    ax.set_aspect("equal");ax.legend(fontsize=7);fig.tight_layout();fig.savefig(out/f"{aid}_world_path.png",dpi=140);plt.close(fig)
    fig,axs=plt.subplots(4,1,figsize=(10,9),sharex=True)
    for p in session["phases"]:
        n=p["phase"];g=pd.read_csv(out/f"{aid}_{n}_ros.csv");t=g.sim_ns/1e9
        for ax,k in zip(axs[:3],("registration_m","linear_mps","angular_radps")):ax.plot(t,g[k],label=n)
    for n,g in d.groupby("phase",sort=False):axs[3].plot(g.sim_ns/1e9,g.clearance_m,label=n)
    axs[0].axhline(.1,ls="--",label="registration gate")
    axs[3].axhline(.05,ls="--",label="clearance gate")
    for ax,unit in zip(axs,("registration (m)","linear (m/s)","angular (rad/s)","clearance (m)")):
        ax.set_ylabel(unit)
        for v in session.get("transfers",[]):ax.axvline(v["sim_ns"]/1e9,ls=":",alpha=.5)
    axs[-1].set_xlabel("simulation seconds (unobserved intervals not joined)")
    axs[0].legend(fontsize=6);fig.suptitle(label_text);fig.tight_layout();fig.savefig(out/f"{aid}_mission_metrics.png",dpi=140);plt.close(fig)
    if (out/f"{aid}_dish_timeseries.csv").exists():
        q=pd.read_csv(out/f"{aid}_dish_timeseries.csv")
        fig,axs=plt.subplots(1,2,figsize=(9,4))
        for ident,g in q.groupby("dish"):
            axs[0].hist(g.center_m*1000,bins=40,alpha=.4,label=str(ident));axs[1].hist(g.tilt_rad,bins=40,alpha=.4,label=str(ident))
        axs[0].set_xlabel("center (mm)");axs[1].set_xlabel("tilt (rad)")
        for ax in axs:ax.legend();ax.set_ylabel("20 ms sampled frequency")
        fig.suptitle(label_text+" | distribution (statistics calculated at 1ms)");fig.tight_layout();fig.savefig(out/f"{aid}_distribution.png",dpi=140);plt.close(fig)
def main():
    p=argparse.ArgumentParser();p.add_argument("--evidence-dir",type=Path,required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--repo-root",type=Path,default=Path("."));a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    report=dict(verdict="HOLD",first_error=None,provenance=[],sessions=[],training_allowed=False,owner_l3="NOT_RUN",same_session_product=False)
    try:
        with tempfile.TemporaryDirectory() as td:
            roots=[]
            for pin in PINS:
                root,m=intake(a.evidence_dir/f"github-actions-artifact-{pin[1]}.zip",Path(td)/str(pin[1]),pin);roots.append(root);report["provenance"].append(m)
            save(a.out/"evidence_manifest.json",report["provenance"])
            g,rc,floor,obs=geometry(roots[0]/"static");report["geometry_static"]=g
            report["map"]=map_check(roots[0]/"static",a.repo_root,floor,obs)
            p=roots[1]/"session";e=js(p/"evidence.json");require_session(e,PINS[1][2],PINS[1][0]);report["no_goal"]=no_goal(p,e,floor,obs)
            configs=[]
            for i in (2,3,4):
                root=roots[i];p=root/"session";e=js(p/"evidence.json");require_session(e,PINS[i][2],PINS[i][0])
                g,rc,floor,obs=geometry(p/"static",p if i==3 else None)
                config={n:sha(p/"static"/n) for n in ("world.before_contact.sdf","transfer_robot.before_contact.sdf","transfer_robot.sdf","candidate.pgm","candidate.yaml","localization.pgm","localization.yaml","live_nav2.yaml","live_bridge.yaml")}
                config["observer_binary_receipt"]= (root/"ecm_binary.sha256").read_text().split()[0];configs.append(config)
                graph(e);rec=replay(p,e,rc,floor,obs,a.out,PINS[i][1])
                result=dict(run_id=PINS[i][0],source_sha=PINS[i][2],first_error=e["first_error"],geometry=g,phases=rec,config=config)
                if i in (2,3):result["transfers"]=transfers(p,e,i==3)
                if i==4:result["shutdown"]=shutdown(p,e)
                report["sessions"].append(result);plots(a.out,result,PINS[i][1]);save(a.out/"qa.json",report)
            need(configs[0]==configs[1]==configs[2],"CONFIG_DRIFT")
            report["same_physical_config"]=True
            need(sum(x["samples"] for x in report["sessions"][1]["phases"])==186122,"MISSION_SAMPLES")
            # Receipt-only boundaries remain explicit; C input is outside A artifacts.
            report["verdict"]="HOLD"
            report["first_error"]="B_STOP_DWELL_RAW_CONTINUOUS_NOT_EXPORTED"
            report["ledger"]={"B_QA_00":"PASS","B_QA_01":"PASS_STATIC_CANDIDATE","B_QA_02":"PASS_ECM_HOLD_FULL_DDS","B_QA_03":"PASS_LOADED_OBSERVED","B_QA_04":"PASS_OBSERVED_GEOMETRY_CONTACTS","B_QA_05":"PASS_RECEIPT_SERVICE_RGB","B_QA_06":"HOLD_RAW_DWELL_AND_E_SINGLE_SESSION","B_QA_07":"PASS_POLICY_NO_TRAINING","B_QA_08":"PASS_REPLAY_HOLD_RELEASE"}
            report["limitations"]=["A receipt fields are not independent raw stop dwell samples","ROS contact exact-stamp matching is positive subset, not full DDS coverage","C input/AI outside A scope","E single-session product required"]
            pd.DataFrame([dict(run_id=s["run_id"],**{k:v for k,v in p.items() if k!="dishes" and not isinstance(v,dict)}) for s in report["sessions"] for p in s["phases"]]).to_csv(a.out/"phases.csv",index=False)
    except Exception as e:
        report.update(verdict="FAIL",first_error=f"{type(e).__name__}: {e}")
        save(a.out/"qa.json",report);print(report["first_error"]);return 1
    save(a.out/"qa.json",report);print(json.dumps({k:report[k] for k in ("verdict","first_error","same_session_product")}))
    return 0
if __name__=="__main__":raise SystemExit(main())
