#!/usr/bin/env python3
"""A-PROD-02 opt-in Waffle Pi rigid tray overlay; NOT a motion release."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import yaml
from smartdish_tray_camera import add_camera, verify_camera, TOPIC, INFO_TOPIC

TRAY_SIZE = (.54, .54, .03)
TRAY_Z = .43
CAMERA_HEIGHT = .65
TRAY_NAME = "smartdish_product_tray"
CAMERA_POSE = "0 0 0.65 0 1.57079632679 0"
JOINT_NAME = "smartdish_tray_fixed"

def el(parent, tag, value=None, **attrs):
    item = ET.SubElement(parent, tag, attrs)
    if value is not None:
        item.text = str(value)
    return item

def box(link, name, size, xyz, color):
    for tag in ("collision", "visual"):
        obj = el(link, tag, name=name + "_" + tag)
        el(obj, "pose", " ".join(map(str, (*xyz, 0, 0, 0))))
        el(el(el(obj, "geometry"), "box"), "size", " ".join(map(str, size)))
        if tag == "visual":
            material = el(obj, "material")
            el(material, "ambient", color)
            el(material, "diffuse", color)

def build_robot(original):
    root = ET.fromstring(original)
    model = root.find("./model[@name='turtlebot3_waffle_pi']")
    if model is None or model.find("./link[@name='base_link']") is None:
        raise ValueError("A_PRODUCT_EXPECTED_OFFICIAL_WAFFLE")
    if (model.find(f"./link[@name='{TRAY_NAME}']") is not None
        or model.find(f"./joint[@name='{JOINT_NAME}']") is not None
        or any(s.findtext("topic") == TOPIC for s in model.findall(".//sensor"))):
        raise ValueError("A_PRODUCT_DUPLICATE_TRAY")
    protected = [ET.tostring(x) for x in model]
    tray = el(model, "link", name=TRAY_NAME)
    el(tray, "pose", f"0 0 {TRAY_Z} 0 0 0")
    # Rigid tray, side mast and crossbar. Nominal simulation mass, not HW data.
    parts = [
        ("platform", TRAY_SIZE, (0., 0., 0.), .35),
        ("mast", (.015, .025, .70), (-.26, 0., .35), .08),
        ("crossbar", (.26, .025, .025), (-.13, 0., .70), .04),
    ]
    total = sum(p[3] for p in parts)
    center = [sum(p[2][i]*p[3] for p in parts)/total for i in range(3)]
    inertial = el(tray, "inertial")
    el(inertial, "pose", " ".join(map(str, (*center, 0, 0, 0))))
    el(inertial, "mass", total)
    mat = el(inertial, "inertia")
    # Box inertia and parallel-axis theorem about aggregate COM.
    terms = dict.fromkeys(("ixx","iyy","izz","ixy","ixz","iyz"), 0.)
    for name, (w,d,h), xyz, mass in parts:
        x,y,z = [xyz[i]-center[i] for i in range(3)]
        terms["ixx"] += mass*((d*d+h*h)/12+y*y+z*z)
        terms["iyy"] += mass*((w*w+h*h)/12+x*x+z*z)
        terms["izz"] += mass*((w*w+d*d)/12+x*x+y*y)
        terms["ixy"] -= mass*x*y
        terms["ixz"] -= mass*x*z
        terms["iyz"] -= mass*y*z
        box(tray, name, (w,d,h), xyz, "0.24 0.38 0.52 1")
    for key, value in terms.items():
        el(mat, key, f"{value:.10f}")
    sensor = add_camera(tray, CAMERA_POSE)
    verify_camera(sensor)
    j = el(model, "joint", name=JOINT_NAME, type="fixed")
    el(j, "parent", "base_link")
    el(j, "child", TRAY_NAME)
    if [ET.tostring(x) for x in list(model)[:-2]] != protected:
        raise ValueError("A_PRODUCT_BASE_CHANGED")
    return '<?xml version="1.0"?>\n'+ET.tostring(root, encoding="unicode")+"\n"

def build_bridge(base):
    if not isinstance(base, list) or not all(isinstance(x, dict) for x in base):
        raise ValueError("A_PRODUCT_BRIDGE_LIST_REQUIRED")
    topics = [x.get("ros_topic_name") for x in base]
    if topics.count("/clock") != 1 or topics.count("/cmd_vel") != 1:
        raise ValueError("A_PRODUCT_BASE_BRIDGE_CONTRACT")
    if any(x in topics for x in (TOPIC, INFO_TOPIC)):
        raise ValueError("A_PRODUCT_DUPLICATE_TRAY_BRIDGE")
    out = deepcopy(base)
    for topic, rt, gt in [(TOPIC,"sensor_msgs/msg/Image","gz.msgs.Image"),
                          (INFO_TOPIC,"sensor_msgs/msg/CameraInfo","gz.msgs.CameraInfo")]:
        out.append(dict(ros_topic_name=topic, gz_topic_name=topic,
                        ros_type_name=rt, gz_type_name=gt, direction="GZ_TO_ROS"))
    return out

def generate(robot_source, bridge_source, out):
    robot_source, bridge_source, out = map(Path, (robot_source, bridge_source, out))
    if out.exists():
        raise ValueError("A_PRODUCT_NO_OVERWRITE")
    robot = robot_source.read_bytes()
    bridge = bridge_source.read_bytes()
    rendered = build_robot(robot.decode("utf-8")).encode("utf-8")
    cfg = yaml.safe_dump(build_bridge(yaml.safe_load(bridge)), sort_keys=False).encode()
    out.mkdir(parents=True, exist_ok=False)
    (out/"robot.sdf").write_bytes(rendered)
    (out/"bridge.yaml").write_bytes(cfg)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    record = {"schema_version":2,"profile":"OWNER_PRODUCT_RECOVERY",
              "source_robot_sha256":sha(robot),"source_bridge_sha256":sha(bridge),
              "robot_sha256":sha(rendered),"bridge_sha256":sha(cfg),
              "tray_size_m":list(TRAY_SIZE),"tray_z_model_m":TRAY_Z,
              "camera_pose_tray":CAMERA_POSE,"camera_hfov_rad":1.3962634,
              "plate_diameter_m":.49,"tray_total_mass_kg":.47,
              "navigation_authorized":False,"runtime_verified":False,
              "footprint_review_required":True,
              "scope":"FIXED_TRAY_OVERLAY_CANDIDATE_NO_GOAL"}
    (out/"manifest.json").write_text(json.dumps(record, sort_keys=True, indent=2)+"\n")
    return record

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--robot-source", required=True, type=Path)
    p.add_argument("--bridge-source", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    print(json.dumps(generate(a.robot_source, a.bridge_source, a.out), sort_keys=True))

if __name__ == "__main__":
    main()
