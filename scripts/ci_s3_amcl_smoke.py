#!/usr/bin/env python3
"""S3 real Gazebo + released occupancy map + official Nav2 AMCL pre-goal L2.

This test never publishes a navigation Goal or commands velocity. No synthetic
/map, /scan, /odom, /amcl_pose, or TF data are created.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

from s3_map_contract import validate_release
from ci_s2_map_smoke import end_process

def run(args):
    import rclpy
    from geometry_msgs.msg import PoseWithCovarianceStamped
    from nav_msgs.msg import OccupancyGrid,Odometry
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from tf2_msgs.msg import TFMessage
    from rclpy.parameter import Parameter
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
    from rclpy.action import ActionClient
    from nav2_msgs.action import NavigateToPose
    from action_msgs.msg import GoalStatus
    from lifecycle_msgs.srv import GetState
    from lifecycle_msgs.msg import State

    repo=Path(__file__).resolve().parents[1]
    contract=validate_release(repo)
    if not args.robot_sdf.is_file() or not args.params.is_file() or not args.map.is_file():
        raise RuntimeError('S3_REQUIRED_ROBOT_SDF_PARAMS_OR_MAP_MISSING')
    state={'clock':False,'scan':0,'scan_t':0.,'odom':None,'odom_t':0.,
           'odom_track':[],'map':None,'amcl_pose':None,
           'amcl_cov':None,'map_to_odom':False,'odom_to_base':False}
    args.log.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    proc=node=None
    started=False
    def odom(m):
        xy=(float(m.pose.pose.position.x),float(m.pose.pose.position.y))
        state['odom']=xy;state['odom_t']=time.monotonic()
        if not state['odom_track'] or math.dist(xy,state['odom_track'][-1])>.02:
            state['odom_track'].append(xy)
    def scan(m):
        if len(m.ranges)>10:
            state['scan']+=1
            state['scan_t']=time.monotonic()
    def amcl(m):
        pose=m.pose.pose
        state['amcl_pose']=(pose.position.x,pose.position.y)
        state['amcl_cov']=(m.pose.covariance[0],m.pose.covariance[7],m.pose.covariance[35])
    def tf(m):
        for t in m.transforms:
            if t.header.frame_id=='map' and t.child_frame_id=='odom':
                state['map_to_odom']=True
            if t.header.frame_id=='odom' and t.child_frame_id in ('base_footprint','base_link'):
                state['odom_to_base']=True
    def spin_once(timeout=.25):
        if proc.poll() is not None:raise RuntimeError('S3_NAV2_LAUNCH_EXITED:'+str(proc.returncode))
        rclpy.spin_once(node,timeout_sec=timeout)
    def wait(fn,seconds,label):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            spin_once()
            if fn():return
        raise RuntimeError('TIMEOUT_'+label)
    try:
        with args.log.open('w') as out:
            proc=subprocess.Popen(
                ['ros2','launch','restaurant_bringup','navigation.launch.py',
                 'gui:=false','robot_sdf:='+str(args.robot_sdf.resolve()),
                 'map:='+str(args.map.resolve()),
                 'params_file:='+str(args.params.resolve())],
                stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
            rclpy.init(args=None);started=True
            node=rclpy.create_node('samsungaxi_s3_amcl_ci_no_goal',
                parameter_overrides=[Parameter('use_sim_time',Parameter.Type.BOOL,True)])
            map_qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,
                               durability=DurabilityPolicy.TRANSIENT_LOCAL)
            node.create_subscription(Clock,'/clock',
                lambda m:state.update(clock=(m.clock.sec>0)),qos_profile_sensor_data)
            node.create_subscription(LaserScan,'/scan',scan,qos_profile_sensor_data)
            node.create_subscription(Odometry,'/odom',odom,qos_profile_sensor_data)
            node.create_subscription(OccupancyGrid,'/map',
                lambda m:state.update(map=m),map_qos)
            node.create_subscription(PoseWithCovarianceStamped,'/amcl_pose',amcl,10)
            node.create_subscription(TFMessage,'/tf',tf,qos_profile_sensor_data)
            pub=node.create_publisher(PoseWithCovarianceStamped,'/initialpose',10)
            action=ActionClient(node,NavigateToPose,'navigate_to_pose')
            wait(lambda:state['clock'] and state['scan']>=3 and state['odom'] is not None
                 and state['map'] is not None,200,'CLOCK_SCAN_ODOM_RELEASED_MAP')
            m=state['map']
            if m.info.width!=contract['width'] or m.info.height!=contract['height']:
                raise RuntimeError('RELEASED_MAP_SERVER_DIMENSIONS_WRONG')
            if m.header.frame_id!='map':
                raise RuntimeError('MAP_FRAME_NOT_MAP')
            print('S3_REAL_GAZEBO_RELEASED_MAP_AND_SENSORS_PRESENT',flush=True)

            # AMCL localization is seeded from the actual *map* start, not SDF World (-2.6,-2.2).
            initial=PoseWithCovarianceStamped()
            initial.header.frame_id='map'
            initial.pose.pose.position.x=contract['pickup_map_xy'][0]
            initial.pose.pose.position.y=contract['pickup_map_xy'][1]
            initial.pose.pose.orientation.w=1.0
            initial.pose.covariance[0]=.20
            initial.pose.covariance[7]=.20
            initial.pose.covariance[35]=.10
            until=time.monotonic()+160
            last_publish=0.0
            while time.monotonic()<until:
                spin_once(.22)
                now=time.monotonic()
                if now-last_publish>2 and pub.get_subscription_count()>0:
                    initial.header.stamp=node.get_clock().now().to_msg()
                    pub.publish(initial);last_publish=now
                if (state['amcl_pose'] is not None and state['map_to_odom']
                    and state['odom_to_base'] and action.wait_for_server(timeout_sec=.25)):
                    break
            else:
                raise RuntimeError('S3_AMCL_TF_OR_NAV2_ACTION_NOT_READY:'+json.dumps({
                    'amcl_pose':state['amcl_pose'],'map_to_odom':state['map_to_odom'],
                    'odom_to_base':state['odom_to_base'],'scan_count':state['scan']}))
            px,py=state['amcl_pose']
            if not (math.isfinite(px) and math.isfinite(py)) or math.hypot(px,py)>.90:
                raise RuntimeError('AMCL_INITIAL_MAP_FRAME_POSITION_INVALID:'+str(state['amcl_pose']))
            if not all(math.isfinite(x) and 0<=x<100 for x in state['amcl_cov']):
                raise RuntimeError('AMCL_COVARIANCE_INVALID:'+str(state['amcl_cov']))
            result={'kind':'s3_real_gazebo_no_navigation_goal',
                    'release_run':contract['release_run'],
                    'map_yaml':str(args.map),'map_pgm_sha256':contract['pgm_sha256'],
                    'pickup_map_xy':contract['pickup_map_xy'],
                    'table3_map_xy':contract['table3_map_xy'],
                    'map_dimensions':[m.info.width,m.info.height],
                    'map_frame':m.header.frame_id,'amcl_pose_xy':[px,py],
                    'amcl_covariance_diag':state['amcl_cov'],
                    'scan_count':state['scan'],'map_to_odom':state['map_to_odom'],
                    'odom_to_base':state['odom_to_base'],
                    'navigate_to_pose_server_ready':True,'goal_sent':False}
            args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
            print('RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL',flush=True)
            if args.exercise_goals:
                # Action discovery alone is NOT evidence of Nav2 Lifecycle readiness.
                # With slow first-time Gazebo startup the action server exists while
                # bt_navigator, planner, controller or collision_monitor are inactive.
                managed=('bt_navigator','planner_server','controller_server',
                         'collision_monitor','behavior_server')
                lc={name:node.create_client(GetState,'/'+name+'/get_state') for name in managed}
                active={name:False for name in managed}
                deadline=time.monotonic()+150.0
                while time.monotonic()<deadline and not all(active.values()):
                    spin_once(.18)
                    for name,client in lc.items():
                        if active[name] or not client.service_is_ready():
                            continue
                        future=client.call_async(GetState.Request())
                        limit=time.monotonic()+1.3
                        while not future.done() and time.monotonic()<limit:
                            spin_once(.12)
                        if future.done() and not future.exception():
                            active[name]=(future.result().current_state.id==State.PRIMARY_STATE_ACTIVE)
                    if time.monotonic()-state['scan_t']>10:
                        raise RuntimeError('S3_NAV_PREGOAL_SCAN_STALE')
                if not all(active.values()):
                    raise RuntimeError('S3_NAV_LIFECYCLE_NOT_ALL_ACTIVE:'+json.dumps(active))
                print('S3_NAV02_LIFECYCLE_ACTIVE_PREGOAL='+','.join(managed),flush=True)
                def goto(target,heading,label):
                    if not (state['map_to_odom'] and state['odom_to_base'] and
                            state['amcl_pose'] is not None and state['scan']>=3):
                        raise RuntimeError('NAV_PREGOAL_NOT_READY_'+label)
                    if time.monotonic()-state['scan_t']>8 or time.monotonic()-state['odom_t']>8:
                        raise RuntimeError('NAV_PREGOAL_SENSOR_STALE_'+label)
                    start=state['odom']
                    scans_before=state['scan']
                    before=len(state['odom_track'])
                    msg=NavigateToPose.Goal()
                    msg.pose.header.frame_id='map'
                    msg.pose.header.stamp=node.get_clock().now().to_msg()
                    msg.pose.pose.position.x=float(target[0])
                    msg.pose.pose.position.y=float(target[1])
                    msg.pose.pose.orientation.z=math.sin(heading/2)
                    msg.pose.pose.orientation.w=math.cos(heading/2)
                    sent=action.send_goal_async(msg)
                    deadline=time.monotonic()+25
                    while not sent.done() and time.monotonic()<deadline:
                        spin_once(.20)
                    if not sent.done():raise RuntimeError('NAV_ACTION_GOAL_RESPONSE_TIMEOUT_'+label)
                    handle=sent.result()
                    if not handle.accepted:raise RuntimeError('NAV_ACTION_GOAL_REJECTED_'+label)
                    print('S3_NAV02_REAL_GOAL_ACCEPTED='+label,flush=True)
                    completed=handle.get_result_async()
                    deadline=time.monotonic()+280
                    while not completed.done() and time.monotonic()<deadline:
                        spin_once(.22)
                        if time.monotonic()-state['scan_t']>10 or time.monotonic()-state['odom_t']>10:
                            handle.cancel_goal_async()
                            raise RuntimeError('NAV_SENSOR_STALE_DURING_GOAL_'+label)
                    if not completed.done():
                        handle.cancel_goal_async()
                        raise RuntimeError('NAV_GOAL_TIMEOUT_'+label)
                    response=completed.result()
                    if response.status!=GoalStatus.STATUS_SUCCEEDED:
                        raise RuntimeError('NAV_GOAL_NOT_SUCCEEDED_'+label+':'+str(response.status))
                    for _ in range(5):spin_once(.20)
                    traveled=max((math.dist(start,xy) for xy in state['odom_track'][before:]),default=0.)
                    if traveled<1.0:
                        raise RuntimeError('NAV_PHYSICAL_ODOM_INSUFFICIENT_'+label+':'+str(round(traveled,3)))
                    error=math.dist(state['amcl_pose'],target)
                    if error>.75:
                        raise RuntimeError('NAV_AMCL_ARRIVAL_OUTSIDE_TOLERANCE_'+label+':'+str(round(error,3)))
                    if state['scan']-scans_before<10:
                        raise RuntimeError('NAV_SCAN_EVIDENCE_MISSING_'+label)
                    evidence={'label':label,'goal_map_xy':target,'action_status':response.status,
                              'physical_odom_max_displacement_m':round(traveled,3),
                              'amcl_arrival_xy':state['amcl_pose'],
                              'amcl_arrival_error_m':round(error,3),
                              'scan_count_delta':state['scan']-scans_before}
                    print('S3_NAV02_GOAL_SUCCEEDED='+label+' ODOM_M='+str(round(traveled,3))+
                          ' AMCL_ERROR_M='+str(round(error,3)),flush=True)
                    return evidence
                legs=[goto(contract['table3_map_xy'],-math.pi/2,'TABLE_3'),
                      goto(contract['pickup_map_xy'],0.,'PICKUP_RETURN')]
                result['goal_sent']=True
                result['real_nav_legs']=legs
                result['delivery_return']=True
                args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                print('RESTAURANT_S3_NAV02_REAL_GAZEBO_DELIVERY_RETURN_PASS',flush=True)
    except Exception as exc:
        print('RESTAURANT_S3_AMCL_L2_BLOCKED='+str(exc),file=sys.stderr,flush=True)
        raise
    finally:
        end_process(proc)
        if node is not None:node.destroy_node()
        if started and rclpy.ok():rclpy.shutdown()
        if args.log.is_file():
            lines=args.log.read_text(errors='replace').splitlines()
            clues=[line[:400] for line in lines if
                   any(word in line.lower() for word in ('error','warn','fail','timeout','lifecycle','amcl'))]
            (args.log.parent/'ci-s3-summary.txt').write_text(
                'FIRST_60_DIAGNOSTIC_LINES\n'+'\n'.join(clues[:60])+
                '\nLAST_80_LINES\n'+'\n'.join(lines[-80:])+'\n')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exercise-goals',action='store_true')
    p.add_argument('--robot-sdf',type=Path,required=True)
    p.add_argument('--params',type=Path,required=True)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--log',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    run(p.parse_args())

if __name__=='__main__':main()
