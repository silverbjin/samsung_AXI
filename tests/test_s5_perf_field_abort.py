"""S5 field Nav2 abort evidence, no ROS/Gazebo needed for L0 tests."""
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from s5_nav_abort_evidence import nav_abort_snapshot


def test_aborted_goal_is_reported_as_sent_and_captures_action_result():
    state={'scan':41,'scan_t':198.7,'odom_t':199.0,
           'amcl_pose':(2.0,0.2),'odom_track':[(0.,0.),(2.2,0.)]}
    result=SimpleNamespace(error_code=212,error_msg='Controller failed to make progress')
    snap=nav_abort_snapshot(label='TABLE_3',status=6,action_result=result,
                            state=state,start_odom=(0.,0.),before_track=0,
                            goal_target=(5.25,0.38),now=200.0,goal_elapsed=50.,
                            last_feedback={'distance_remaining_m':3.0,
                                           'number_of_recoveries':2})
    assert snap['goal_sent'] is True
    assert snap['action_status']==6
    assert snap['nav2_error_code']==212
    assert snap['nav2_error_msg']=='Controller failed to make progress'
    assert snap['goal_label']=='TABLE_3'
    assert snap['elapsed_wall_sec']==50.
    assert snap['physical_odom_max_displacement_m']>=2.2
    assert snap['scan_age_sec']==1.3
    assert snap['odom_age_sec']==1.
    assert snap['last_feedback']['number_of_recoveries']==2


def test_missing_nav2_details_are_unknown_not_guessed():
    state={'scan':2,'scan_t':0.,'odom_t':0.,'amcl_pose':None,'odom_track':[]}
    snap=nav_abort_snapshot(label='PICKUP_RETURN',status=6,action_result=object(),
                            state=state,start_odom=None,before_track=0,
                            goal_target=(0.,0.),now=4.,goal_elapsed=3.,
                            last_feedback={})
    assert snap['nav2_error_code'] is None
    assert snap['nav2_error_msg'] is None
    assert snap['physical_odom_max_displacement_m'] is None
    assert snap['goal_sent'] is True


def test_existing_nav2_action_and_safety_thresholds_remain():
    source=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert "response.status!=GoalStatus.STATUS_SUCCEEDED" in source
    assert 'nav_abort_snapshot(' in source
    assert "result['goal_sent']=True" in source
    assert "time.monotonic()-state['scan_t']>8 or time.monotonic()-state['odom_t']>8" in source
    assert "time.monotonic()-state['scan_t']>10 or time.monotonic()-state['odom_t']>10" in source
    assert 'perform_s4_stop(result)' in source


def test_ci_runs_same_baseline_5hz_with_active_perf_collector():
    wf=(ROOT/'.github/workflows/restaurant-s5-perf-field-parity-ci.yml').read_text()
    assert 'scripts/s5_perf_profile.py' in wf
    assert 'scripts/s5_ci_delayed_tty.py' in wf
    assert '--approval-delay-sec 12' in wf
    assert '--mode baseline' in wf
    assert "s5_perf_baseline_real_gazebo.log" in wf
    assert 'S5_PERF_PROFILED_BASELINE_REAL_GAZEBO_L2_PASS' in wf
    assert 'S5_PERF_BASELINE_RTF_SAMPLE_PRESENCE_PASS' in wf
    assert "S5_PERF_ROOT_CAUSE_RTF_90_FIELD_VERIFIED" not in wf
