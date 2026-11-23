"""S6-FLOW-01: return Goal cannot be sent on any ambiguous condition."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('flow',ROOT/'scripts/s6_flow_contract.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
GOOD={'result':'STACKED','reason':'REAL_RGB_MODEL_INFERENCE','confidence':.91}
def test_positive_flow_requires_explicit_verified_stages():
    a=m.next_state('NAV_TO_TABLE','GOAL_SUCCEEDED_AND_STOPPED')
    b=m.next_state(a,'IMAGE_SUBSCRIPTION_STARTED')
    c=m.next_state(b,'CLASSIFIED')
    d=m.next_state(c,'AUTHORIZE_RETURN',GOOD)
    assert (a,b,c,d)==('ARRIVAL_SETTLED','VISION_REQUESTED','VISION_RESULT','NAV_RETURN')
    assert m.next_state(d,'RETURN_GOAL_SUCCEEDED')=='RETURNED'
def test_negative_or_unknown_never_leads_to_return():
    assert m.next_state('NAV_TO_TABLE','ACTION_ABORTED')=='HOLD'
    assert m.next_state('ARRIVAL_SETTLED','TIMEOUT')=='HOLD'
    assert m.next_state('VISION_REQUESTED','IMAGE_STALE')=='HOLD'
    for result in ('NOT_STACKED','UNKNOWN'):
        assert m.next_state('VISION_RESULT','AUTHORIZE_RETURN',
            {'result':result,'reason':'REAL_RGB_MODEL_INFERENCE','confidence':1})=='HOLD'
    assert m.next_state('VISION_RESULT','AUTHORIZE_RETURN',
        {'result':'STACKED','reason':'MOCK_INJECTION','confidence':1})=='HOLD'
    assert m.next_state('VISION_RESULT','AUTHORIZE_RETURN',
        {'result':'STACKED','reason':'REAL_RGB_MODEL_INFERENCE','confidence':.4})=='HOLD'
    assert m.next_state('HOLD','AUTHORIZE_RETURN',GOOD)=='HOLD'
def test_actual_s5_script_is_not_implicitly_changed_to_vision():
    s=(ROOT/'scripts/restaurant_demo.sh').read_text()
    assert 'SAMSUNGAXI_S6_VISION' not in s or 'SAMSUNGAXI_S6_VISION:-0' in s
    test=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    # S6 must have separate opt-in flag; never run when original S5 defaults.
    assert "--s6-vision" in test
    assert 's6_vision_gate' in test
