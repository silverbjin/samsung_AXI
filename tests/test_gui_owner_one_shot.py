"""Owner GUI one-shot static, self-test and fail-closed ZIP contract."""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OWNER=ROOT/'scripts'/'samsungaxi_wsl2_gui_acceptance_once.sh'

def test_gui_owner_syntax_and_no_goal_self_test():
    subprocess.run(['bash','-n',str(OWNER)],check=True)
    completed=subprocess.run(['bash',str(OWNER),'--self-test'],capture_output=True,text=True,check=True,timeout=10)
    assert 'SAMSUNGAXI_GUI_STATIC_PASS_NO_GOAL' in completed.stdout

def test_gui_owner_is_pinned_and_never_maps_or_sends_goals():
    src=OWNER.read_text()
    assert 'f39dc1757588b9f7cde1a56f73659f629c57e703' in src
    assert '"$OWNER" navigation NORMAL' in src
    assert 'NO_GOAL' in src
    assert 'pkill' not in src and 'killall' not in src
    assert 'python3 - <<' in src
    assert 'SAMSUNGAXI_DIAGNOSTIC_ZIP=' in src

def test_invalid_cli_fails_before_launch():
    result=subprocess.run(['bash',str(OWNER),'--bogus'],capture_output=True,text=True,timeout=10)
    assert result.returncode == 2

def test_auto_pose_opt_in_and_gui_only():
    p=(ROOT/'scripts'/'prepare_nav2_params.py').read_text()
    assert "auto_initial_pose=False" in p
    assert "amcl['set_initial_pose']=True" in p
    assert "--auto-initial-pose" in p
    runner=(ROOT/'scripts'/'restaurant_demo.sh').read_text()
    assert "NAV_AUTO_ARGS=(--auto-initial-pose)" in runner
    assert "S2_MAP03_CANDIDATE_81PCT" in runner
    assert "NO GOAL acceptance must never fall through" in runner
    smoke=(ROOT/'scripts'/'ci_s3_amcl_smoke.py').read_text()
    assert "not args.no_initial_pose_publish and now-last_publish" in smoke
    assert "S3_AMCL_AUTO_INITIAL_POSE_REAL_GAZEBO_PASS_NO_MANUAL_PUBLISH" in smoke
