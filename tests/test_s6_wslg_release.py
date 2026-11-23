"""G06 release: one block never sends a Goal with no TTY; diagnostics NO_GOAL."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
F=ROOT/'scripts/samsungaxi_s6_wslg_reaccept_once.sh'
def test_release_pin_and_safety():
    src=F.read_text()
    assert "SOURCE_SHA='611ac7b9edf5aa275dc4dbbde86530a573165a77'" in src
    assert 'SAMSUNGAXI_S6_VISION=1' in src
    assert '--s5-live --preflight-only' in src
    assert '--s5-live --perf-rgbd2 --approve-goals' in src
    assert 'YES-S5-LIVE-GOALS' in src
    assert '[[ ! -t 0 ]]' in src
    assert '--diagnose-only' in src
    subprocess.run(['bash','-n',str(F)],check=True)
    p=subprocess.run(['bash',str(F),'--self-test'],capture_output=True,text=True,check=True)
    assert 'S6_WSLG_REACCEPT_SELF_TEST_PASS_NO_GOAL' in p.stdout
    p=subprocess.run(['bash',str(F)],input='',capture_output=True,text=True)
    assert p.returncode==2 and 'S6_WSLG_BLOCKED_TTY_REQUIRED_NO_GOAL' in p.stderr
    # Diagnosis path never goes through the live Owner entry, even if online.
    assert src.index('if (( DIAG )); then')<src.index('SAMSUNG_AXI_GUI_PIN')
