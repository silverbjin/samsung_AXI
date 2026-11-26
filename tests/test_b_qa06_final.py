import io,sys,tarfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import pytest
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ai/scripts"))
import b_qa06_cli as q
def tar(files,unsafe=None):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        for n,v in {**files,"SHA256SUMS":"".join(q.sha(v)+"  "+n+"\n" for n,v in files.items()).encode()}.items():
            m=tarfile.TarInfo(n);m.size=len(v);t.addfile(m,io.BytesIO(v))
        if unsafe:
            m=tarfile.TarInfo(unsafe);m.type=tarfile.SYMTYPE;m.linkname="/tmp/x";t.addfile(m)
    return b.getvalue()
def test_tar_and_wrong_sha():
    b=tar({"x":b"abc"});assert q.safe_tar(b,q.sha(b))=={"x":b"abc"}
    with pytest.raises(ValueError,match="ARCHIVE_SHA"):q.safe_tar(b,"0"*64)
@pytest.mark.parametrize("name",["../escape","/abs","link"])
def test_unsafe_tar(name):
    b=tar({"x":b"abc"},name)
    with pytest.raises(ValueError,match="TAR_UNSAFE"):q.safe_tar(b,q.sha(b))
def test_manifest_tamper():
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        for n,v in {"x":b"abc","SHA256SUMS":b"0000000000000000000000000000000000000000000000000000000000000000  x\n"}.items():
            m=tarfile.TarInfo(n);m.size=len(v);t.addfile(m,io.BytesIO(v))
    with pytest.raises(ValueError,match="MANIFEST_MISMATCH"):q.safe_tar(b.getvalue(),q.sha(b.getvalue()))
def test_freeze_identity_and_registry():
    assert len(q.SCENES)==20 and not any(s.startswith("L13") for s in q.SCENES)
    p=Path(q.__file__).with_name("qa06_a18_registry.json");assert q.sha(p.read_bytes())==q.REG18
def test_phase_source_fail():
    with pytest.raises(ValueError,match="OUTER_SET"):q.phase_check({}, {}, 1)
def test_hold_boundary():
    d=dict(human_approved=False,training_eligible=False,ground_truth="UNKNOWN_HOLD",rule_candidate="UNKNOWN")
    v=dict(d,production_contact_health="HOLD")
    q.hold_boundary(d,v)
    with pytest.raises(ValueError,match="GT_CONTACT_BOUNDARY"):q.hold_boundary(d,dict(v,human_approved=True))
def test_fingerprint_seed_invariance():
    ds=[dict(radius_m=.1,thickness_m=.03,mass_kg=.22,friction_mu=.65,x=0,y=0,z=.6)]
    assert q.fingerprint(ds)==q.fingerprint([dict(ds[0],seed=1,color="red")])
    assert q.fingerprint(ds)!=q.fingerprint([dict(ds[0],x=.001)])
