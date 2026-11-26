import sys,io,tarfile,hashlib
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from a14_r03_dbg_review import classify,unpack_verified,review
def fixture(error=True,server=0,stopped=True):
    e="A13_GAZEBO_GUI_EARLY_EXIT_RC=-6" if error else None
    s=dict(first_error=e,verdict="FAIL" if error else "GAZEBO_TRAY_L2_PHYSICS_AND_CAMERA_PASS")
    t=dict(sensor_physics_verdict="PASS",gui_verdict="FAIL" if error else "PASS",gui_failure_reason=e)
    c=dict(all_owned_processes_stopped=stopped,owned_processes=[
        dict(pid=3,stopped=True,returncode_after_cleanup=-6 if error else 0),
        dict(pid=2,stopped=True,returncode_after_cleanup=0),
        dict(pid=1,stopped=stopped,returncode_after_cleanup=server)])
    d=dict(stage="evidence_verification",first_error="RuntimeError: "+str(e),
           owned_processes_before_cleanup=[dict(pid=1,running_at_failure=True),
               dict(pid=3,running_at_failure=False,returncode_at_failure=-6)]) if error else None
    return s,t,c,d,{1:"server",2:"aux",3:"gui"}
def test_normal(): assert classify(*fixture(False))["cleanup"]=="PASS"
def test_gui_only():
    r=classify(*fixture());assert r["gui"]=="FAIL" and r["data_verdict"]=="PASS" and r["cleanup"]=="PASS"
def test_server_cleanup_crash():
    r=classify(*fixture(server=-11));assert r["data_verdict"]=="PASS" and r["cleanup"]=="FAIL" and r["overall"]=="HOLD_CLEANUP"
def test_unstopped(): assert not classify(*fixture(stopped=False))["next_independent_scene_allowed"]
@pytest.mark.parametrize("kind",["startup","rgb","physics","server","wrong_rc","wrong_phase","wrong_role"])
def test_fail_closed(kind):
    s,t,c,d,roles=fixture()
    if kind=="startup":s["first_error"]="A13_GAZEBO_GUI_START_FAILED_RC=-6"
    if kind=="rgb":s["first_error"]="A13_GUI_ACTIVE_BUT_NO_LIVE_RGB_FRAMES"
    if kind=="physics":t["sensor_physics_verdict"]="HOLD"
    if kind=="server":d["owned_processes_before_cleanup"][0]["running_at_failure"]=False
    if kind=="wrong_rc":c["owned_processes"][0]["returncode_after_cleanup"]=-11
    if kind=="wrong_phase":d["stage"]="physics_observation"
    if kind=="wrong_role":roles={1:"gui",2:"aux",3:"server"}
    with pytest.raises(ValueError):classify(s,t,c,d,roles)
def make_tar(path,items):
    with tarfile.open(path,"w:gz") as t:
        for n,b in items:
            m=tarfile.TarInfo(n);m.size=len(b);t.addfile(m,io.BytesIO(b))
def test_archive(tmp_path):
    a=tmp_path/"raw.tar.gz"; out=tmp_path/"out";out.mkdir()
    b=b"raw"; h=hashlib.sha256(b).hexdigest()
    make_tar(a,[("raw",b),("SHA256SUMS",(h+"  raw\n").encode())])
    assert unpack_verified(a,out)==1
@pytest.mark.parametrize("kind",["traversal","duplicate","bad_hash","unlisted"])
def test_archive_reject(tmp_path,kind):
    a=tmp_path/"raw.tar.gz";out=tmp_path/"out";out.mkdir()
    b=b"raw"; h=hashlib.sha256(b).hexdigest()
    items=[("raw",b),("SHA256SUMS",(h+"  raw\n").encode())]
    if kind=="traversal":items.append(("../outside",b))
    if kind=="duplicate":items.append(("raw",b))
    if kind=="bad_hash":items[0]=("raw",b"tampered")
    if kind=="unlisted":items.append(("extra",b))
    make_tar(a,items)
    with pytest.raises(ValueError):unpack_verified(a,out)
def test_reuse_cannot_relabel(tmp_path):
    p=tmp_path/"fake";p.write_bytes(b"fake")
    with pytest.raises(ValueError,match="REUSE_PIN_OR_HASH"):
        review(p,"a"*40,"ST-02","b"*40,reuse=True)
