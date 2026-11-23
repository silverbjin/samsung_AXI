"""S6 release: immutable pin, NO_GOAL, TTY required, no ROS dependencies."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'scripts/samsungaxi_s6_wsl2_l3_once.sh'
def test_s6_owner_no_goal_release():
    src=ENTRY.read_text()
    assert "SOURCE_SHA='937fbf025cefec01489c40bc5104c39e3d4709be'" in src
    assert 'SAMSUNGAXI_S6_VISION=1' in src
    assert '--s5-live --preflight-only' in src
    assert '--s5-live --perf-rgbd2 --approve-goals' in src
    assert 'YES-S5-LIVE-GOALS' in src
    assert '[[ ! -t 0 ]]' in src
    subprocess.run(['bash','-n',str(ENTRY)],check=True)
    probe=subprocess.run(['bash',str(ENTRY),'--self-test'],check=True,
                         text=True,capture_output=True)
    assert 'S6_L3_RELEASE_SELF_TEST_PASS_NO_GOAL' in probe.stdout
    blocked=subprocess.run(['bash',str(ENTRY)],input='',
                           text=True,capture_output=True)
    assert blocked.returncode==2
    assert 'S6_L3_BLOCKED_INTERACTIVE_TTY_REQUIRED_NO_GOAL' in blocked.stderr
