"""Legacy S6 initial entry must never launch obsolete pre-G09 code."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'scripts/samsungaxi_s6_wsl2_l3_once.sh'
NEW=ROOT/'scripts/samsungaxi_s6_wslg_reaccept_once.sh'
def test_legacy_entry_retired_fail_closed():
    body=OLD.read_text()
    assert 'S6_LEGACY_ENTRY_RETIRED_NO_GOAL' in body
    assert '937fbf025cefec01489c40bc5104c39e3d4709be' not in body
    assert 'S6_OFFICIAL_OWNER_ENTRY_KO.md' in body
    assert 'ros2' not in body and 'YES-S5-LIVE-GOALS' not in body
    subprocess.run(['bash','-n',str(OLD)],check=True)
    test=subprocess.run(['bash',str(OLD),'--self-test'],capture_output=True,text=True)
    assert test.returncode==0 and 'S6_LEGACY_ENTRY_RETIRED_SELF_TEST_PASS_NO_GOAL' in test.stdout
    for args in ([],['--approve-goals'],['--diagnose-only']):
        blocked=subprocess.run(['bash',str(OLD),*args],capture_output=True,text=True,input='')
        assert blocked.returncode==2
        assert 'S6_LEGACY_ENTRY_RETIRED_NO_GOAL' in blocked.stderr
def test_canonical_source_pin_kept_immutable():
    body=NEW.read_text()
    assert "SOURCE_SHA='9d402a991d1ee0a1c46027abe91a55266b69d9bd'" in body
    assert '--preflight-only' in body and '--approve-goals' in body
    assert 'S6_WSLG_BLOCKED_TTY_REQUIRED_NO_GOAL' in body
