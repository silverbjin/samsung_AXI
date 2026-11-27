"""Product-specific conservative footprint and static map screening.
Never edit the released Nav2 config, map or CM. Static connectivity is not a live path.
"""
from collections import deque
import argparse
import hashlib
import json
import math
from pathlib import Path
import yaml
from PIL import Image
from prepare_nav2_params import build

HALF = 0.28
PADDING = 0.01
FOOTPRINT = [[-HALF,-HALF],[HALF,-HALF],[HALF,HALF],[-HALF,HALF]]
TARGETS = ("HOME","T03","DISH_RETURN")

def screen_map(map_path, pose_path):
    map_path=Path(map_path)
    cfg=yaml.safe_load(map_path.read_text())
    if cfg.get("mode")!="trinary" or cfg.get("negate")!=0 or cfg["origin"][2]!=0:
        raise RuntimeError("MAP_CONTRACT_DRIFT")
    res=float(cfg["resolution"])
    if not math.isfinite(res) or not 0<res<=0.1:
        raise RuntimeError("MAP_RESOLUTION_INVALID")
    origin=cfg["origin"][:2]
    image_path=map_path.parent/cfg["image"]
    with Image.open(image_path) as image:
        w,h=image.size
        pixels=list(image.convert("L").getdata())
    # A full yaw-independent square bounding disk plus half-cell diagonal.
    radius=math.sqrt(2)*(HALF+PADDING)+math.sqrt(2)*res/2
    extent=math.ceil(radius/res)
    offsets=[(dx,dy) for dx in range(-extent,extent+1)
             for dy in range(-extent,extent+1) if math.hypot(dx*res,dy*res)<=radius]
    free=lambda x,y: (0<=x<w and 0<=y<h and (255-pixels[y*w+x])/255<float(cfg["free_thresh"]))
    valid={(x,y) for y in range(extent,h-extent) for x in range(extent,w-extent)
           if all(free(x+dx,y+dy) for dx,dy in offsets)}
    poses=yaml.safe_load(Path(pose_path).read_text())
    if poses["frame"]!="map" or set(poses["poses"])!=set(TARGETS):
        raise RuntimeError("MAP_POSE_CONTRACT_DRIFT")
    def cell(name):
        p=poses["poses"][name]
        return math.floor((p["x"]-origin[0])/res),h-1-math.floor((p["y"]-origin[1])/res)
    results=[]
    for start,end in zip(TARGETS,(*TARGETS[1:],TARGETS[0])):
        a,b=cell(start),cell(end)
        queue=deque([a]);dist={a:0} if a in valid else {}
        while queue and a in dist and b not in dist:
            x,y=queue.popleft()
            for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if n in valid and n not in dist:
                    dist[n]=dist[(x,y)]+1
                    queue.append(n)
        results.append({"from":start,"to":end,"start_free":a in valid,"end_free":b in valid,
                        "path_exists":b in dist,"grid_path_m":None if b not in dist else dist[b]*res})
    return {"scope":"STATIC_CONSERVATIVE_GRID_CONNECTIVITY_NOT_NAV2",
            "map_sha256":hashlib.sha256(image_path.read_bytes()).hexdigest(),"width":w,"height":h,
            "resolution_m":res,"screening_radius_m":radius,"legs":results,
            "motion_authorized":False,"all_connected":all(x["path_exists"] for x in results)}

def apply_product_footprint(params):
    for name in ("local_costmap","global_costmap"):
        node=params[name][name]["ros__parameters"]
        node["footprint"]=json.dumps(FOOTPRINT,separators=(",",":"))
        node["footprint_padding"]=PADDING
        node.pop("robot_radius",None)
    cm=params["collision_monitor"]["ros__parameters"]
    if cm["cmd_vel_in_topic"]!="cmd_vel_smoothed" or cm["cmd_vel_out_topic"]!="cmd_vel":
        raise RuntimeError("CM_CHAIN_DRIFT")
    if "FootprintApproach" not in cm["polygons"] or "S4ForwardStop" not in cm["polygons"]:
        raise RuntimeError("CM_PROTECTION_MISSING")
    # Preserve original stop extent and point count, expand for the wider tray.
    stop=cm["S4ForwardStop"]
    if stop.get("action_type")!="stop" or stop.get("enabled") is not True:
        raise RuntimeError("CM_STOP_PROTECTION_DRIFT")
    stop["points"]="[[0.10,0.30],[0.58,0.30],[0.58,-0.30],[0.10,-0.30]]"
    return params

def prepare(source,output,map_path,pose_path,receipt):
    source,output,receipt=map(Path,(source,output,receipt))
    if output.exists() or receipt.exists() or output.resolve()==source.resolve():
        raise RuntimeError("PRODUCT_OVERLAY_NO_OVERWRITE")
    original=source.read_bytes()
    screen=screen_map(map_path,pose_path)
    if not screen["all_connected"]:
        raise RuntimeError("PRODUCT_STATIC_CLEARANCE_FAILED")
    base=output.with_suffix(".s7.yaml")
    if base.exists():
        raise RuntimeError("PRODUCT_OVERLAY_NO_OVERWRITE")
    build(source,base,auto_initial_pose=True,s6_bt_ack_ms=200)
    params=apply_product_footprint(yaml.safe_load(base.read_text()))
    output.write_text(yaml.safe_dump(params,sort_keys=False))
    if source.read_bytes()!=original:
        raise RuntimeError("PRODUCT_BASE_CHANGED")
    screen.update(footprint=FOOTPRINT,footprint_padding_m=PADDING,
                  source_params_sha256=hashlib.sha256(original).hexdigest(),
                  generated_params_sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    receipt.write_text(json.dumps(screen,indent=2)+"\n")
    return screen

def main():
    ap=argparse.ArgumentParser()
    for key in ("source","output","map","poses","receipt"):
        ap.add_argument("--"+key,type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(prepare(a.source,a.output,a.map,a.poses,a.receipt),sort_keys=True))
if __name__=="__main__":main()
