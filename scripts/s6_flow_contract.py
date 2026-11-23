#!/usr/bin/env python3
"""S6-FLOW-01: safe TABLE_3 → vision result → return state machine.

NO cmd_vel output. No implicit retry, no mock positive authorization.
"""
STAGES=('NAV_TO_TABLE','ARRIVAL_SETTLED','VISION_REQUESTED',
        'VISION_RESULT','NAV_RETURN','RETURNED','HOLD')
def next_state(state,event,prediction=None):
    if state not in STAGES:raise ValueError('S6_INVALID_FLOW_STATE')
    if state=='HOLD':return 'HOLD'
    transitions={
        ('NAV_TO_TABLE','GOAL_SUCCEEDED_AND_STOPPED'):'ARRIVAL_SETTLED',
        ('ARRIVAL_SETTLED','IMAGE_SUBSCRIPTION_STARTED'):'VISION_REQUESTED',
        ('NAV_RETURN','RETURN_GOAL_SUCCEEDED'):'RETURNED'
    }
    if (state,event) in transitions:return transitions[(state,event)]
    if state=='VISION_REQUESTED' and event=='CLASSIFIED':
        return 'VISION_RESULT'
    if state=='VISION_RESULT' and event=='AUTHORIZE_RETURN':
        if prediction is not None and prediction.get('result')=='STACKED' and (
            prediction.get('reason')=='REAL_RGB_MODEL_INFERENCE') and (
            prediction.get('confidence',0)>=.5):
            return 'NAV_RETURN'
    return 'HOLD'
