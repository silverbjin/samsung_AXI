#!/usr/bin/env python3
"""A-12 deterministic isolated Gazebo Harmonic tray gravity/stack tests.

Only generates SDF+metadata; NEVER infers physical labels from scenario names.
Each trial's world process is independent: no previous dynamic objects persist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from xml.etree import ElementTree as ET

from smartdish_tray_camera import standalone_camera_model, verify_camera

WORLD = "smartdish_tray"
SCENARIOS = ("ST-01", "ST-02", "UN-01", "UN-02")
TRAY_WIDTH, TRAY_DEPTH, TRAY_TOP = .70, .56, .57
SIM_SECS = 10
# Values below are reproducible SIMULATION EXPERIMENT constants, not measured
# physical mass, friction or real tableware material properties.
MU = 0.65
MASS_KG = 0.22


def el(parent, tag, text=None, **attrs):
    node = ET.SubElement(parent, tag, attrs)
    if text is not None:
        node.text = str(text)
    return node


def inertial(link, mass, radius, height):
    i = el(link, "inertial")
    el(i, "mass", f"{mass:.6f}")
    mat = el(i, "inertia")
    # Uniform solid cylinder about its center.
    ixy = mass * (3 * radius**2 + height**2) / 12
    izz = mass * radius**2 / 2
    for key, value in {"ixx": ixy, "iyy": ixy, "izz": izz,
                       "ixy": 0., "ixz": 0., "iyz": 0.}.items():
        el(mat, key, f"{value:.9f}")


def box_model(name, size, pose, color, static=True):
    m = ET.Element("model", {"name": name})
    el(m, "static", "true" if static else "false")
    el(m, "pose", " ".join(map(str, pose)))
    link = el(m, "link", name="body")
    for tag in ("collision", "visual"):
        item = el(link, tag, name=tag)
        box = el(el(item, "geometry"), "box")
        el(box, "size", " ".join(map(str, size)))
        if tag == "visual":
            material = el(item, "material")
            el(material, "ambient", color)
            el(material, "diffuse", color)
    return m


def plate_model(name, x, y, z, roll, pitch, radius, thickness, color):
    m = ET.Element("model", {"name": name})
    el(m, "static", "false")
    el(m, "pose", f"{x:.5f} {y:.5f} {z:.5f} {roll:.5f} {pitch:.5f} 0")
    # Official Gazebo PosePublisher emits NAMED Pose_V with world-relative
    # model transforms. SceneBroadcaster's dynamic_pose/info may omit TF
    # frame names when bridged; never infer entity identity from array index.
    pub=el(m,"plugin",filename="gz-sim-pose-publisher-system",
           name="gz::sim::systems::PosePublisher")
    el(pub,"publish_model_pose","true")
    el(pub,"publish_nested_model_pose","true")
    el(pub,"publish_link_pose","false")
    el(pub,"use_pose_vector_msg","true")
    el(pub,"update_frequency","20")
    el(pub,"topic","/smartdish/tray/gz_pose/"+name)
    link = el(m, "link", name="body")
    el(link, "gravity", "true")
    inertial(link, MASS_KG, radius, thickness)
    for tag in ("collision", "visual"):
        item = el(link, tag, name=tag)
        cyl = el(el(item, "geometry"), "cylinder")
        el(cyl, "radius", f"{radius:.4f}")
        el(cyl, "length", f"{thickness:.4f}")
        if tag == "collision":
            contact = el(el(item, "surface"), "friction")
            ode = el(contact, "ode")
            el(ode, "mu", str(MU))
            el(ode, "mu2", str(MU))
        else:
            material = el(item, "material")
            el(material, "ambient", color)
            el(material, "diffuse", color)
    return m


def placements(scene_id, seed):
    if scene_id not in SCENARIOS:
        raise ValueError("A12_UNKNOWN_SCENARIO")
    if not isinstance(seed, int) or not 0 <= seed <= 2**31-1:
        raise ValueError("A12_INVALID_SEED")
    r = random.Random(seed)
    jitter = lambda: (r.random() - .5) * .002
    # Geometry: dynamic discs. Unstable candidates are initially off-support
    # and/or tilted. These are hypotheses, never automatic ground-truth labels.
    specs = {
        "ST-01": [(0.00, 0.00, .589, 0., 0., .105, .035),
                  (0.00, 0.00, .625, 0., 0., .100, .035)],
        "ST-02": [(-.09, .025, .589, 0., 0., .11, .035),
                  (-.09, .025, .624, 0., 0., .085, .035),
                  (.135, -.05, .588, 0., 0., .068, .030)],
        "UN-01": [(.50, .005, .79, 0., 0., .10, .035),
                  (.51, .005, .84, 0., 0., .09, .035)],
        "UN-02": [(-.47, .34, .78, .52, .32, .12, .035),
                  (-.43, .30, .835, .25, .35, .09, .035)],
    }
    colors = ["0.87 0.90 0.96 1", "0.94 0.72 0.62 1", "0.76 0.92 0.73 1"]
    return [
        {"name": f"dish_{i+1:02d}", "x": x+jitter(), "y": y+jitter(),
         "z": z, "roll": roll, "pitch": pitch,
         "radius_m": rad, "thickness_m": height,
         "mass_kg": MASS_KG, "friction_mu": MU, "color": colors[i]}
        for i, (x,y,z,roll,pitch,rad,height) in enumerate(specs[scene_id])
    ]


def build_world(scene_id: str, seed: int):
    models = placements(scene_id, seed)
    root = ET.Element("sdf", version="1.9")
    w = el(root, "world", name=WORLD)
    el(w, "gravity", "0 0 -9.81")
    physics = el(w, "physics", name="tray_physics", type="ode")
    el(physics, "max_step_size", "0.001")
    el(physics, "real_time_factor", "1.0")
    for filename, name in [
        ("gz-sim-physics-system", "gz::sim::systems::Physics"),
        ("gz-sim-user-commands-system", "gz::sim::systems::UserCommands"),
        ("gz-sim-scene-broadcaster-system", "gz::sim::systems::SceneBroadcaster"),
    ]:
        el(w, "plugin", filename=filename, name=name)
    sensors = el(w, "plugin", filename="gz-sim-sensors-system",
                 name="gz::sim::systems::Sensors")
    el(sensors, "render_engine", "ogre2")
    sc = el(w, "scene")
    el(sc, "ambient", "0.72 0.72 0.72 1")
    el(sc, "background", "0.78 0.82 0.88 1")
    sun = el(w, "light", name="sun", type="directional")
    el(sun, "cast_shadows", "true")
    el(sun, "pose", "0 0 3 0 0 0")
    el(sun, "diffuse", "0.92 0.92 0.92 1")
    el(sun, "specular", "0.1 0.1 0.1 1")
    el(sun, "direction", "-0.3 -0.3 -0.8")
    w.append(box_model("tray_test_floor", (4,4,.10), (0,0,-.05,0,0,0),
                       "0.48 0.49 0.50 1"))
    w.append(box_model("tray_platform", (TRAY_WIDTH,TRAY_DEPTH,.04),
                       (0,0,TRAY_TOP-.02,0,0,0), "0.32 0.42 0.53 1"))
    w.append(standalone_camera_model())
    for d in models:
        w.append(plate_model(d["name"], d["x"],d["y"],d["z"],
                             d["roll"],d["pitch"],d["radius_m"],
                             d["thickness_m"],d["color"]))
    validate_world(root, models)
    return root, models


def validate_world(root, expected=None):
    w = root.find("./world[@name='smartdish_tray']")
    if w is None:
        raise ValueError("A12_WORLD_NAME_INVALID")
    if w.findtext("gravity") != "0 0 -9.81":
        raise ValueError("A12_GRAVITY_CHANGED")
    s = w.find("./model[@name='smartdish_tray_observer']/link/sensor")
    verify_camera(s)
    dish = [x for x in w.findall("model") if x.attrib["name"].startswith("dish_")]
    if not 2 <= len(dish) <= 3 or any(x.findtext("static") != "false" for x in dish):
        raise ValueError("A12_NO_DYNAMIC_DISH")
    if any(x.find(".//joint") is not None for x in dish):
        raise ValueError("A12_DISH_FIXED_JOINT_FORBIDDEN")
    if any(x.find(".//inertial") is None or x.find(".//collision") is None for x in dish):
        raise ValueError("A12_MASS_OR_COLLISION_MISSING")
    if any(x.findtext("./plugin[@name='gz::sim::systems::PosePublisher']/use_pose_vector_msg") != "true"
           or x.findtext("./plugin[@name='gz::sim::systems::PosePublisher']/publish_nested_model_pose") != "true"
           or x.findtext("./plugin[@name='gz::sim::systems::PosePublisher']/topic")
           != "/smartdish/tray/gz_pose/"+x.attrib["name"] for x in dish):
        raise ValueError("A12_GAZEBO_NAMED_POSE_PUBLISHER_MISSING")
    names = [x.attrib["name"] for x in dish]
    if len(set(names)) != len(names) or (expected is not None
                                        and names != [d["name"] for d in expected]):
        raise ValueError("A12_ENTITY_DUPLICATE_OR_DRIFT")
    return True


def write_trial(scene_id, seed, output: Path, trial_id: str):
    if not trial_id.isascii() or not trial_id.replace("_","").replace("-","").isalnum():
        raise ValueError("A12_TRIAL_ID_INVALID")
    root, plates = build_world(scene_id, seed)
    output = Path(output)
    if output.exists():
        raise ValueError("A12_NO_OVERWRITE")
    output.parent.mkdir(parents=True,exist_ok=True)
    xml = '<?xml version="1.0"?>\n' + ET.tostring(root,encoding="unicode") + '\n'
    output.write_text(xml)
    row = {"schema":1, "scene_id":scene_id, "stack_id":trial_id,
           "trial_id":trial_id, "seed":seed, "world_name":WORLD,
           "world_sha256":hashlib.sha256(xml.encode()).hexdigest(),
           "gravity_m_s2":-9.81,"friction_mu":MU,"mass_kg_per_dish":MASS_KG,
           "platform": {"width_m":TRAY_WIDTH,"depth_m":TRAY_DEPTH,"top_z_m":TRAY_TOP},
           "initial_dishes":plates,"observation_seconds":SIM_SECS,
           "scenario_hint_only_not_ground_truth":scene_id,
           "label":"REVIEW_REQUIRED", "input_capture_phase":"PRE_OBSERVATION",
           "ground_truth":"NOT_YET_OBSERVED"}
    metadata=output.with_suffix(".scenario.json")
    if metadata.exists():
        raise ValueError("A12_NO_OVERWRITE_METADATA")
    metadata.write_text(json.dumps(row,indent=2,sort_keys=True)+'\n')
    return row



def split_scene_for_sensor_warmup(full_sdf: Path):
    """Preserve full physical contract, load a camera-only world for warmup.

    Dish SDFs are spawned via Gazebo's real UserCommands EntityFactory API
    AFTER an actual ROS camera frame has proved the bridge is ready.
    Nothing is static/fixed: each spawned dish retains its original model
    mass, inertial, friction, pose and PosePublisher parameters.
    """
    source=Path(full_sdf)
    root=ET.parse(source).getroot()
    w=root.find("./world[@name='%s']" % WORLD)
    if w is None:
        raise ValueError("A12_WARMUP_ORIGINAL_WORLD_MISSING")
    dishes=[m for m in list(w.findall("model"))
            if m.attrib.get("name","").startswith("dish_")]
    if not 2<=len(dishes)<=3:
        raise ValueError("A12_WARMUP_EXPECTED_DYNAMIC_DISHES")
    validate_world(root)
    plan=[]
    for model in dishes:
        name=model.attrib["name"]
        if model.findtext("static")!="false":
            raise ValueError("A12_WARMUP_DYNAMIC_DISH_REQUIRED")
        individual=ET.Element("sdf",version="1.9")
        individual.append(model)
        dish_sdf=source.with_name(name+".sdf")
        if dish_sdf.exists():
            raise ValueError("A12_WARMUP_DISH_NO_OVERWRITE")
        content='<?xml version="1.0"?>\n'+ET.tostring(individual,encoding="unicode")+"\n"
        dish_sdf.write_text(content)
        plan.append({"name":name,"path":str(dish_sdf.resolve()),
                     "sha256":hashlib.sha256(content.encode()).hexdigest()})
        w.remove(model)
    world_sdf=source.with_name("sensor_preflight.sdf")
    if world_sdf.exists():
        raise ValueError("A12_WARMUP_WORLD_NO_OVERWRITE")
    content='<?xml version="1.0"?>\n'+ET.tostring(root,encoding="unicode")+"\n"
    world_sdf.write_text(content)
    manifest={"schema":1,"original_scenario_sdf":source.name,
              "sensor_preflight_sdf":world_sdf.name,
              "sensor_preflight_sha256":hashlib.sha256(content.encode()).hexdigest(),
              "spawned_dynamic_models":plan,
              "method":"GAZEBO_REAL_ENTITYFACTORY_AFTER_LIVE_CAMERA_WARMUP",
              "label":"REVIEW_REQUIRED"}
    manifest_path=source.with_name("sensor_preflight_manifest.json")
    if manifest_path.exists():
        raise ValueError("A12_WARMUP_MANIFEST_NO_OVERWRITE")
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return world_sdf,manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scenario",choices=SCENARIOS,required=True)
    p.add_argument("--seed",type=int,default=101)
    p.add_argument("--trial-id",required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    row=write_trial(a.scenario,a.seed,a.out,a.trial_id)
    print("SMARTDISH_A12_TRIAL_SDF_GENERATED_UNVERIFIED="+row["world_sha256"])


if __name__ == "__main__":
    main()
