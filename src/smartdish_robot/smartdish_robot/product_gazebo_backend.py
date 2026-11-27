"""Actual Gazebo UserCommands primitives for A's opt-in product transfer.

No ROS control publisher or navigation authorization exists here. Only the A
controller, after real terminal UUID + fresh stop proof, may use these
mutation primitives. CI may exercise them in an isolated no-goal world.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree as ET
from .product_contract import ContractError, require

DISH_NAMES=tuple("smartdish_product_dish_%02d"%i for i in range(3))
FIXTURE="s6_stacked_dishes"
PLATE_RADIUS=.245
PLATE_HEIGHT=.037
PLATE_MASS=.22
TRAY_TOP=.445

def el(parent,tag,value=None,**attrs):
    item=ET.SubElement(parent,tag,attrs)
    if value is not None:item.text=str(value)
    return item

def add_pose_publisher(model,topic):
    require(not any(p.findtext("topic")==topic for p in model.findall("plugin")),
            "POSE_PUBLISHER_DUPLICATE")
    p=el(model,"plugin",filename="gz-sim-pose-publisher-system",
         name="gz::sim::systems::PosePublisher")
    for k,v in {"publish_model_pose":"true","publish_nested_model_pose":"true",
                "publish_link_pose":"false","use_pose_vector_msg":"true",
                "update_frequency":"20","topic":topic}.items():el(p,k,v)
    return p

def build_dish_sdf(fixture,index,xyz,yaw):
    """Reuse the exact S6 visual shapes, one free dynamic cylinder per plate.
    Collision is a conservative envelope of the two source visual cylinders.
    """
    require(type(index) is int and 0<=index<3,"DISH_INDEX")
    require(len(xyz)==3 and all(math.isfinite(v) for v in (*xyz,yaw)),"POSE_INVALID")
    require(fixture.attrib.get("name")==FIXTURE,"FIXTURE_IDENTITY")
    source=fixture.find("link")
    visuals=[]
    for kind in ("plate","blue_rim"):
        v=source.find(f"./visual[@name='{kind}_{index}']")
        require(v is not None,"S6_VISUAL_MISSING")
        visuals.append(ET.fromstring(ET.tostring(v)))
    # Absolute S6 visual z is re-centered about the measured visual envelope.
    centers=[]
    for v in visuals:
        p=[float(x) for x in v.findtext("pose").split()]
        h=float(v.findtext("geometry/cylinder/length"))
        centers.append((p[2]-h/2,p[2]+h/2))
    lo=min(x[0] for x in centers);hi=max(x[1] for x in centers)
    require(abs(hi-lo-PLATE_HEIGHT)<1e-6,"S6_GEOMETRY_DRIFT")
    center=(lo+hi)/2
    root=ET.Element("sdf",version="1.9")
    model=el(root,"model",name=DISH_NAMES[index])
    el(model,"static","false")
    el(model,"pose"," ".join(map(str,(*xyz,0,0,yaw))))
    add_pose_publisher(model,"/smartdish/product/gz_pose/"+DISH_NAMES[index])
    link=el(model,"link",name="body")
    el(link,"gravity","true")
    inertial=el(link,"inertial")
    el(inertial,"mass",PLATE_MASS)
    it=el(inertial,"inertia")
    ixy=PLATE_MASS*(3*PLATE_RADIUS**2+PLATE_HEIGHT**2)/12
    for k,v in {"ixx":ixy,"iyy":ixy,"izz":PLATE_MASS*PLATE_RADIUS**2/2,
                "ixy":0,"ixz":0,"iyz":0}.items():el(it,k,v)
    collision=el(link,"collision",name="envelope")
    cylinder=el(el(collision,"geometry"),"cylinder")
    el(cylinder,"radius",PLATE_RADIUS);el(cylinder,"length",PLATE_HEIGHT)
    ode=el(el(el(collision,"surface"),"friction"),"ode")
    el(ode,"mu",.65);el(ode,"mu2",.65)
    for v in visuals:
        p=[float(x) for x in v.findtext("pose").split()]
        p[2]-=center
        v.find("pose").text=" ".join(map(str,p))
        link.append(v)
    return '<?xml version="1.0"?>\n'+ET.tostring(root,encoding="unicode")+"\n"

def parse_scene_models(text):
    out={}
    for m in re.finditer(r"(?m)^model[ \t]*\{[ \t]*$",text):
        start=m.end();depth=1;end=start
        for c in text[start:]:
            end+=1
            if c=="{":depth+=1
            elif c=="}":depth-=1
            if depth==0:break
        require(depth==0,"SCENE_PROTOBUF_TRUNCATED")
        block=text[start:end-1]
        name=re.search(r'(?m)^  name: "([^"]+)"',block)
        ident=re.search(r"(?m)^  id: (\d+)",block)
        require(name and ident and int(ident.group(1))>0,"SCENE_ID_MISSING")
        key=name.group(1)
        require(key not in out,"SCENE_DUPLICATE_MODEL")
        out[key]=int(ident.group(1))
    require(len(set(out.values()))==len(out),"SCENE_DUPLICATE_ID")
    return out

class GazeboEntityServices:
    def __init__(self,evidence_dir,timeout_s=5.):
        self.root=Path(evidence_dir)
        self.root.mkdir(parents=True,exist_ok=True)
        require(0<timeout_s<=5.,"SERVICE_TIMEOUT_INVALID")
        self.timeout=timeout_s
        self.calls=[]

    def _call(self,suffix,reqtype,reptype,request):
        command=["gz","service","-s","/world/restaurant/"+suffix,
                 "--reqtype",reqtype,"--reptype",reptype,
                 "--timeout",str(int(self.timeout*1000)),"--req",request]
        try:
            result=subprocess.run(command,capture_output=True,text=True,timeout=self.timeout+2)
            row={"service":suffix,"request":request,"exit":result.returncode,
                 "stdout":result.stdout,"stderr":result.stderr}
        except subprocess.TimeoutExpired:
            row={"service":suffix,"request":request,"exit":None,"error":"TIMEOUT"}
        self.calls.append(row)
        with (self.root/"gazebo_service_calls.jsonl").open("a",encoding="utf-8") as f:
            f.write(json.dumps(row,sort_keys=True)+"\n")
        require(row["exit"]==0,"GAZEBO_SERVICE_FAILED_"+suffix)
        return row["stdout"]

    def scene(self):
        models=parse_scene_models(self._call("scene/info","gz.msgs.Empty","gz.msgs.Scene",""))
        require("table_3" in models and "floor" in models,"RESTAURANT_SCENE_NOT_OBSERVED")
        return models

    def create(self,path,name):
        path=Path(path).resolve()
        require(path.is_file() and path.is_relative_to(self.root.resolve()),"DISH_SDF_PATH")
        require(name in DISH_NAMES,"DISH_NAME_INVALID")
        request="sdf_filename: "+json.dumps(str(path))+", name: "+json.dumps(name)+", allow_renaming: false"
        out=self._call("create","gz.msgs.EntityFactory","gz.msgs.Boolean",request)
        require(re.search(r"(?m)^data:\s*true\s*$",out),"CREATE_REJECTED")

    def remove(self,ident):
        require(type(ident) is int and ident>0,"ENTITY_ID_INVALID")
        out=self._call("remove","gz.msgs.Entity","gz.msgs.Boolean",
                       f"id: {ident}, type: MODEL")
        require(re.search(r"(?m)^data:\s*true\s*$",out),"REMOVE_REJECTED")

def relative_xyz(robot_xyz,robot_q,world_xyz):
    """Inverse unit quaternion rotation: actual world -> robot model."""
    require(len(robot_xyz)==len(world_xyz)==3 and len(robot_q)==4,"POSE_SHAPE")
    require(all(math.isfinite(v) for v in (*robot_xyz,*world_xyz,*robot_q)),"POSE_NONFINITE")
    x,y,z,w=robot_q
    n=x*x+y*y+z*z+w*w
    require(abs(n-1)<.03,"POSE_QUATERNION")
    norm=math.sqrt(n);x,y,z,w=-x/norm,-y/norm,-z/norm,w/norm
    v=[a-b for a,b in zip(world_xyz,robot_xyz)]
    qv=(x,y,z)
    cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    t=[2*k for k in cross(qv,v)]
    c=cross(qv,t)
    return tuple(v[i]+w*t[i]+c[i] for i in range(3))