def sample(i):
    return dict(evidence_id=str(i),scene_id=str(i),archive_sha256="a"*64,image_sha256="b"*64,observation="OTHER_OBSERVED",physical_layout_id="L"+str(i),geometry_family_id="F"+str(i//2),preprocess_224="PASS")
def approval(r,label):
    return dict(q.review_rows([r])[0],reviewer="fixture",reviewed_at="2026-11-26T00:00:00Z",initial_placement="PASS",rgb_observable="PASS",occlusion="PASS",physics_validity="PASS",learning_suitability="PASS",license_status="OWNED",license_basis="fixture only",decision=label,reason="synthetic contract")
def test_approval_blank_and_wrong_link():
    r=sample(0)
    with pytest.raises(ValueError,match="PENDING"):q.validate_approvals(q.review_rows([r]),[r])
    a=approval(r,"STABLE")
    with pytest.raises(ValueError,match="EVIDENCE_LINK"):q.validate_approvals([dict(a,image_sha256="c"*64)],[r])
    with pytest.raises(ValueError,match="RIGHTS_HOLD"):q.validate_approvals([dict(a,license_status="UNKNOWN")],[r])
    assert q.validate_approvals([a],[r])[0][0][1]["decision"]=="STABLE"
def test_family_split_and_near_hold():
    reg=[sample(i) for i in range(6)];valid=[(r,approval(r,"STABLE" if i%2==0 else "UNSTABLE")) for i,r in enumerate(reg)]
    m=q.family_split(valid,[],{});assert len(set(m.values()))==3
    p={"a":"0","b":"2","same_pixel":False,"same_file":False,"tray_ahash":0,"dish_ahash":9}
    with pytest.raises(ValueError,match="NEAR_PAIR"):q.family_split(valid,[p],{})
    with pytest.raises(ValueError,match="NO_INDEPENDENT_FAMILY_SPLIT"):q.family_split(valid,[p],{"0|2":{"decision":"SAME_SPLIT","reason":"fixture","reviewer":"fixture"}})
    with pytest.raises(ValueError,match="EXACT_DUPLICATE"):q.family_split(valid,[dict(p,same_pixel=True)],{})
def test_preprocess():
    b=io.BytesIO();Image.new("RGB",(640,480)).save(b,format="PNG")
    assert Image.open(io.BytesIO(q.preprocess(b.getvalue(),[100,100,500,400]))).size==(224,224)
    with pytest.raises(ValueError,match="CLIPPED"):q.preprocess(b.getvalue(),[0,100,500,400])
def test_sealed_tamper(tmp_path):
    p=tmp_path/"a";p.write_bytes(b"x");Path(str(p)+".sha256").write_text(q.sha(b"x")+"  a\n")
    assert q.side_verified(p)==b"x";p.write_bytes(b"y")
    with pytest.raises(ValueError,match="SHA"):q.side_verified(p)
def test_readiness_hold(tmp_path):
    q.readiness(tmp_path,"HOLD",["pending"]);assert json.loads((tmp_path/"c_training_readiness.json").read_text())["verdict"]=="NO_GO"
    assert json.loads((tmp_path/"e_integration_readiness.json").read_text())["verdict"]=="HOLD"
def test_missing_inputs_diagnostics_no_overwrite(tmp_path):
    pin="a"*40;reg=tmp_path/"inputs.json";reg.write_text(json.dumps({k:str(tmp_path/"missing") for k in q.PINS}));out=tmp_path/"out"
    args=["audit","--out-dir",str(out),"--verifier-sha",pin,"--input-registry",str(reg)]
    with patch.object(q.platform,"platform",return_value="fixture-linux"), patch.object(q.subprocess,"check_output",side_effect=[pin+"\n",""]):assert q.main(args)==2
    s=json.loads((out/"diagnostic_status.json").read_text());assert s["dataset_release"]=="HOLD" and s["first_error"] and len(s["input_receipt"])==9
    assert not (out/"dataset_v1").exists() and (out/"b_qa06_diagnostics.tar.gz.sha256").is_file()
    with pytest.raises(FileExistsError):q.main(args)

def test_near_pair_template_blank():
    rows=q.review_pair_template([{"a":"b","b":"a","tray_ahash":1,"dish_ahash":20},{"a":"a","b":"c","tray_ahash":9,"dish_ahash":9}])
    assert len(rows)==1 and rows[0]["pair_key"]=="a|b" and all(not rows[0][k] for k in ("decision","reviewer","reason"))
def test_release_positive_contract_fixture_only(tmp_path):
    # In-memory mock receipt only; no real candidate/approval/manifest is touched.
    root=tmp_path/"fixture";root.mkdir();out=tmp_path/"out";out.mkdir()
    reg=[];approvals=[]
    for i in range(6):
        r=sample(i);r.update(image_path=f"image{i}.png",physics_path=f"e{i}.tar.gz",dish_bbox=[100,100,500,400])
        Image.new("RGB",(640,480),(i*30,20,50)).save(root/r["image_path"])
        e=("synthetic review evidence "+str(i)).encode();(root/r["physics_path"]).write_bytes(e);r["archive_sha256"]=q.sha(e);r["image_sha256"]=q.sha((root/r["image_path"]).read_bytes())
        reg.append(r);approvals.append(approval(r,"STABLE" if i%2==0 else "UNSTABLE"))
    (root/"similarity_matrix.csv").write_text("a,b,same_pixel,same_file,tray_ahash,dish_ahash\n")
    a=tmp_path/"approval.jsonl";a.write_text("".join(json.dumps(x)+"\n" for x in approvals))
    Path(str(a)+".sha256").write_text(q.sha(a.read_bytes())+"  "+a.name+"\n")
    receipt="f"*64;pin="e"*40
    p=tmp_path/"policy.json";d={"receipt_sha256":receipt,"approval_sha256":q.sha(a.read_bytes()),"scope":q.SCOPE,"offline_pose_ecm_contact_exception":"ACCEPT_RESEARCH_ONLY_WITH_PRODUCTION_CONTACT_HOLD","diversity_risk_acceptance":{"decision":"APPROVE_RESEARCH_ONLY","reviewer":"fixture","reason":"fixture"}}
    d.update({k:{"decision":"APPROVE","reviewer":"fixture","reason":"fixture only"} for k in ("pm","b","c")})
    p.write_text(json.dumps(d));Path(str(p)+".sha256").write_text(q.sha(p.read_bytes())+"  "+p.name+"\n")
    with patch.object(q,"read_receipt",return_value=({"candidate_version":"fixture"},reg)):
        release=q.release(root,out,receipt,pin,a,p)
    ds=out/"dataset_v1";assert release["approved_count"]==6 and release["label_map"]=={"STABLE":0,"UNSTABLE":1}
    import csv
    rows=list(csv.DictReader((ds/"split_manifest.csv").open()))
    assert set(rows[0])==set(q.contract.SPLIT_FIELDS)
    assert {r["split"] for r in rows}==set(q.contract.SPLITS)
    assert all("STABLE" not in r["image_path"] and "UNSTABLE" not in r["image_path"] for r in rows)
    for s in q.contract.SPLITS:assert {r["label"] for r in rows if r["split"]==s}==set(q.contract.LABELS)
    out2=tmp_path/"readiness";out2.mkdir()
    q.verify_released(ds,q.sha((ds/"dataset_release.json").read_bytes()),pin,out2)
    assert json.loads((out2/"c_training_readiness.json").read_text())["verdict"]=="C_REVIEW_REQUIRED"
    assert json.loads((out2/"e_integration_readiness.json").read_text())["verdict"]=="HOLD"
    (ds/rows[0]["image_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError,match="RELEASE_ARTIFACT_DRIFT"):q.verify_released(ds,q.sha((ds/"dataset_release.json").read_bytes()),pin,out2)
def test_release_requires_approval(tmp_path):
    out=tmp_path/"out";out.mkdir()
    with patch.object(q,"read_receipt",return_value=({},[])):
        with pytest.raises(ValueError,match="HUMAN_APPROVAL_REQUIRED"):q.release(tmp_path,out,"f"*64,"a"*40,None,None)
    assert not (out/"dataset_v1").exists()
