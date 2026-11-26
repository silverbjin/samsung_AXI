import io,sys,math,tarfile,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ai/scripts"))
import audit_b_qa05_diversity as q
import b_qa05_cli as cli
def test_bit_hamming():
    assert q.hamming("0"*64,"1"*64)==64
    assert q.hamming("0"*64,"0"*63+"1")==1
    with pytest.raises(ValueError):q.hamming("f"*16,"0"*16)
def test_roi_bounds():
    assert q.crop_box((1.1,2.1,8.2,9.2))==(1,2,9,10)
    for b in [(-1,2,8,9),(1,2,640,9),(1,2,1,9),(1,2,float("nan"),9)]:
        with pytest.raises(ValueError):q.crop_box(b)
def test_projection():
    cam=dict(x=0,y=0,z=0,qx=0,qy=0,qz=0,qw=1)
    assert q.project((1,0,0),cam,[100,0,320,0,100,240,0,0,1])==(320,240)
    with pytest.raises(ValueError):q.project((-1,0,0),cam,[100,0,320,0,100,240,0,0,1])
def test_same_different():
    a=Image.new("RGB",(64,64),"black");b=Image.new("RGB",(64,64),"white")
    x,y=q.image_data(a),q.image_data(b)
    assert q.pixels(a)!=q.pixels(b)
    assert q.block_ssim(x["gray"],x["gray"])==pytest.approx(1)
    assert q.block_ssim(x["gray"],y["gray"])<.01
    assert q.hamming(x["ahash"],y["ahash"])==0 # uniform images can share aHash
def fixture(n,layout=None):
    r={"scene_id":str(n),"layout":layout or str(n),"family":str(n%4),"observation":"POSITION_MAINTAINED" if n%2 else "LARGE_DISPLACEMENT","pixel_sha":str(n),"image_sha":str(n)}
    im=Image.new("RGB",(8,8),(n,n,n));return (r,{k:q.image_data(im) for k in q.REGIONS},b"",{})
def test_pairs_and_duplicate():
    items=[fixture(i) for i in range(12)]
    items[1][0]["pixel_sha"]=items[0][0]["pixel_sha"]
    rows=q.similarity(items)
    assert len(rows)==66 and sum(x["same_pixel"] for x in rows)==1
def test_layout_group_seed_and_split():
    records=[fixture(i)[0] for i in range(12)]
    records.append(dict(records[0],seed=100,scene_id="repeat"))
    assert len(q.unique_layouts(records))==12
    r=q.split_feasibility(records,[])
    assert r["layout_groups"]==12 and r["scope"]=="NON_RELEASED_SIMULATION" and not r["released"] and r["approved_groups"]==0
    assert r["family_partitions_with_every_observation_in_each_split"]==0
def test_wrong_sha(tmp_path):
    p=tmp_path/"a";p.write_bytes(b"bad");Path(str(p)+".sha256").write_text("0"*64+"  a\n")
    with pytest.raises(ValueError):q.get(p,"a","0"*64)
def test_safe_tar_reused():
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        m=tarfile.TarInfo("../bad");m.size=1;t.addfile(m,io.BytesIO(b"x"))
    with pytest.raises(ValueError):q.a16.read_tar(b.getvalue(),q.sha(b.getvalue()),allowed=set())
