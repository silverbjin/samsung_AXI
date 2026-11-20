"""S5 Owner L0: actual shell RUN_ID preflight, no ROS or Gazebo."""
from pathlib import Path
import os,re,subprocess,zipfile

ROOT=Path(__file__).resolve().parents[1]
GUI=ROOT/'scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
OWNER=ROOT/'scripts/owner_wsl2_once.sh'
CORE=ROOT/'scripts/restaurant_demo.sh'
HELPER=ROOT/'scripts/s5_run_id_contract.sh'
PIN="a"*40

def invoke(tmp_path,*args,run_id=None):
    env=os.environ.copy()
    env.update(HOME=str(tmp_path),SAMSUNG_AXI_GUI_PIN=PIN,
               SAMSUNGAXI_S5_PREFLIGHT_REPO=str(ROOT))
    env.pop('SAMSUNGAXI_S5_RUN_ID',None)
    if run_id is not None:env['SAMSUNGAXI_S5_RUN_ID']=run_id
    return subprocess.run(['bash',str(GUI),*args],env=env,stdin=subprocess.DEVNULL,
                          capture_output=True,text=True,timeout=20)

def bundle(path):
    files=list((path/'samsungaxi_gui_evidence').glob('*.zip'))
    assert len(files)==1,files
    with zipfile.ZipFile(files[0]) as z:
        return {name:z.read(name).decode(errors='replace') for name in z.namelist()}

def test_b01_auto_id_through_full_chain(tmp_path):
    p=invoke(tmp_path,'--s5-live','--preflight-only')
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'S5_RUN_ID_CONTRACT_PASS' in p.stdout
    assert 'S5_OWNER_PREFLIGHT_PASS_NO_GOAL' in p.stdout
    assert 'S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL' in p.stdout
    b=bundle(tmp_path)
    rid=re.search(r'^S5_RUN_ID=([A-Za-z0-9_-]+)$',b['status.txt'],re.M)
    assert rid,b['status.txt']
    assert rid.group(1) in b['run.log']
    assert 'GOAL_SENT=FALSE' in b['status.txt']
    assert 'VERDICT=PREFLIGHT_PASS_NO_GOAL' in b['status.txt']

def test_b02_valid_external_id(tmp_path):
    rid='s5_20261120T044231Z_3756'
    p=invoke(tmp_path,'--s5-live','--preflight-only',run_id=rid)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'S5_RUN_ID='+rid in bundle(tmp_path)['status.txt']

def test_b03_invalid_id_zip_first_failure(tmp_path):
    for i,bad in enumerate(['20261120T044231Z-$','bad/name','bad name']):
        d=tmp_path/str(i)
        p=invoke(d,'--s5-live','--preflight-only',run_id=bad)
        assert p.returncode==2,(bad,p.stdout,p.stderr)
        b=bundle(d)
        assert 'S5_BLOCKED_INVALID_RUN_ID' in b['run.log']
        assert 'S5_BLOCKED_INVALID_RUN_ID' in b['error_clues.txt']
        assert 'FIRST_FAILED_PHASE=OWNER_PRELAUNCH' in b['status.txt']
        assert 'FIRST_FAILED_MARKER=S5_BLOCKED_INVALID_RUN_ID' in b['status.txt']
        assert 'GOAL_AUTHORIZED=FALSE' in b['status.txt']
        assert 'GOAL_SENT=FALSE' in b['status.txt']
        assert 'DIAGNOSTIC_ZIP=' in b['status.txt']

def test_b04_owner_core_preflight_no_ros():
    env=os.environ.copy()
    env['SAMSUNGAXI_S5_RUN_ID']='s5_20261120T044231Z_3756'
    p=subprocess.run(['bash',str(OWNER),'live','NORMAL','--preflight-only',
                      '--ref',PIN,'--workspace',str(ROOT)],env=env,
                     capture_output=True,text=True,timeout=10)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'S5_OWNER_PREFLIGHT_PASS_NO_GOAL' in p.stdout
    assert 'S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL' in p.stdout

def test_b05_cli_approval_and_terminal_without_ros(tmp_path):
    no=invoke(tmp_path,'--s5-live')
    assert no.returncode==2
    assert 'S5_BLOCKED_REQUIRES_EXPLICIT_PIN_AND_APPROVE_GOALS' in no.stdout
    tty=invoke(tmp_path/'tty','--s5-live','--approve-goals')
    assert tty.returncode==2
    assert 'S5_BLOCKED_OWNER_TERMINAL_REQUIRED' in tty.stdout
    safe=invoke(tmp_path/'safe','--s5-live','--preflight-only',run_id='safe_1')
    assert safe.returncode==0
    assert 'GOAL_SENT=FALSE' in bundle(tmp_path/'safe')['status.txt']

def test_bash_contract_shared_not_relaxed():
    for p in (GUI,OWNER,CORE):
        subprocess.run(['bash','-n',str(p)],check=True)
    assert HELPER.is_file()
    src=HELPER.read_text()
    assert '^[A-Za-z0-9_-]+$' in src
    assert 'S5_BLOCKED_INVALID_RUN_ID' in src
    for p in (GUI,OWNER,CORE):
        assert 's5_run_id_contract.sh' in p.read_text()


def test_b06_core_fallback_pid_in_same_shared_contract():
    # Direct entry without the wrapper is still safe and uses a real Bash PID.
    env=os.environ.copy()
    env.pop('SAMSUNGAXI_S5_RUN_ID',None)
    p=subprocess.run(['bash',str(CORE),'live','NORMAL','--preflight-only'],
                     env=env,capture_output=True,text=True,timeout=10)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'S5_OWNER_CORE_PREFLIGHT_PASS_NO_GOAL' in p.stdout
    assert re.search(r'S5_RUN_ID=\d{8}T\d{6}Z-\d+',p.stdout)
