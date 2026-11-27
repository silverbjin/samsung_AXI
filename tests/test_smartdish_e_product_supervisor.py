import json,os,signal,subprocess,sys,time,uuid
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from smartdish_e_product_supervisor import ENV,phase_timeout,owned,cleanup,token

def test_startup_phase_budget(tmp_path):
    p=tmp_path/"phase.json"
    assert phase_timeout(p,100.) is None
    p.write_text(json.dumps(dict(stage="CAPTURE_NODE_BEGIN",initializing=True,steady_s=10.)))
    assert phase_timeout(p,54.99) is None
    assert phase_timeout(p,55.)=="CAPTURE_NODE_BEGIN"
    p.write_text(json.dumps(dict(stage="INIT_COMPLETE",initializing=False,steady_s=10.)))
    assert phase_timeout(p,999.) is None

def test_scoped_cleanup_does_not_touch_unrelated():
    value="test-"+uuid.uuid4().hex
    env=os.environ|{ENV:value}
    # An inherited token survives start_new_session; the old outer timeout missed that group.
    owned_proc=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],env=env,start_new_session=True,stderr=subprocess.DEVNULL)
    other=subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],start_new_session=True)
    try:
        until=time.monotonic()+2
        while owned_proc.pid not in owned(value) and time.monotonic()<until:time.sleep(.02)
        assert owned_proc.pid in owned(value) and other.pid not in owned(value)
        r=cleanup(value)
        assert owned_proc.pid in r["before"] and not r["remaining"] and not r["clean"]
        owned_proc.wait(timeout=3)
        assert other.poll() is None
        assert cleanup(value)["clean"]
    finally:
        for p in (owned_proc,other):
            if p.poll() is None:p.kill()
            p.wait(timeout=3)

def test_ci_scope(monkeypatch):
    monkeypatch.setenv("CI","true")
    monkeypatch.setenv("GITHUB_ACTIONS","true")
    monkeypatch.setenv("GZ_PARTITION","smartdish_a04_e_test")
    monkeypatch.setenv("GITHUB_RUN_ID","1")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT","2")
    monkeypatch.delenv("WSL_DISTRO_NAME",raising=False)
    assert token()=="smartdish-e-1-2"
    monkeypatch.setenv("WSL_DISTRO_NAME","Ubuntu")
    with pytest.raises(RuntimeError,match="CI_ONLY"):token()