def make_a15_schema_fixture():
    """Synthetic contract only. Real schemas, fabricated pixels and poses."""
    from xml.etree import ElementTree as ET
    d={"scene_id":"L15-01","trial_id":"fixture","source_sha":q.a15.A15_SHA,"seed":0,"environment_profile_id":"A15_STATIC_TRAY_OVERHEAD_V1","human_approved":False,"rule_candidate":"UNKNOWN","platform":{"width_m":.7,"depth_m":.56},"trigger":{"frame":"world","torque_nm":[0,.12,0],"start_ns":q.a15.TRIGGER_NS},"end_ns":q.a15.END_NS}
    ds=[dict(name="dish_01",radius_m=.11,thickness_m=.035,mass_kg=.22,friction_mu=.65,x=0.,y=0.,z=.5875),dict(name="dish_02",radius_m=.085,thickness_m=.035,mass_kg=.22,friction_mu=.65,x=.01,y=0.,z=.6225)]
    d["initial_dishes"]=ds
    canonical=lambda v:q.sha(json.dumps(v,sort_keys=True,separators=(",",":")).encode())
    fam=canonical({"shape":"cylinder_stack_2","dimensions":[[x["radius_m"],x["thickness_m"]] for x in ds],"mass":.22,"mu":.65})
    lay=canonical({"family":fam,"centers":[[x[k] for k in ("x","y","z")] for x in ds]})
    d.update(geometry_family_id=fam,physical_layout_id=lay,stack_id=lay)
    xml='<sdf><world><model name="tray_platform"><link><visual><geometry><box><size>0.7 0.56 0.04</size></box></geometry></visual></link></model>'
    for x in ds:
        xml+=f'<model name="{x["name"]}"><link><visual><geometry><cylinder><radius>{x["radius_m"]}</radius><length>{x["thickness_m"]}</length></cylinder></geometry><material><diffuse>0.5 0.5 0.5 1</diffuse></material></visual></link></model>'
    sdf=(xml+'</world></sdf>').encode();d["world_sha256"]=q.sha(sdf)
    v={"scene_id":"L15-01","source_sha":q.a15.A15_SHA,"human_approved":False,"ground_truth":"UNKNOWN_HOLD","production_contact_health":"HOLD","cleanup":"FAIL","processes":[{"role":"server","returncode":-11}],"metrics":{x["name"]:{"max_relative_displacement_m":0.} for x in ds}}
    info={"stamp_ns":q.a15.T0_NS,"width":640,"height":480,"k":[381.,0,320.,0,381.,240.,0,0,1],"d":[0.]*5}
    buf=io.BytesIO();Image.new("RGB",(640,480),"gray").save(buf,format="PNG");png=buf.getvalue()
    c={"camera_info":info,"stamp_ns":q.a15.T0_NS,"encoding":"rgb8","image_sha256":q.sha(png)}
    cam={"x":0.,"y":0.,"z":1.5,"qx":0.,"qy":math.sqrt(.5),"qz":0.,"qw":math.sqrt(.5)}
    iv={"support":{},"dishes":{}}
    import itertools
    for x in ds:
        rad=math.hypot(x["radius_m"],x["thickness_m"]/2)
        pts=[q.project(tuple(x[k]+v for k,v in zip(("x","y","z"),delta)),cam,info["k"]) for delta in itertools.product((-rad,rad),repeat=3)]
        iv["dishes"][x["name"]]={"conservative_projected_bbox_px":q.bounds(pts)}
    pose="sim_ns\tentity\tx\ty\tz\tqx\tqy\tqz\tqw\n"
    for stamp in range(q.a15.T0_NS,q.a15.END_NS+1,100_000_000):
        for n,p in [("camera",cam),("tray_platform",dict(x=0,y=0,z=.55,qx=0,qy=0,qz=0,qw=1))]+[(x["name"],dict(x=x["x"],y=x["y"],z=x["z"],qx=0,qy=0,qz=0,qw=1)) for x in ds]:
            pose+=str(stamp)+"\t"+n+"\t"+"\t".join(str(p[k]) for k in ("x","y","z","qx","qy","qz","qw"))+"\n"
    f={"scenario.sdf":sdf,"poses.tsv":pose.encode(),"tray_rgb_t0.png":png}
    for k,obj in (("a15_design.json",d),("capture.json",c),("initial_validity.json",iv),("verdict.json",v)):
        f[k]=json.dumps(obj).encode()
    return f
def test_positive_adapter_and_workbook(tmp_path):
    f=make_a15_schema_fixture()
    with patch.dict(q.a15.EXPECTED_IMAGES,{"L15-01":q.sha(f["tray_rgb_t0.png"])}):
        item=q.adapt(f,"a15","L15-01","fixture")
    r=item[0]
    assert r["visibility"]=="BBOX_ONLY_NOT_SEGMENTATION" and r["contact_health"]=="HOLD" and r["cleanup"]=="FAIL" and r["gt"]=="UNKNOWN_HOLD"
    assert set(item[1])==set(q.REGIONS) and len(item[3]["dish_01"])==104
    assert not r["training_eligible"]
    q.workbook(tmp_path,[item],[])
    import csv
    row=next(csv.DictReader((tmp_path/"review_worksheet.csv").open()))
    assert all(not row[k] for k in ("initial_placement","occlusion","physics_validity","learning_suitability","license_status","gt_decision","reviewer","reason"))
    assert set(x.name for x in tmp_path.iterdir())=={"review_workbook.html","review_worksheet.csv"}
def test_missing_image_fails():
    f=make_a15_schema_fixture();del f["tray_rgb_t0.png"]
    with pytest.raises(KeyError,match="tray_rgb_t0.png"):q.adapt(f,"a15","L15-01","fixture")
@pytest.mark.parametrize("key,value,error",[("human_approved",True,"GT_BOUNDARY"),("production_contact_health","PASS","CONTACT_CLEANUP_BOUNDARY"),("cleanup","PASS","CONTACT_CLEANUP_BOUNDARY")])
def test_no_gt_contact_or_cleanup_promotion(key,value,error):
    f=make_a15_schema_fixture();v=json.loads(f["verdict.json"]);v[key]=value;f["verdict.json"]=json.dumps(v).encode()
    with pytest.raises(ValueError,match=error):q.adapt(f,"a15","L15-01","fixture")
def test_layout_family_conflict():
    records=[fixture(0)[0],dict(fixture(1)[0],layout="0")]
    with pytest.raises(ValueError,match="LAYOUT_FAMILY_CONFLICT"):q.unique_layouts(records)
def test_link_rejected():
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        m=tarfile.TarInfo("link");m.type=tarfile.SYMTYPE;m.linkname="../outside";t.addfile(m)
    with pytest.raises(ValueError):q.a16.read_tar(b.getvalue(),q.sha(b.getvalue()),allowed=set())
