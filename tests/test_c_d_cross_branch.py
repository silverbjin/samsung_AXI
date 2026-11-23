"""C07 cross-branch *mock-only* D MissionManager + C InferenceCore contract.

D code is read from its OWN separately checked-out SHA; this does not patch D.
No Nav2 action, physical model or ROS process runs in this test.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/smartdish_ai'))
from smartdish_ai.inference_core import InferenceCore

D_ROOT = Path(os.environ.get('SMARTDISH_D_READONLY', str(ROOT/'d-read-only')))
D_PACKAGE = D_ROOT/'src/smartdish_service'
if not (D_PACKAGE/'smartdish_service/mission_manager.py').is_file():
    pytest.skip('D_READONLY_SOURCE_NOT_AVAILABLE_LOCAL; CI checkout required',allow_module_level=True)
sys.path.insert(0,str(D_PACKAGE))
from smartdish_service.mission_manager import MissionManager


def frame():
    return bytes((7, 9, 11)) * (16*16)


def start_ai_check(now):
    clock = [now]
    d = MissionManager(clock=lambda:clock[0],ai_available=True,ai_timeout_s=5)
    req={'request_id':'C07-REQ','table_id':'T03','table_wait_s':1,
         'dropoff_wait_s':1,'ai_enabled':True}
    assert d.handle_request(req)
    initial=d.drain()
    assert any(t=='/collection/nav_goal' and m['leg']=='TO_TABLE' for t,m in initial)
    # Synthetic success is a contract stimulus, NEVER actual navigation.
    assert d.on_nav_result({'request_id':'C07-REQ','leg':'TO_TABLE','result':'SUCCEEDED','reason':''})
    d.drain()
    clock[0]+=1.01
    d.tick()
    events=d.drain()
    checks=[x for t,x in events if t=='/collection/ai_check_request']
    assert len(checks)==1
    assert d.state=='AI_CHECK'
    return d,clock,checks[0]


def test_model_absent_routes_unknown_to_staff_not_navigation():
    d,clock,req=start_ai_check(10.)
    c=InferenceCore(None,'none')
    response=c.handle_request(json.dumps(req),now=clock[0])
    assert response=={'request_id':req['request_id'],'capture_id':req['capture_id'],
                      'status':'UNKNOWN','confidence':None,'model_version':'none'}
    assert d.on_stability(response)
    assert d.state=='NEEDS_CONFIRMATION'
    assert not any(t=='/collection/nav_goal' for t,_ in d.drain())
    assert d.on_staff_confirm({'request_id':'C07-REQ','action':'APPROVE_CONTINUE'})
    assert d.state=='TO_RETURN'
    assert [m['destination_id'] for t,m in d.drain() if t=='/collection/nav_goal']==['DISH_RETURN']


def test_low_confidence_and_stale_frames_never_release():
    for conf,age in ((0.79,0.1), (0.99,3.0)):
        d,clock,req=start_ai_check(20.)
        c=InferenceCore(lambda *_:('STABLE',conf),'MOCK_PREDICTOR_NOT_WEIGHTS',confidence_min=.8)
        c.cache_rgb(frame(),16,16,received_at=clock[0]-age)
        response=c.handle_request(json.dumps(req),now=clock[0])
        assert response['status']=='UNKNOWN' and response['confidence'] is None
        assert d.on_stability(response)
        assert d.state=='NEEDS_CONFIRMATION'
        assert not any(t=='/collection/nav_goal' for t,_ in d.drain())


def test_unstable_requires_staff_and_abort_cancels():
    d,clock,req=start_ai_check(30.)
    c=InferenceCore(lambda *_:('UNSTABLE',.95),'MOCK_PREDICTOR_NOT_WEIGHTS')
    c.cache_rgb(frame(),16,16,received_at=clock[0])
    assert d.on_stability(c.handle_request(json.dumps(req),now=clock[0]))
    assert d.state=='NEEDS_CONFIRMATION'
    assert not any(t=='/collection/nav_goal' for t,_ in d.drain())
    assert d.on_staff_confirm({'request_id':'C07-REQ','action':'ABORT'})
    assert d.state=='CANCELED'
    assert not any(t=='/collection/nav_goal' for t,_ in d.drain())


def test_stable_mock_path_only_proves_message_shape():
    d,clock,req=start_ai_check(40.)
    c=InferenceCore(lambda *_:('STABLE',.93),'MOCK_PREDICTOR_NOT_WEIGHTS')
    c.cache_rgb(frame(),16,16,received_at=clock[0])
    response=c.handle_request(json.dumps(req),now=clock[0])
    assert response['status']=='STABLE'
    assert d.on_stability(response)
    assert d.state=='TO_RETURN'
    assert [m['destination_id'] for t,m in d.drain() if t=='/collection/nav_goal']==['DISH_RETURN']


def test_mismatched_capture_and_duplicate_check_cannot_move():
    d,clock,req=start_ai_check(50.)
    c=InferenceCore(None)
    malformed={'request_id':req['request_id'],'capture_id':'OLD-CAP',
               'status':'STABLE','confidence':.99,'model_version':'fake'}
    assert not d.on_stability(malformed)
    assert d.state=='AI_CHECK'
    assert c.handle_request(json.dumps(req),now=clock[0])['status']=='UNKNOWN'
    assert c.handle_request(json.dumps(req),now=clock[0]) is None
    clock[0]+=5.01
    d.tick()
    assert d.state=='NEEDS_CONFIRMATION'
    assert not any(t=='/collection/nav_goal' for t,_ in d.drain())


def test_ai_off_does_not_depend_on_c():
    clock=[0.]
    d=MissionManager(clock=lambda:clock[0],ai_available=False)
    assert d.handle_request({'request_id':'C07-AI-OFF','table_id':'T03','table_wait_s':1,
                             'dropoff_wait_s':1,'ai_enabled':False})
    d.drain()
    assert d.on_nav_result({'request_id':'C07-AI-OFF','leg':'TO_TABLE','result':'SUCCEEDED','reason':''})
    d.drain()
    clock[0]=1.1
    d.tick()
    out=d.drain()
    assert d.state=='TO_RETURN'
    assert all(t!='/collection/ai_check_request' for t,_ in out)
    assert any(t=='/collection/nav_goal' and m['destination_id']=='DISH_RETURN' for t,m in out)
