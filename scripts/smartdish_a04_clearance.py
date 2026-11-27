#!/usr/bin/env python3
"""A04 conservative SDF/map audit. Candidate only; never grants motion.
All solid projections included (including above the scan plane). World/map
registration is nominal until independently measured in the actual runtime.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
from collections import deque
from xml.etree import ElementTree as ET
import numpy as np
from scipy.ndimage import distance_transform_edt, binary_erosion
from scipy.spatial.transform import Rotation
from PIL import Image
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from smartdish_product_scene import generate as scene_generate
from smartdish_product_robot import generate as robot_generate
from smartdish_robot.product_gazebo_backend import build_dish_sdf
HALF=.28
PADDING=.01
NOMINAL=(-2.60,-2.20,0.)
REGISTRATION_MARGIN=.10
TARGETS=("HOME","T03","DISH_RETURN")

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\n")
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def pose(element):
    p=element.find("pose")
    if p is None:return np.eye(4)
    require(not p.attrib,"UNSUPPORTED_POSE_ATTRIBUTES")
    vals=[float(v) for v in p.text.split()]
    require(len(vals)==6 and np.isfinite(vals).all(),"POSE_INVALID")
    t=np.eye(4);t[:3,:3]=Rotation.from_euler("xyz",vals[3:]).as_matrix();t[:3,3]=vals[:3]
    return t
def half_extent(geom):
    require(len(geom)==1,"GEOMETRY_INVALID")
    if geom.find("box") is not None:
        q=np.array([float(v) for v in geom.findtext("box/size").split()])/2
    elif geom.find("cylinder") is not None:
        r=float(geom.findtext("cylinder/radius"));q=np.array([r,r,float(geom.findtext("cylinder/length"))/2])
    elif geom.find("sphere") is not None:
        q=np.repeat(float(geom.findtext("sphere/radius")),3)
    else:raise RuntimeError("UNSUPPORTED_COLLISION_GEOMETRY:"+geom[0].tag)
    require(q.shape==(3,) and np.isfinite(q).all() and (q>0).all(),"GEOMETRY_SIZE")
    return q
def collisions(model):
    require(not model.findall("model") and not model.findall("include"),"NESTED_MODEL_UNSUPPORTED")
    result=[]
    for link in model.findall("link"):
        for col in link.findall("collision"):
            t=pose(model)@pose(link)@pose(col);q=half_extent(col.find("geometry"))
            center=t[:3,3];extent=np.abs(t[:3,:3])@q
            result.append(dict(model=model.get("name"),link=link.get("name"),collision=col.get("name"),
                shape=col.find("geometry")[0].tag,lo=(center-extent).tolist(),hi=(center+extent).tolist()))
    return result
def mass_properties(model):
    parts=[]
    for link in model.findall("link"):
        i=link.find("inertial")
        if i is None:continue
        t=pose(model)@pose(link)@pose(i)
        mass=float(i.findtext("mass"));v=[float(i.findtext("inertia/"+k)) for k in ("ixx","iyy","izz","ixy","ixz","iyz")]
        I=np.array([[v[0],v[3],v[4]],[v[3],v[1],v[5]],[v[4],v[5],v[2]]])
        require(mass>0 and np.linalg.eigvalsh(I).min()>0,"INERTIA_INVALID")
        parts.append((mass,t[:3,3],t[:3,:3]@I@t[:3,:3].T))
    m=sum(p[0] for p in parts);c=sum(p[0]*p[1] for p in parts)/m
    I=sum(i+mass*(np.dot(p-c,p-c)*np.eye(3)-np.outer(p-c,p-c)) for mass,p,i in parts)
    return dict(mass_kg=m,com_model_m=c.tolist(),inertia_about_com_kg_m2=I.tolist())
def geometry(robot,world):
    model=ET.parse(robot).getroot().find("model")
    w=ET.parse(world).getroot().find("world")
    require(w.get("name")=="restaurant" and not w.findall("include"),"WORLD_UNSUPPORTED")
    models=w.findall("model")
    require(all(m.findtext("static")=="true" for m in models),"WORLD_DYNAMIC_UNMODELED")
    rc=collisions(model);wc=[c for m in models for c in collisions(m)]
    fixture=w.find("model[@name='s6_stacked_dishes']")
    require(fixture is not None,"INITIAL_STACK_MISSING")
    plates=[ET.fromstring(build_dish_sdf(fixture,i,(0,0,.445+.037*(i+.5)),0)).find("model") for i in range(3)]
    pc=[c for m in plates for c in collisions(m)]
    # Use the rotationally invariant disk radius, not the cylinder's bounding-box corners.
    loaded_radius=.245+.015
    lateral=max(abs(v) for c in rc for k in ("lo","hi") for v in c[k][:2])
    require(lateral<=HALF and loaded_radius<=HALF,"FOOTPRINT_UNDERSIZED")
    lidar=model.find(".//sensor[@type='gpu_lidar']")
    link=next(l for l in model.findall("link") if lidar in list(l))
    lidar_z=float((pose(model)@pose(link)@pose(lidar))[2,3])
    floor=[c for c in wc if c["model"]=="floor"]
    require(len(floor)==1,"FLOOR_COUNT")
    obstacles=[c for c in wc if c["model"]!="floor"]
    # Entire planar projection, not scan-height-only. Static obstacles above floor.
    return dict(scope="SDF_COLLISION_AABB_CONSERVATIVE_NOT_CONTACT_EVIDENCE",
        robot_sha256=sha(robot),world_sha256=sha(world),robot_collisions=rc,dish_collisions=pc,
        robot_mass=mass_properties(model),dish_mass=[mass_properties(m) for m in plates],
        max_robot_xy_m=lateral,loaded_dish_radius_with_centering_m=loaded_radius,
        top_model_z_m=max(c["hi"][2] for c in rc+pc),lidar_model_z_m=lidar_z,
        lidar_blind_static_collisions=[c for c in obstacles if not c["lo"][2]<=lidar_z+.02<=c["hi"][2]],
        footprint_half_m=HALF,padding_m=PADDING,floor=floor[0],obstacles=obstacles,
        motion_authorized=False)
def read_map(path):
    p=Path(path);cfg=yaml.safe_load(p.read_text())
    require(cfg["mode"]=="trinary" and cfg["negate"]==0 and cfg["origin"][2]==0,"MAP_MODE")
    a=np.asarray(Image.open(p.parent/cfg["image"]).convert("L"))[::-1].copy()
    prob=(255-a.astype(float))/255
    classes=np.where(prob>cfg["occupied_thresh"],100,np.where(prob<cfg["free_thresh"],0,-1))
    return cfg,classes
def xy_grid(cfg,shape):
    res=cfg["resolution"];ox,oy=cfg["origin"][:2]
    return np.meshgrid(ox+(np.arange(shape[1])+.5)*res,oy+(np.arange(shape[0])+.5)*res)
def nominal_world(x,y):
    return x+NOMINAL[0],y+NOMINAL[1]
def candidate(cfg,classes,g):
    x,y=xy_grid(cfg,classes.shape);wx,wy=nominal_world(x,y)
    # Entire cell must lie inside the floor and outside all projected collision
    # bounds expanded by registration margin. Keep original occupied cells.
    cell=cfg["resolution"]/2;pad=cell+REGISTRATION_MARGIN
    f=g["floor"];lo,hi=f["lo"],f["hi"]
    inside=(wx>=lo[0]+pad)&(wx<=hi[0]-pad)&(wy>=lo[1]+pad)&(wy<=hi[1]-pad)
    blocked=np.zeros(classes.shape,dtype=bool)
    for c in g["obstacles"]:
        lo,hi=c["lo"],c["hi"]
        blocked|=(wx>=lo[0]-pad)&(wx<=hi[0]+pad)&(wy>=lo[1]-pad)&(wy<=hi[1]+pad)
    known_clear=inside&~blocked
    out=np.full(classes.shape,-1,dtype=np.int16)
    out[known_clear]=0
    out[inside&blocked]=100
    out[classes==100]=100
    return out
def count(a):return {k:int(np.count_nonzero(a==v)) for k,v in (("free",0),("unknown",-1),("occupied",100))}
def grid_screen(cfg,a,targets):
    res=cfg["resolution"];ox,oy=cfg["origin"][:2]
    radius=math.sqrt(2)*(HALF+PADDING)+res/math.sqrt(2)
    # Padding by a blocked border makes out-of-map nonfree.
    d=distance_transform_edt(np.pad(a==0,1,constant_values=False))[1:-1,1:-1]*res
    valid=d>radius
    def cell(p):return (math.floor((p["y"]-oy)/res),math.floor((p["x"]-ox)/res))
    legs=[]
    for u,v in zip(TARGETS,(*TARGETS[1:],TARGETS[0])):
        start,end=cell(targets[u]),cell(targets[v]);q=deque([start]);seen={start} if valid[start] else set()
        while q and start in seen and end not in seen:
            i,j=q.popleft()
            for n in ((i-1,j),(i+1,j),(i,j-1),(i,j+1)):
                if 0<=n[0]<a.shape[0] and 0<=n[1]<a.shape[1] and valid[n] and n not in seen:
                    seen.add(n);q.append(n)
        legs.append(dict(start=u,end=v,connected=end in seen,start_clearance_cell_center_m=float(d[start]),end_clearance_cell_center_m=float(d[end])))
    return dict(radius_m=radius,legs=legs,classes=count(a),connected=all(v["connected"] for v in legs))
def prepare(out,robot_source,bridge_source,world_source,map_path,pose_path,run_id):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    scene=scene_generate(world_source,out/"world.sdf","stacked",run_id)
    robot_generate(robot_source,bridge_source,out/"overlay")
    g=geometry(out/"overlay/robot.sdf",out/"world.sdf");save(out/"geometry.json",g)
    cfg,original=read_map(map_path);poses=yaml.safe_load(Path(pose_path).read_text())
    require(poses["frame"]=="map","TARGET_FRAME")
    targets=poses["poses"];new=candidate(cfg,original,g)
    original_screen=grid_screen(cfg,original,targets);candidate_screen=grid_screen(cfg,new,targets)
    Image.fromarray(np.where(new==100,0,np.where(new==0,254,205)).astype(np.uint8)[::-1]).save(out/"candidate.pgm")
    newcfg=dict(cfg,image="candidate.pgm");(out/"candidate.yaml").write_text(yaml.safe_dump(newcfg,sort_keys=False))
    x,y=xy_grid(cfg,original.shape);endpoint={}
    for name,p in targets.items():
        ds=np.hypot(x-p["x"],y-p["y"]);r=original_screen["radius_m"]
        endpoint[name]={"original_unknown_in_disk":int(np.sum((ds<=r)&(original==-1))),
            "candidate_unknown_in_disk":int(np.sum((ds<=r)&(new==-1))),
            "nominal_world_xy":list(nominal_world(p["x"],p["y"]))}
    data=dict(scope="NOMINAL_SDF_CANDIDATE_NOT_ADOPTED_NO_MOTION",source_map_sha256=sha(Path(map_path).parent/cfg["image"]),
        source_map_yaml_sha256=sha(map_path),source_world_sha256=sha(world_source),
        candidate_sha256=sha(out/"candidate.pgm"),candidate_yaml_sha256=sha(out/"candidate.yaml"),
        nominal_map_to_world=NOMINAL,registration_margin_m=REGISTRATION_MARGIN,
        original=original_screen,candidate=candidate_screen,targets=endpoint,
        changed_unknown_to_free=int(np.sum((original==-1)&(new==0))),
        original_occupied_preserved=bool(np.all(new[original==100]==100)),motion_authorized=False)
    save(out/"map_audit.json",data);return scene,g,data

def main():
    p=argparse.ArgumentParser()
    for k in ("out","robot-source","bridge-source","world-source","map","poses"):p.add_argument("--"+k,type=Path,required=True)
    p.add_argument("--run-id",required=True);a=p.parse_args()
    _,_,d=prepare(a.out,a.robot_source,a.bridge_source,a.world_source,a.map,a.poses,a.run_id)
    print(json.dumps(d,sort_keys=True))
if __name__=="__main__":main()
