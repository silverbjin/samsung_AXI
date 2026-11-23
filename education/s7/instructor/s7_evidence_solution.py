#!/usr/bin/env python3
"""S7 instructor solution: read-only, inspect actual Gazebo/ROS evidence.

The input may be from real L2 or L3. The program itself does NOT run
Gazebo, synthesize a Goal or a sensor, or replace original evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path

def ppm_rgb(path):
    blob=Path(path).read_bytes()
    header=blob.split(b'\n',3)
    if len(header)!=4 or header[0]!=b'P6' or header[2]!=b'255':
        raise ValueError('S7_PPM_P6_8BIT_REQUIRED')
    dims=header[1].split()
    if len(dims)!=2:raise ValueError('S7_PPM_DIMS_BAD')
    w,h=(int(x) for x in dims)
    if w<16 or h<16 or len(header[3])!=w*h*3:
        raise ValueError('S7_PPM_RGB_PAYLOAD_BAD')
    return w,h,header[3]

def evaluate(evidence,ppm_path):
    scene=evidence.get('s7_scene',{})
    if (scene.get('scenario')!='stacked' or
        scene.get('fixture_preloaded_at_world_start') is not True or
        scene.get('dynamic_fixture_spawn_requested') is not False):
        raise ValueError('S7_STACKED_STARTUP_WORLD_PROOF_MISSING')
    legs=evidence.get('real_nav_legs',[])
    if len(legs)!=2 or [a.get('label') for a in legs]!=['TABLE_3','PICKUP_RETURN']:
        raise ValueError('S7_NAV2_GOAL_SEQUENCE_INVALID')
    if any(a.get('action_status')!=4 for a in legs):
        raise ValueError('S7_NAV2_GOAL_NOT_SUCCEEDED')
    v=evidence.get('s6_vision',{})
    p=v.get('prediction',{})
    if (v.get('authorized') is not True or
        p.get('result')!='STACKED' or
        p.get('reason')!='REAL_RGB_MODEL_INFERENCE' or
        p.get('confidence',0)<.5):
        raise ValueError('S7_REAL_VISION_STACKED_MISSING')
    if evidence.get('s6_return_goal_sent') is not True:
        raise ValueError('S7_RETURN_GOAL_NOT_SENT')
    img=v.get('image',{})
    if (img.get('frames',0)<2 or not img.get('captured_after_arrival') or
        not img.get('captured_after_subscribe')):
        raise ValueError('S7_REAL_RGB_NOT_FRESH_AFTER_ARRIVAL')
    width,height,rgb=ppm_rgb(ppm_path)
    image_hash=hashlib.sha256(rgb).hexdigest()
    if (width,height)!=(img.get('width'),img.get('height')) or image_hash!=img.get('image_sha256'):
        raise ValueError('S7_PPM_SHA_OR_SIZE_MISMATCH')
    stop=evidence.get('s4_safety_stop',{})
    if (stop.get('filtered_output_max_abs_mps',float('inf'))>.025 or
        stop.get('physical_odom_motion_m',float('inf'))>.045):
        raise ValueError('S7_LIDAR_STOP_OR_PHYSICAL_DWELL_FAILED')
    if evidence.get('s6_integrated') is not True:
        raise ValueError('S7_INTEGRATED_VERDICT_MISSING')
    return {'verdict':'S7_TRAINING_EVIDENCE_CONTRACT_PASS',
            'scene_world_sha256':scene.get('world_sha256'),
            'nav2_labels':[a['label'] for a in legs],
            'vision_prediction':p['result'],
            'vision_confidence':p['confidence'],
            'rgb_frames':img['frames'],'rgb_sha256':image_hash,
            'filtered_output_max_abs_mps':stop['filtered_output_max_abs_mps'],
            'physical_odom_motion_m':stop['physical_odom_motion_m']}

def main():
    p=argparse.ArgumentParser(description='S7 instructor evidence-only validator')
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--ppm',type=Path,required=True)
    a=p.parse_args()
    e=json.loads(a.evidence.read_text())
    result=evaluate(e,a.ppm)
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=='__main__':main()
