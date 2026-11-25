"""L0 contract fixtures ONLY. Never real physics evidence."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from a14_production_health_contract import assess

STEP = 1_000_000
TOPICS = ['/smartdish/tray/contact/tray_platform', '/smartdish/tray/contact/tray_test_floor']
EXPECT = {t: {'model': t.rsplit('/',1)[1], 'sensor': 'a14_contact', 'collision': 'collision'} for t in TOPICS}

def fixture():
    rows = []
    ros = []
    clocks = [n*STEP for n in range(1, 6)]
    for n in range(1, 6):
        for k,t in enumerate(TOPICS):
            pairs = [[20,30]] if k == 0 else []
            rows.append(dict(topic=t, **EXPECT[t], sim_ns=n*STEP, iteration=n,
                             dt_ns=STEP, sensor_id=10+k, collision_id=20+k,
                             present=True, count=len(pairs), pairs=pairs,
                             source='GAZEBO_POSTUPDATE_ECM_SNAPSHOT'))
            if pairs:
                ros.append(dict(topic=t, sim_ns=n*STEP, pairs=pairs,
                                source='ROS_CONTACT_HEADER_STAMP'))
    return rows, ros, clocks

def run(rows=None, ros=None, clocks=None, **kw):
    a,b,c=fixture()
    return assess(EXPECT, a if rows is None else rows, b if ros is None else ros,
                  c if clocks is None else clocks, STEP, 5*STEP, STEP,
                  discovered=kw.pop('discovered', dict.fromkeys(TOPICS,1)), **kw)

def test_complete_snapshot_and_positive_transport_but_silence_hold():
    r=run()
    assert r['diagnostic_capture_pass']
    assert r['sensors'][TOPICS[0]]['matched_positive_steps']==5
    assert r['sensors'][TOPICS[1]]['snapshot_coverage_pass']
    assert r['sensors'][TOPICS[1]]['status']=='ECM_EMPTY_FRESHNESS_UNPROVEN'
    assert r['production_contact_health']=='HOLD'
    assert r['rule_candidate']=='UNKNOWN' and not r['human_approved']
    assert r['ground_truth']=='NOT_OPERATOR_APPROVED'

@pytest.mark.parametrize('kind', ['missing_topic','missing_step','id_change','missing_component',
                                  'wrong_model','wrong_sensor','wrong_collision','fake_source',
                                  'bad_count','wrong_pair_id','dt_wrong','duplicate_step','iteration_jump'])
def test_invalid_snapshot_holds(kind):
    a,b,c=fixture()
    if kind=='missing_topic': a=[x for x in a if x['topic']==TOPICS[1]]
    elif kind=='missing_step': del a[4]
    elif kind=='id_change': a[4]['sensor_id']=999
    elif kind=='missing_component': a[4]['present']=False
    elif kind=='wrong_model': a[4]['model']='other'
    elif kind=='wrong_sensor': a[4]['sensor']='other'
    elif kind=='wrong_collision': a[4]['collision']='other'
    elif kind=='fake_source': a[4]['source']='SYNTHETIC_HEARTBEAT'
    elif kind=='bad_count': a[4]['count']=0
    elif kind=='wrong_pair_id': a[4]['pairs']=[[99,30]]
    elif kind=='dt_wrong': a[4]['dt_ns']=2*STEP
    elif kind=='duplicate_step': a.insert(4,copy.deepcopy(a[4]))
    elif kind=='iteration_jump': a[4]['iteration']+=9
    r=run(a,b,c)
    assert not r['diagnostic_capture_pass'] and r['production_contact_health']=='HOLD'

@pytest.mark.parametrize('clock', [[STEP]*5, [STEP,3*STEP,2*STEP,5*STEP], [2*STEP,3*STEP,4*STEP]])
def test_clock_stall_regression_or_truncated(clock):
    assert not run(clocks=clock)['diagnostic_capture_pass']

def test_bridge_discovered_but_no_data():
    r=run(ros=[])
    assert not r['diagnostic_capture_pass']
    assert r['sensors'][TOPICS[0]]['status']=='ECM_POSITIVE_ROS_UNMATCHED'

def test_bridge_not_discovered():
    assert not run(discovered={TOPICS[0]:1})['diagnostic_capture_pass']

def test_wrong_stamp_pair_or_source_cannot_match():
    a,b,c=fixture()
    for x in b: x['pairs']=[[20,999]]
    assert not run(a,b,c)['diagnostic_capture_pass']
    for x in b: x['pairs']=[[20,30]]; x['source']='SYNTHETIC'
    assert not run(a,b,c)['diagnostic_capture_pass']

def test_overflow_holds_even_with_valid_fixture():
    assert not run(overflow=True)['diagnostic_capture_pass']

def test_separate_positive_calibration_cannot_fill_silent_channel():
    a,b,c=fixture()
    b.append(dict(topic='/smartdish/a14/calibration/contact/floor',sim_ns=3*STEP,
                  pairs=[[21,30]],source='ROS_CONTACT_HEADER_STAMP'))
    r=run(a,b,c)
    assert r['sensors'][TOPICS[1]]['status']=='ECM_EMPTY_FRESHNESS_UNPROVEN'
    assert r['production_contact_health']=='HOLD'
