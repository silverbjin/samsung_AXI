"""S7 negative gate L0: synthetic fixtures ONLY for contract, not real L2."""
import copy
import hashlib
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from s7_negative_contract import validate
from s6_vision_ai import accept_return
from s6_flow_contract import next_state

def evidence(tmp_path):
    rgb=bytes([40,35,30])*32*32
    p=tmp_path/'real.ppm'
    p.write_bytes(b'P6\n32 32\n255\n'+rgb)
    x={'s7_scene':{'scenario':'empty','dynamic_fixture_spawn_requested':False},
       'real_nav_legs':[{'label':'TABLE_3','action_status':4}],
       's6_return_goal_sent':False,'delivery_return':False,
       's6_vision':{'authorized':False,'return_goal_sent':False,
                    'prediction':{'result':'NOT_STACKED','reason':'REAL_RGB_MODEL_INFERENCE','confidence':.91},
                    'image':{'frames':3,'width':32,'height':32,'image_sha256':hashlib.sha256(rgb).hexdigest(),
                             'captured_after_arrival':True,'captured_after_subscribe':True}}}
    return x,p

def test_expected_empty_rgb_no_return_contract(tmp_path):
    x,p=evidence(tmp_path)
    assert validate(x,p,'S6_VISION_HOLD_NO_RETURN_GOAL')['goal_sent'] is False
    assert not accept_return(x['s6_vision']['prediction'],True,True,True)
    assert next_state('VISION_RESULT','AUTHORIZE_RETURN',x['s6_vision']['prediction'])=='HOLD'
    x['s6_vision']['prediction']['result']='UNKNOWN'
    assert validate(x,p,'S6_VISION_HOLD_NO_RETURN_GOAL')['prediction']=='UNKNOWN'

def test_goal_spoofing_missing_rgb_and_false_hold_blocked(tmp_path):
    original,p=evidence(tmp_path)
    for field,value in [('s6_return_goal_sent',True),('delivery_return',True),
                        ('real_nav_legs',original['real_nav_legs']+[{'label':'PICKUP_RETURN','action_status':4}])]:
        x=copy.deepcopy(original);x[field]=value
        with pytest.raises(ValueError):validate(x,p,'S6_VISION_HOLD_NO_RETURN_GOAL')
    x=copy.deepcopy(original);x['s6_vision']['image']['frames']=0
    with pytest.raises(ValueError,match='FRESH_REAL_RGB'):validate(x,p,'S6_VISION_HOLD_NO_RETURN_GOAL')
    with pytest.raises(ValueError,match='HOLD_LOG_MISSING'):validate(original,p,'')
    with pytest.raises(ValueError,match='UNEXPECTED_RETURN_SUCCESS'):
        validate(original,p,'S6_VISION_HOLD_NO_RETURN_GOAL\nS3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN')
