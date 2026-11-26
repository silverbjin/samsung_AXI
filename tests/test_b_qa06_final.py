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
    with patch.object(q.subprocess,"check_output",side_effect=[pin+"\n",""]):assert q.main(args)==2
    s=json.loads((out/"diagnostic_status.json").read_text());assert s["dataset_release"]=="HOLD" and s["first_error"] and len(s["input_receipt"])==9
    assert not (out/"dataset_v1").exists() and (out/"b_qa06_diagnostics.tar.gz.sha256").is_file()
    with pytest.raises(FileExistsError):q.main(args)
