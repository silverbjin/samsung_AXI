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
def test_missing_image_fails():
    with pytest.raises(KeyError):q.adapt({},"a15","L15-01","x")
def test_failure_diagnostic_and_no_overwrite(tmp_path):
    pin="a"*40
    args=["--a15",str(tmp_path/"missing"),"--a16",str(tmp_path/"missing"),"--a16-diag",str(tmp_path/"missing"),"--qa04",str(tmp_path/"missing"),"--out-dir",str(tmp_path/"out"),"--verifier-sha",pin]
    with patch.object(cli.subprocess,"check_output",side_effect=[pin+"\n",""]):
        assert cli.main(args)==2
    out=tmp_path/"out";r=json.loads((out/"qa05_report.json").read_text())
    assert not r["actual_12_scene_roi_review"] and r["approved_count"]==0 and not r["training_eligible"] and r["production_contact_health"]=="HOLD" and r["cleanup"]=="FAIL"
    assert not (out/"approval_ledger.jsonl").exists() and not (out/"train_manifest.csv").exists()
    a=out/"b_qa05_diagnostics.tar.gz";assert hashlib.sha256(a.read_bytes()).hexdigest() in Path(str(a)+".sha256").read_text()
    with tarfile.open(a) as t:assert set(t.getnames())=={"qa05_report.json","diagnostic_status.json","SHA256SUMS"}
    with pytest.raises(FileExistsError):cli.main(args)
