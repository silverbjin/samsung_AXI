"""A18 고정 교차 구성. 물리 관측을 정답으로 승격하지 않는다."""
import hashlib,json,math,uuid,os
from pathlib import Path
import xml.etree.ElementTree as ET
import smartdish_tray_world as w
from smartdish_a14_physics import configure_sdf
from a15_pilot_world import STEP_NS,TRIGGER_NS,DURATION_NS,END_NS,TORQUE_NM,design as design15,SCENES as S15
from a16_pilot_world import design as design16,SCENES as S16
PLATFORM_SHA="b8ef3998973a5e33b67ddd5c5b63c3c89b837840"
VERSION="SMARTDISH_A18_V1"
REGISTRY=Path(__file__).resolve().parents[1]/"config/smartdish_a18_layouts.json"
SCENES=tuple(f"L18-{i:02d}" for i in range(1,9))
COLORS=("0.87 0.90 0.96 1","0.94 0.72 0.62 1","0.76 0.92 0.73 1","0.78 0.80 0.93 1")
def need(ok,reason):
    if not ok:raise ValueError(reason)
def hash_json(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def mic(v):return round(float(v)*1_000_000)
def geometry(ds):return [[mic(d[k]) for k in ("radius_m","thickness_m","mass_kg","friction_mu")] for d in ds]
def poses(ds):return [[mic(d.get(k,0)) for k in ("x","y","z","roll","pitch","yaw")] for d in ds]
def fingerprint(ds):
    return hash_json({"version":"A18_CANONICAL_PHYSICAL_V1","shape":"uniform_solid_cylinder_stack","geometry_um_mg_micro_mu":geometry(ds),"pose_um_urad":poses(ds)})
def old_designs():return [design15(s) for s in S15]+[design16(s) for s in S16]
def read_registry():
    r=json.loads(REGISTRY.read_text())
    need(r["schema"]==3 and r["version"]==VERSION and tuple(x["scene_id"] for x in r["layouts"])==SCENES,"A18_REGISTRY_CONTRACT")
    need([x["phase"] for x in r["layouts"]]==[1]*4+[2]*4,"A18_PHASE_CONTRACT")
    return r
def phase_scenes(phase):
    need(phase in (1,2),"A18_PHASE")
    return tuple(x["scene_id"] for x in read_registry()["layouts"] if x["phase"]==phase)
def design(scene):
    r=read_registry();need(scene in SCENES,"A18_SCENE_UNKNOWN")
    spec=r["layouts"][SCENES.index(scene)];fam=r["families"][spec["family"]];dims=fam["dims"];xs=spec["x"]
    need(2<=len(dims)<=4 and len(xs)==len(dims),"A18_DISH_COUNT")
    z=w.TRAY_TOP;ds=[];boxes=[];clearances=[]
    for i,((radius,height),x) in enumerate(zip(dims,xs)):
        need(all(math.isfinite(v) for v in (radius,height,x)) and radius>0 and height>0,"A18_NONFINITE_GEOMETRY")
        d=dict(name=f"dish_{i+1:02}",x=x,y=0.,z=round(z+height/2,6),roll=0.,pitch=0.,yaw=0.,radius_m=radius,thickness_m=height,mass_kg=w.MASS_KG,friction_mu=w.MU,color=COLORS[i])
        z+=height;ds.append(d)
        rad=math.hypot(radius,height/2)
        clearances.append(min(w.TRAY_WIDTH/2-abs(x)-rad,w.TRAY_DEPTH/2-rad))
        need(clearances[-1]>0,"A18_NOMINAL_OUTSIDE")
        uv=[(320-381.3611602783203*dy/(1.5-d["z"]-dz),240-381.361141204834*(x+dx)/(1.5-d["z"]-dz)) for dx in (-rad,rad) for dy in (-rad,rad) for dz in (-rad,rad)]
        box=[min(p[0] for p in uv),min(p[1] for p in uv),max(p[0] for p in uv),max(p[1] for p in uv)]
        need(0<=box[0]<=box[2]<640 and 0<=box[1]<=box[3]<480,"A18_NOMINAL_FOV");boxes.append(box)
    sub=[]
    for i,d in enumerate(ds[:-1]):
        above=ds[i+1:];total=sum(a["mass_kg"] for a in above)
        x=sum(a["x"]*a["mass_kg"] for a in above)/total
        y=sum(a["y"]*a["mass_kg"] for a in above)/total
        m=d["radius_m"]-math.hypot(x-d["x"],y-d["y"]);need(m>0,"A18_NOMINAL_SUBSTACK_UNSUPPORTED");sub.append(round(m,6))
    g=geometry(ds);p=poses(ds);old=old_designs();matching={x["geometry_family_id"] for x in old if geometry(x["initial_dishes"])==g}
    family=next(iter(matching)) if len(matching)==1 else hash_json({"version":"A18_FAMILY_V1","shape":"uniform_solid_cylinder_stack","geometry_um_mg_micro_mu":g})
    need(len(matching)<=1 and family==fam["id"],"A18_FAMILY_MISMATCH")
    fp=fingerprint(ds);need(fp not in {fingerprint(x["initial_dishes"]) for x in old},"A18_HISTORICAL_LAYOUT_DUPLICATE")
    layout=hash_json({"version":"A18_LAYOUT_V1","family_id":family,"pose_um_urad":p})
    dx=round(ds[-1]["x"]-ds[-2]["x"],6);margin=round(ds[-2]["radius_m"]-abs(dx),6)
    return dict(schema=3,producer_version=VERSION,scene_id=scene,phase=spec["phase"],geometry_family_id=family,physical_layout_id=layout,comparison_fingerprint=fp,physical_fingerprint=fp,hash_version="A18_CANONICAL_PHYSICAL_V1",family_basis={"shape":"uniform_solid_cylinder_stack","geometry_um_mg_micro_mu":g},layout_basis=p,initial_dishes=ds,platform=dict(width_m=w.TRAY_WIDTH,depth_m=w.TRAY_DEPTH,top_z_m=w.TRAY_TOP),platform_sha=PLATFORM_SHA,physics_profile="STATIC_TRAY_FIXED_WORLD_Y_TORQUE",prediction_contract="FIXED_WORLD_Y_TORQUE_CONDITIONAL",trigger_profile="A16_UPPERMOST_WORLD_Y_012NM_500MS_V1",trigger=dict(target=ds[-1]["name"]+"/body",frame="world",torque_nm=[0,TORQUE_NM,0],start_ns=TRIGGER_NS,duration_ns=DURATION_NS),end_ns=END_NS,step_ns=STEP_NS,t0_ns=2_000_000_000,environment_profile_id="A15_STATIC_TRAY_OVERHEAD_V1",ground_truth="UNKNOWN_HOLD",human_approved=False,training_eligible=False,rule_candidate="UNKNOWN",nominal_center_support_margin_m=margin,nominal_full_containment_margin_m=round(margin-ds[-1]["radius_m"],6),nominal_substack_center_margins_m=sub,nominal_bboxes_px=boxes,nominal_min_tray_clearance_m=min(clearances),upper_tray_center_group="CENTER" if ds[-1]["x"]==0 else "ECCENTRIC",upper_support_offset_x_m=dx,expected_entities=["tray_platform","camera"]+[d["name"] for d in ds],comparison_scene=spec["comparison"],qa05_evidence_sha256=r["qa05_evidence_sha256"],exclusion_reason=None)

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
    meta.update(trial_id=uuid.uuid4().hex, batch_id=os.environ.get("SMARTDISH_A18_BATCH_ID",uuid.uuid4().hex),seed=0,stack_id=meta["physical_layout_id"],observation_id=uuid.uuid4().hex)
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
    (out/"a18_design.json").write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    return meta
