"""G08: negative verdict never promotes Action ABORTED to PASS."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s6_abort',ROOT/'scripts/s6_nav2_return_abort_classifier.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def test_follow_path_timeout_keeps_abort():
    evidence={'nav2_goal_failure':{
        'goal_label':'PICKUP_RETURN','action_status':6,
        'nav2_error_code':0,'nav2_error_msg':None,
        'amcl_goal_error_m':.3774,
        'scan_age_sec':.131,'odom_age_sec':.068,
        'last_feedback':{'distance_remaining_m':.419},
        'physical_odom_max_displacement_m':4.8596
    }}
    d=m.classify(evidence,
         '[bt_navigator] Timed out while waiting for action server to acknowledge goal request for follow_path')
    assert d['first_failure']=='S6_RETURN_FOLLOW_PATH_ACK_TIMEOUT'
    assert d['nav2_return_succeeded'] is False
    assert d['root_cause']=='NOT_CONFIRMED_FROM_BOUNDED_SUMMARY'
    assert d['sensor_fresh'] is True
    assert d['goal_error_m']==.3774
def test_unknown_abort_does_not_guess_origin():
    d=m.classify({'nav2_goal_failure':{'action_status':6}},'')
    assert d['first_failure']=='S6_NAV2_ABORT_UNCLASSIFIED'
    assert d['nav2_return_succeeded'] is False
