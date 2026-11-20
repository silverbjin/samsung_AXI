"""S5-LIVE-01 fail-closed static contract, no ROS or Gazebo required."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OWNER=ROOT/'scripts/owner_wsl2_once.sh'
GUI=ROOT/'scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
CORE=ROOT/'scripts/restaurant_demo.sh'
SMOKE=ROOT/'scripts/ci_s3_amcl_smoke.py'

def test_owner_live_requires_explicit_goal_approval():
    for p in (OWNER,GUI,CORE):
        subprocess.run(['bash','-n',str(p)],check=True)
    no=subprocess.run(['bash',str(OWNER),'live','NORMAL','--self-test','--ref','a'*40],
                      capture_output=True,text=True,timeout=10)
    assert no.returncode==2
    assert 'S5_LIVE_BLOCKED_GOALS_APPROVAL_REQUIRED' in no.stderr
    yes=subprocess.run(['bash',str(OWNER),'live','NORMAL','--self-test',
                        '--ref','a'*40,'--goals-approved'],
                       capture_output=True,text=True,timeout=10)
    assert yes.returncode==0
    assert 'PASS_NO_ROS_NO_GOAL' in yes.stdout
    gui_no=subprocess.run(['bash',str(GUI),'--s5-live','--approve-goals'],
                          capture_output=True,text=True,timeout=10)
    assert gui_no.returncode==2
    assert 'S5_BLOCKED_REQUIRES_EXPLICIT_PIN_AND_APPROVE_GOALS' in gui_no.stdout
    gui_wrong=subprocess.run(['bash',str(GUI),'--approve-goals'],
                             capture_output=True,text=True,timeout=10)
    assert gui_wrong.returncode==2

def test_s5_uses_proven_map_amcl_nav_and_cm_in_one_session():
    s=CORE.read_text();p=SMOKE.read_text()
    assert '"$MODE" == navigation || "$MODE" == live' in s
    assert 'validate_s2_map03_candidate' in s
    assert 'NAV_AUTO_ARGS=(--auto-initial-pose)' in s
    assert '--exercise-goals --menu-safety --no-initial-pose-publish' in s
    assert '--s5-integrated --gui --live-owner' in s
    assert 'S5_REQUIRES_CUSTODY_VERIFIED_S2_MAP03' in p
    assert 'S5_OWNER_GOAL_CONFIRMATION_MISSING' in (ROOT/'scripts/s5_owner_approval.py').read_text()
    assert 'S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS' in p
    assert 'S5_INTEGRATED_EVIDENCE_INCOMPLETE' in p
    assert 'perform_s4_stop(result)' in p
    assert 'S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS' in p
    assert 'while True:spin_once(.25)' in p

def test_s5_never_bypasses_one_zip_or_writes_direct_motor_commands():
    s=CORE.read_text();w=GUI.read_text()
    assert 'SAMSUNGAXI_S5_GOALS_APPROVED' in s
    assert 'SAMSUNGAXI_DIAGNOSTIC_ZIP=' in w
    assert 's5_live_evidence.json' in w
    assert 'SAMSUNGAXI_S5_RUN_ID' in w
    assert '</dev/tty &' in w
    assert 'S5_BLOCKED_OWNER_TERMINAL_REQUIRED' in w
    assert 'S5_EVIDENCE_DIR' in s
    assert 'setsid bash "$OWNER"' in w
    assert 'pkill' not in w and 'killall' not in w
    assert 'ros2 run slam_toolbox' not in s
    assert '/cmd_vel' not in s

def test_s5_ci_physical_source_and_green_evidence_contract():
    w=(ROOT/'.github/workflows/restaurant-s5-live-ci.yml').read_text()
    assert '--s5-integrated --exercise-goals --menu-safety --no-initial-pose-publish' in w
    assert 'maps/candidates/s2_map03/restaurant_map.yaml' in w
    assert '--auto-initial-pose' in w
    assert 'S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS' in w
    assert w.count('scripts/ci_s3_amcl_smoke.py')==1
    assert 'actions/upload-artifact@v4' in w
