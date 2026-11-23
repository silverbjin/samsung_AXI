#!/usr/bin/env python3
"""S7 empty-table expected HOLD evidence verifier; never starts ROS or sends Goals."""
import argparse
import hashlib
import json
from pathlib import Path
from s6_vision_ai import read_ppm

def validate(e,ppm,log):
    if e.get('s7_scene',{}).get('scenario')!='empty':
        raise ValueError('S7_NEGATIVE_NOT_EMPTY')
    if e['s7_scene'].get('dynamic_fixture_spawn_requested') is not False:
        raise ValueError('S7_NEGATIVE_DYNAMIC_SPAWN')
    legs=e.get('real_nav_legs',[])
    if len(legs)!=1 or legs[0].get('label')!='TABLE_3' or legs[0].get('action_status')!=4:
        raise ValueError('S7_NEGATIVE_NOT_ONE_SUCCESSFUL_DELIVERY')
    if e.get('s6_return_goal_sent') is not False or e.get('delivery_return') is True:
        raise ValueError('S7_NEGATIVE_RETURN_GOAL_ALREADY_SENT')
    v=e.get('s6_vision',{})
    if v.get('authorized') is not False or v.get('return_goal_sent') is not False:
        raise ValueError('S7_NEGATIVE_UNSAFE_AUTHORIZATION')
    if v.get('prediction',{}).get('result') not in ('NOT_STACKED','UNKNOWN'):
        raise ValueError('S7_NEGATIVE_PREDICTION_NOT_NEGATIVE')
    im=v.get('image',{})
    if im.get('frames',0)<2 or not im.get('captured_after_arrival') or not im.get('captured_after_subscribe'):
        raise ValueError('S7_NEGATIVE_NO_FRESH_REAL_RGB')
    w,h,rgb=read_ppm(ppm)
    if (w,h)!=(im.get('width'),im.get('height')) or hashlib.sha256(rgb).hexdigest()!=im.get('image_sha256'):
        raise ValueError('S7_NEGATIVE_RGB_SHA_MISMATCH')
    if 'S6_VISION_HOLD_NO_RETURN_GOAL' not in log:
        raise ValueError('S7_NEGATIVE_EXPECTED_HOLD_LOG_MISSING')
    if 'S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN' in log:
        raise ValueError('S7_NEGATIVE_UNEXPECTED_RETURN_SUCCESS')
    return {'verdict':'S7_REAL_EMPTY_TABLE_NO_RETURN_PASS','goal_sent':False,
            'prediction':v['prediction']['result'],'frames':im['frames']}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--ppm',type=Path,required=True)
    p.add_argument('--log',type=Path,required=True)
    a=p.parse_args()
    result=validate(json.loads(a.evidence.read_text()),a.ppm,a.log.read_text(errors='replace'))
    print(json.dumps(result,sort_keys=True))
    print('S7_EMPTY_RGB_NO_RETURN_REAL_GAZEBO_L2_PASS',flush=True)