def test_actual_sha_receipt_mismatch(tmp_path):
    p=tmp_path/"x";p.write_bytes(b"data");Path(str(p)+".sha256").write_text("0"*64+"  x\n");r={}
    with pytest.raises(ValueError):q.get(p,"x","0"*64,r)
    assert r["actual_sha256"]==q.sha(b"data") and not r["verified"]
def test_failure_diagnostic_and_no_overwrite(tmp_path):
    pin="a"*40
    args=["--a15",str(tmp_path/"missing"),"--a16",str(tmp_path/"missing"),"--a16-diag",str(tmp_path/"missing"),"--qa04",str(tmp_path/"missing"),"--out-dir",str(tmp_path/"out"),"--verifier-sha",pin]
    with patch.object(cli.subprocess,"check_output",side_effect=[pin+"\n",""]):
        assert cli.main(args)==2
    out=tmp_path/"out";r=json.loads((out/"qa05_report.json").read_text())
    assert not r["actual_12_scene_roi_review"] and r["approved_count"]==0 and not r["training_eligible"] and r["production_contact_health"]=="HOLD" and r["cleanup"]=="FAIL"
    status=json.loads((out/"diagnostic_status.json").read_text())
    assert set(status["input_receipt"])==set(q.INPUTS) and all(not r["verified"] for r in status["input_receipt"].values())
    assert not (out/"approval_ledger.jsonl").exists() and not (out/"train_manifest.csv").exists()
    a=out/"b_qa05_diagnostics.tar.gz";assert hashlib.sha256(a.read_bytes()).hexdigest() in Path(str(a)+".sha256").read_text()
    with tarfile.open(a) as t:assert set(t.getnames())=={"qa05_report.json","diagnostic_status.json","SHA256SUMS"}
    with pytest.raises(FileExistsError):cli.main(args)

def test_seed_jitter_profile_rejected():
    f=make_a15_schema_fixture();d=json.loads(f["a15_design.json"]);d["seed"]=1;f["a15_design.json"]=json.dumps(d).encode()
    with pytest.raises(ValueError,match="UNQUALIFIED_SEED"):q.adapt(f,"a15","L15-01","fixture")
def test_same_physical_signature_not_new_layout():
    records=[dict(fixture(0)[0],physical_signature="same"),dict(fixture(1)[0],physical_signature="same")]
    with pytest.raises(ValueError,match="SAME_PHYSICS_DISTINCT_LAYOUT_REVIEW"):q.unique_layouts(records)
def test_complete_12_scene_synthetic_outputs(tmp_path):
    """Exercise all output writers; no Owner data, no real acceptance."""
    import copy,csv
    f=make_a15_schema_fixture()
    with patch.dict(q.a15.EXPECTED_IMAGES,{"L15-01":q.sha(f["tray_rgb_t0.png"])}):
        item=q.adapt(f,"a15","L15-01","fixture")
    items=[]
    for i in range(12):
        r=copy.deepcopy(item[0]);im=Image.new("RGB",(8,8),(i,i,i))
        r.update(scene_id=f"FIXTURE-{i:02d}",layout=f"layout-{i}",stack_id=f"layout-{i}",physical_signature=f"physical-{i}",family=f"family-{i%4}",pixel_sha=q.pixels(im),image_sha=f"file-{i}",observation="POSITION_MAINTAINED" if i%2 else "LARGE_DISPLACEMENT")
        items.append((r,{k:q.image_data(im) for k in q.REGIONS},item[2],item[3],item[4]))
    result=q.finalize(items,{"near_duplicate_review_candidates":[]},{},tmp_path)
    assert result["scenes"]==12 and result["roi"]["pair_count"]==66
    assert not result["roi"]["qa04_full_ahash_matches"] and len(result["roi"]["qa04_full_ahash_mismatches"])==66
    assert not result["product_approval"] and result["approved_count"]==0
    assert result["gates"]["B-Q01"]=="PASS" and all(result["gates"][f"B-Q0{i}"]=="HOLD" for i in range(2,8))
    for region in q.REGIONS:
        for metric in ("ahash","dhash","block_ssim"):
            with (tmp_path/(region+"_"+metric+"_12x12.csv")).open() as file:rows=list(csv.DictReader(file))
            assert len(rows)==12 and len(rows[0])==13
    with (tmp_path/"similarity_matrix.csv").open() as file:assert len(list(csv.DictReader(file)))==66
    with (tmp_path/"review_worksheet.csv").open() as file:rows=list(csv.DictReader(file))
    assert len(rows)==12 and all(not row["gt_decision"] and not row["reviewer"] for row in rows)
    assert (tmp_path/"review_workbook.html").is_file() and (tmp_path/"pose_review_timeseries.csv").is_file()
    assert (tmp_path/"next_a_requirements.json").is_file() and (tmp_path/"shortcut_summary.json").is_file()
    assert not any(p.name in ("approval_ledger.jsonl","manifest.csv","split_manifest.csv","train_manifest.csv") for p in tmp_path.iterdir())
