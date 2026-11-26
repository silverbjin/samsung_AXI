"""A16 versioned independent layout registry, no labels or outcome-dependent selection."""
import hashlib,json,math,uuid,os
from pathlib import Path
import xml.etree.ElementTree as ET
import smartdish_tray_world as w
from smartdish_a14_physics import configure_sdf
from a15_pilot_world import STEP_NS,TRIGGER_NS,DURATION_NS,END_NS,TORQUE_NM,hash_json
PLATFORM_SHA="b8ef3998973a5e33b67ddd5c5b63c3c89b837840"
VERSION="SMARTDISH_A16_V1"
SCENES=tuple(f"L16-{i:02d}" for i in range(1,9))
DIMS=(((.115,.045),(.082,.050)),((.140,.025),(.105,.025),(.075,.035)))
# lower center, upper center, nominal hypothesis; not an expected label
LAYOUTS=((-0.012,0., "SMALL_PLAUSIBLE"),(-.097,0.,"LARGE_PLAUSIBLE"),(.09,.102,"SMALL_PLAUSIBLE"),(-.005,-.102,"OPPOSITE_ALIGNMENT_UNCERTAIN"),
         (-.012,0.,"SMALL_PLAUSIBLE"),(.087,0.,"OPPOSITE_ALIGNMENT_UNCERTAIN"),(-.09,-.102,"SMALL_PLAUSIBLE"),(.015,.102,"LARGE_PLAUSIBLE"))
def design(scene):
    if scene not in SCENES:raise ValueError("A16_SCENE_UNKNOWN")
    idx=SCENES.index(scene);dims=DIMS[idx//4];lower,upper,hyp=LAYOUTS[idx]
    z=w.TRAY_TOP;dishes=[]
    for i,(r,h) in enumerate(dims):
        x=upper if i==len(dims)-1 else lower
        d=dict(name=f"dish_{i+1:02}",x=x,y=0.,z=round(z+h/2,5),roll=0.,pitch=0.,yaw=0.,radius_m=r,thickness_m=h,mass_kg=w.MASS_KG,friction_mu=w.MU,color=("0.87 0.90 0.96 1","0.94 0.72 0.62 1","0.76 0.92 0.73 1")[i])
        z+=h;dishes.append(d)
        if abs(x)+math.hypot(r,h/2)>w.TRAY_WIDTH/2 or math.hypot(r,h/2)>w.TRAY_DEPTH/2:raise ValueError("A16_NOMINAL_OUTSIDE")
    geometry={"shape":"cylinder_stack","dimensions_m":dims,"mass_kg_per_dish":w.MASS_KG,"friction_mu":w.MU,"inertia":"UNIFORM_SOLID_CYLINDER"}
    poses=[[d[k] for k in ("x","y","z","roll","pitch","yaw")] for d in dishes]
    family=hash_json({"version":"A16_FAMILY_V1","geometry":geometry})
    physical={"geometry":geometry,"world_poses_m_rad":poses}
    layout=hash_json({"version":"A16_LAYOUT_V1","family":family,"world_poses_m_rad":poses})
    margin=dims[-2][0]-abs(upper-lower)
    if margin<=0:raise ValueError("A16_NOMINAL_UNSUPPORTED")
    return dict(schema=2,producer_version=VERSION,hash_version="SORTED_COMPACT_JSON_UTF8_V1",scene_id=scene,geometry_family_id=family,physical_layout_id=layout,physical_fingerprint=hash_json(physical),family_basis=geometry,layout_basis=poses,initial_dishes=dishes,platform=dict(width_m=w.TRAY_WIDTH,depth_m=w.TRAY_DEPTH,top_z_m=w.TRAY_TOP),platform_sha=PLATFORM_SHA,physics_profile="STATIC_TRAY_COMMON_TORQUE_PILOT",trigger_profile="A16_UPPERMOST_WORLD_Y_012NM_500MS_V1",trigger=dict(target=dishes[-1]["name"]+"/body",frame="world",torque_nm=[0,TORQUE_NM,0],start_ns=TRIGGER_NS,duration_ns=DURATION_NS),end_ns=END_NS,step_ns=STEP_NS,t0_ns=2000000000,environment_profile_id="A15_STATIC_TRAY_OVERHEAD_V1",ground_truth="UNKNOWN_HOLD",human_approved=False,training_eligible=False,rule_candidate="UNKNOWN",design_hypothesis=hyp,nominal_support_margin_m=round(margin,6),upper_tray_center_group="CENTER" if upper==0 else "ECCENTRIC",upper_support_offset_x_m=round(upper-lower,6),expected_entities=["tray_platform","camera"]+[d["name"] for d in dishes],exclusion_reason=None)

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
    meta.update(trial_id=uuid.uuid4().hex, batch_id=os.environ.get("SMARTDISH_A16_BATCH_ID",uuid.uuid4().hex),seed=0,stack_id=meta["physical_layout_id"])
    # Reuse exact A14 contact SDF/bridge generator; its STATIC_GRAVITY metadata
    # is auxiliary legacy output, NOT the A15 profile. Keep A16 metadata separate.
    cfg=configure_sdf(path,dict(meta))
    # Remove auxiliary legacy metadata generated in this new trial only; the
    # A16 design is the sole profile/identity authority.
    path.with_suffix(".scenario.json").unlink()
    (out/"geometry_layout.json").unlink()
    tree=ET.parse(path);world=tree.getroot().find("world")
    p=ET.SubElement(world,"plugin",filename=str(Path(pose_plugin).resolve()),name="smartdish::A16Pilot")
    for k,v in dict(output=str((out/"poses.tsv").resolve()),trigger_output=str((out/"trigger.tsv").resolve()),trigger_ns=TRIGGER_NS,duration_ns=DURATION_NS,torque_nm=TORQUE_NM,target_model=meta["initial_dishes"][-1]["name"],registry_output=str((out/"entity_registry.tsv").resolve())).items():ET.SubElement(p,k).text=str(v)
    p=ET.SubElement(world,"plugin",filename=str(Path(health_plugin).resolve()),name="smartdish::A14ProductionHealth")
    ET.SubElement(p,"output").text=str((out/"ecm_contact_steps.tsv").resolve())
    ET.SubElement(p,"late_control").text="false"
    tree.write(path,encoding="utf-8",xml_declaration=True)
    meta.update(world_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),contact_topics=cfg["topics"],pose_plugin_sha256=hashlib.sha256(Path(pose_plugin).read_bytes()).hexdigest(),health_plugin_sha256=hashlib.sha256(Path(health_plugin).read_bytes()).hexdigest())
    (out/"a16_design.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta
