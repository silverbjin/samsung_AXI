#!/usr/bin/env python3
"""S6 opt-in real TABLE_3 RGB model gate, never publish velocity or a Goal.

Called by the already accepted S5 NavigateToPose runner only AFTER TABLE_3
SUCCEEDED. The model is frozen before leaving pickup. Fail closed by returning
UNKNOWN/HOLD evidence, never interpreting a missing frame as success.
"""
import hashlib,json,subprocess,time
from pathlib import Path
from s6_camera_scene_ci import rgb_bytes,save_ppm
from s6_scene import write_fixture,FIXTURE_WORLD_XY
from s6_vision_ai import infer,accept_return,validate
from s6_flow_contract import next_state

def gate(node,spin_once,state,model_path,evidence_dir,seed_fixture):
    from sensor_msgs.msg import Image
    from rclpy.qos import qos_profile_sensor_data
    model=validate(json.loads(Path(model_path).read_text()))
    status='NAV_TO_TABLE'
    # Actual positive Nav2 action was proven by caller. Odom must settle
    # BEFORE any image request and before returning to the pickup.
    speeds=[]
    arrived=time.monotonic()
    for _ in range(12):
        spin_once(.13)
        if state.get('odom_speed_t',0)>=arrived:
            speeds.append(abs(state.get('odom_speed',float('inf'))))
    stopped=len(speeds)>=3 and max(speeds)<=.025
    if not stopped:
        return {'state':'HOLD','authorized':False,'prediction':{
            'result':'UNKNOWN','confidence':0.,'reason':'NOT_SETTLED'},
            'odom_speed_samples_mps':speeds,'return_goal_sent':False}
    status=next_state(status,'GOAL_SUCCEEDED_AND_STOPPED')
    evidence_dir=Path(evidence_dir)
    if seed_fixture:
        fixture=evidence_dir/'s6_stacked_dishes.sdf'
        write_fixture(fixture)
        p=subprocess.run(['ros2','run','ros_gz_sim','create',
                '-name','s6_stacked_dishes','-file',str(fixture),
                '-x',str(FIXTURE_WORLD_XY[0]),'-y',str(FIXTURE_WORLD_XY[1]),
                '-z','0'],capture_output=True,text=True,timeout=30)
        if p.returncode or 'entity creation successful' not in (
                p.stdout+p.stderr).lower():
            return {'state':'HOLD','authorized':False,'prediction':{
                'result':'UNKNOWN','confidence':0.,'reason':'DISH_FIXTURE_SPAWN_FAIL'},
                'spawn_log_tail':(p.stdout+p.stderr)[-350:],
                'return_goal_sent':False}
    started=time.monotonic()
    frames=[]
    def on_image(msg):
        if msg.width and msg.height and msg.data:
            frames.append((time.monotonic(),msg))
            if len(frames)>5:del frames[:-5]
    sub=node.create_subscription(Image,'/restaurant/rgbd/image',on_image,
                                 qos_profile_sensor_data)
    status=next_state(status,'IMAGE_SUBSCRIPTION_STARTED')
    try:
        until=time.monotonic()+12.0
        while time.monotonic()<until and len(frames)<3:
            spin_once(.22)
        if len(frames)<2:
            prediction={'result':'UNKNOWN','confidence':0.,'reason':'IMAGE_TIMEOUT'}
            image={'frames':len(frames)}
        else:
            t,msg=frames[-1]
            raw=rgb_bytes(msg)
            prediction=infer(model,raw,msg.width,msg.height)
            file=evidence_dir/'s6_table_rgb.ppm'
            save_ppm(file,msg.width,msg.height,raw)
            image={'frames':len(frames),'width':msg.width,'height':msg.height,
                   'frame_id':msg.header.frame_id,'stamp_sec':msg.header.stamp.sec,
                   'stamp_nsec':msg.header.stamp.nanosec,
                   'image_sha256':hashlib.sha256(raw).hexdigest(),
                   'captured_after_arrival':t>arrived,
                   'captured_after_subscribe':t>started}
    finally:
        node.destroy_subscription(sub)
    status=next_state(status,'CLASSIFIED')
    fresh=bool(image.get('captured_after_arrival') and
               image.get('captured_after_subscribe') and
               image.get('stamp_sec',0)>0)
    allowed=accept_return(prediction,True,stopped,fresh)
    transition=next_state(status,'AUTHORIZE_RETURN',prediction)
    return {'state':transition,'authorized':bool(allowed and transition=='NAV_RETURN'),
            'prediction':prediction,'image':image,
            'odom_speed_samples_mps':speeds,
            'fixture_seeded_for_demo':bool(seed_fixture),'return_goal_sent':False}
