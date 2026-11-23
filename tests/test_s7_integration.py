"""S7 real startup integration static and single immutable SHA owner."""
from pathlib import Path
import os
import subprocess
ROOT=Path(__file__).resolve().parents[1]
def txt(path):return (ROOT/path).read_text()
def test_optin_s7_routes_world_without_double_spawn():
    c=txt('scripts/ci_s3_amcl_smoke.py')
    assert "nav_cmd.append('world_file:='+str(args.s7_world.resolve()))" in c
    assert "args.s7_scenario=='stacked'" in c
    assert "result['s7_scene']" in c
    assert "args.s6_scene_fixture" in c
    r=txt('scripts/restaurant_demo.sh')
    assert 'S7_STARTUP_SCENARIO=' in r
    assert 'S7_REQUIRES_EXPLICIT_S6_VISION_NO_GOAL' in r
    assert '--s7-world "$S7_WORLD"' in r
    assert '--s6-scene-fixture' in r
    h=txt('scripts/s5_ci_delayed_tty.py')
    assert "cmd.append('--s6-scene-fixture')" in h
    assert 'args.s7_scenario' in h
def test_single_sha_and_real_tty_entry():
    entry=ROOT/'scripts/samsungaxi_s7_wsl2_l3_once.sh'
    src=entry.read_text()
    assert 'SAMSUNGAXI_S7_SOURCE_SHA' in src
    assert 'S7_OWNER_PREFLIGHT_PASS_NO_GOAL' in src
    assert 'SAMSUNGAXI_S7_SCENARIO=stacked' in src
    assert '[[ -t 0 ]]' in src
    assert '--s5-live --perf-rgbd2 --approve-goals' in src
    subprocess.run(['bash','-n',str(entry)],check=True)
    p=subprocess.run(['bash',str(entry)],capture_output=True,text=True)
    assert p.returncode==2 and 'S7_BLOCKED_MISSING_IMMUTABLE_SHA_NO_GOAL' in p.stderr
    env=dict(os.environ,SAMSUNGAXI_S7_SOURCE_SHA='9d402a991d1ee0a1c46027abe91a55266b69d9bd')
    p=subprocess.run(['bash',str(entry),'--self-test'],capture_output=True,text=True,env=env)
    assert p.returncode==0 and 'S7_OWNER_SELF_TEST_PASS_NO_GOAL' in p.stdout
    p=subprocess.run(['bash',str(entry)],input='',capture_output=True,text=True,env=env)
    assert p.returncode==2 and 'S7_BLOCKED_REAL_TTY_REQUIRED_NO_GOAL' in p.stderr
