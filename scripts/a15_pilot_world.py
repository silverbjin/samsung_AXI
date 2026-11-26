"""A15 loaded-domain pilot. No scene name or geometry implies ground truth."""
import hashlib,json,math
from pathlib import Path
import xml.etree.ElementTree as ET
import smartdish_tray_world as w
from smartdish_a14_physics import configure_sdf

SCENES=("L15-01","L15-02","L15-03","L15-04")
TRIGGER_NS=2_200_000_000
DURATION_NS=500_000_000
END_NS=12_300_000_000
TORQUE_NM=.12
STEP_NS=1_000_000
def hash_json(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def design(scene):
    if scene not in SCENES:raise ValueError("A15_SCENE_UNKNOWN")
    idx=SCENES.index(scene);family=idx//2
    base_r,top_r=(.11,.085) if family==0 else (.13,.09)
    offset=.01 if idx%2==0 else base_r-.018
    dims=[(base_r,.035),(top_r,.035)]
    centers=[(-.05,0,w.TRAY_TOP+.0175),(-.05+offset,0,w.TRAY_TOP+.0525)]
    dishes=[dict(name=f"dish_{i+1:02}",x=x,y=y,z=z,roll=0.,pitch=0.,radius_m=r,thickness_m=h,mass_kg=w.MASS_KG,friction_mu=w.MU,color=("0.87 0.90 0.96 1","0.94 0.72 0.62 1")[i]) for i,((r,h),(x,y,z)) in enumerate(zip(dims,centers))]
    # Family is geometry/material identity, not scene or outcome; layout is actual nominal geometry/pose.
    f=hash_json({"shape":"cylinder_stack_2","dimensions":dims,"mass":w.MASS_KG,"mu":w.MU})
    l=hash_json({"family":f,"centers":centers})
    for d in dishes:
        if abs(d["x"])+d["radius_m"]>w.TRAY_WIDTH/2 or abs(d["y"])+d["radius_m"]>w.TRAY_DEPTH/2:
            raise ValueError("A15_INITIAL_OUTSIDE_TRAY")
    return dict(schema=1,scene_id=scene,geometry_family_id=f,physical_layout_id=l,initial_dishes=dishes,platform=dict(width_m=w.TRAY_WIDTH,depth_m=w.TRAY_DEPTH,top_z_m=w.TRAY_TOP),physics_profile="STATIC_TRAY_COMMON_TORQUE_PILOT",trigger=dict(target="dish_02/body",frame="world",torque_nm=[0,TORQUE_NM,0],start_ns=TRIGGER_NS,duration_ns=DURATION_NS),end_ns=END_NS,step_ns=STEP_NS,environment_profile_id="A15_STATIC_TRAY_OVERHEAD_V1",ground_truth="NOT_OPERATOR_APPROVED",human_approved=False,rule_candidate="UNKNOWN")
def generate(scene,out,pose_plugin,health_plugin):
    out=Path(out);meta=design(scene)
    root,_=w.build_world("ST-01",101)
    world=root.find("world")
    for m in list(world.findall("model")):
        if m.get("name","").startswith("dish_"):world.remove(m)
    for d in meta["initial_dishes"]:
        world.append(w.plate_model(d["name"],d["x"],d["y"],d["z"],0.,0.,d["radius_m"],d["thickness_m"],d["color"]))
    path=out/"scenario.sdf"
    with path.open("xb") as f:f.write(ET.tostring(root,encoding="utf-8",xml_declaration=True))
    meta.update(trial_id=out.name,seed=0,stack_id=meta["physical_layout_id"])
    # Reuse exact A14 contact SDF/bridge generator; its STATIC_GRAVITY metadata
    # is auxiliary legacy output, NOT the A15 profile. Keep A15 metadata separate.
    cfg=configure_sdf(path,dict(meta))
    # Remove auxiliary legacy metadata generated in this new trial only; the
    # A15 design is the sole profile/identity authority.
    path.with_suffix(".scenario.json").unlink()
    (out/"geometry_layout.json").unlink()
    tree=ET.parse(path);world=tree.getroot().find("world")
    p=ET.SubElement(world,"plugin",filename=str(Path(pose_plugin).resolve()),name="smartdish::A15Pilot")
    for k,v in dict(output=str((out/"poses.tsv").resolve()),trigger_output=str((out/"trigger.tsv").resolve()),trigger_ns=TRIGGER_NS,duration_ns=DURATION_NS,torque_nm=TORQUE_NM).items():ET.SubElement(p,k).text=str(v)
    p=ET.SubElement(world,"plugin",filename=str(Path(health_plugin).resolve()),name="smartdish::A14ProductionHealth")
    ET.SubElement(p,"output").text=str((out/"ecm_contact_steps.tsv").resolve())
    ET.SubElement(p,"late_control").text="false"
    tree.write(path,encoding="utf-8",xml_declaration=True)
    meta.update(world_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),contact_topics=cfg["topics"],pose_plugin_sha256=hashlib.sha256(Path(pose_plugin).read_bytes()).hexdigest(),health_plugin_sha256=hashlib.sha256(Path(health_plugin).read_bytes()).hexdigest())
    (out/"a15_design.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta
