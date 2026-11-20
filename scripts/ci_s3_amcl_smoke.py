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

from s3_map_contract import validate_release,validate_s2_map03_candidate
from s5_owner_approval import wait_for_owner_approval,wait_for_fresh_sensors
from ci_s2_map_smoke import end_process
from s2_map02_gt_pose import GazeboModelPose
from s4_menu_contract import (NORMAL_LIMIT,SOUP_LIMIT,measured_speed,compare_speeds,
                              fixture_sdf,front_obstacle_points,stop_polygon_points)

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
    from nav2_msgs.msg import SpeedLimit, CollisionMonitorState
    from geometry_msgs.msg import Twist
    from action_msgs.msg import GoalStatus
    from lifecycle_msgs.srv import GetState
    from lifecycle_msgs.msg import State

    # S5 is one combined physical Gazebo session; never silently launch goals
    # in an instructor GUI without explicit CLI and on-terminal authorization.
    if args.s5_integrated and not (args.exercise_goals and args.menu_safety
                                   and args.no_initial_pose_publish):
        raise RuntimeError('S5_REQUIRES_MENU_NAV_ACTION_AND_AUTO_AMCL')
    if args.live_owner and not (args.s5_integrated and args.gui and
                                os.environ.get('SAMSUNGAXI_S5_GOALS_APPROVED')=='YES-S5-LIVE-GOALS'):
        raise RuntimeError('S5_OWNER_GOALS_NOT_AUTHORIZED')
    repo=Path(__file__).resolve().parents[1]
    candidate=repo/'maps/candidates/s2_map03/restaurant_map.yaml'
    contract=(validate_s2_map03_candidate(repo) if args.map.resolve()==candidate.resolve()
              else validate_release(repo))
    if args.s5_integrated and args.map.resolve()!=candidate.resolve():
        raise RuntimeError('S5_REQUIRES_CUSTODY_VERIFIED_S2_MAP03')
    if not args.robot_sdf.is_file() or not args.params.is_file() or not args.map.is_file():
        raise RuntimeError('S3_REQUIRED_ROBOT_SDF_PARAMS_OR_MAP_MISSING')
    if args.menu_safety and not args.exercise_goals:
        raise RuntimeError('S4_MENU_REQUIRES_REAL_NAV_ACTIONS')
    if args.s4_stop_only and (args.menu_safety or args.exercise_goals):
        raise RuntimeError('S4_STOP_ONLY_MUST_NOT_SEND_NAV_GOALS')
    s4={'active_menu':None,'speed_samples':{'NORMAL':[],'SOUP':[]},
        'scan':None,'cm_states':[],'cmd_in':[],'cmd_out':[]}
    state={'clock':False,'scan':0,'scan_t':0.,'odom':None,'odom_t':0.,'odom_count':0,
           'odom_track':[],'map':None,'amcl_pose':None,
           'amcl_cov':None,'map_to_odom':False,'odom_to_base':False}
    args.log.parent.mkdir(parents=True,exist_ok=True)
    args.evidence.parent.mkdir(parents=True,exist_ok=True)
    proc=node=None
    started=False
    def odom(m):
        xy=(float(m.pose.pose.position.x),float(m.pose.pose.position.y))
        state['odom']=xy;state['odom_t']=time.monotonic();state['odom_count']+=1
        if args.menu_safety and s4['active_menu'] is not None:
            s4['speed_samples'][s4['active_menu']].append(float(m.twist.twist.linear.x))
        if not state['odom_track'] or math.dist(xy,state['odom_track'][-1])>.02:
            state['odom_track'].append(xy)
    def scan(m):
        if len(m.ranges)>10:
            state['scan']+=1
            state['scan_t']=time.monotonic()
            if args.menu_safety or args.s4_stop_only:s4['scan']=m
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
                 'gui:=true' if args.gui else 'gui:=false',
                 'robot_sdf:='+str(args.robot_sdf.resolve()),
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
            s4_speed_pub=s4_probe=None
            if args.menu_safety or args.s4_stop_only:
                def on_cm(m):
                    s4['cm_states'].append((time.monotonic(),int(m.action_type),m.polygon_name))
                def on_input(m):
                    s4['cmd_in'].append((time.monotonic(),float(m.linear.x)))
                def on_output(m):
                    s4['cmd_out'].append((time.monotonic(),float(m.linear.x)))
                node.create_subscription(CollisionMonitorState,'/collision_monitor_state',on_cm,10)
                node.create_subscription(Twist,'/cmd_vel_smoothed',on_input,10)
                node.create_subscription(Twist,'/cmd_vel',on_output,10)
                s4_speed_pub=node.create_publisher(SpeedLimit,'/speed_limit',10)
                s4_probe=node.create_publisher(Twist,'/cmd_vel_smoothed',10)
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
                if not args.no_initial_pose_publish and now-last_publish>2 and pub.get_subscription_count()>0:
                    initial.header.stamp=node.get_clock().now().to_msg()
                    pub.publish(initial);last_publish=now
                if (state['amcl_pose'] is not None and state['map_to_odom']
                    and state['odom_to_base'] and (args.s4_stop_only or action.wait_for_server(timeout_sec=.25))):
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
            result['manual_initial_pose_published']=not args.no_initial_pose_publish
            if args.no_initial_pose_publish:
                print('S3_AMCL_AUTO_INITIAL_POSE_REAL_GAZEBO_PASS_NO_MANUAL_PUBLISH',flush=True)
            args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
            print('RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL',flush=True)
            def perform_s4_stop(result):
                # Real Gazebo physical fixture and real LiDAR/CM output only.
                # A bounded 0.08 m/s CI probe into the *upstream* CM input
                # checks its actual STOP filtering, not an alternate robot controller.
                gt=GazeboModelPose()
                try:
                    gt.start()
                    wait(lambda:gt.fresh() and gt.samples>=2,12,'S4_GAZEBO_MODEL_POSE')
                    rx,ry,ryaw=gt.pose
                    if math.dist((rx,ry),(-2.60,-2.20))>.80:
                        raise RuntimeError('S4_ROBOT_NOT_BACK_AT_PICKUP')
                    # The physical cylinder must be observed inside the actual
                    # CM forward STOP polygon, not merely in a broad front sector.
                    fx=rx+.52*math.cos(ryaw)
                    fy=ry+.52*math.sin(ryaw)
                    # Before injecting, prove the requested STOP zone is clear.
                    initial_rect=stop_polygon_points(s4['scan'])
                    if initial_rect>=4:
                        raise RuntimeError('S4_FIXTURE_PRECONDITION_STOP_ZONE_NOT_CLEAR:'+str(initial_rect))
                    fixture=args.evidence.parent/'s4_collision_fixture.sdf'
                    fixture.write_text(fixture_sdf())
                    fixture_marker=time.monotonic()
                    created=subprocess.run(
                        ['ros2','run','ros_gz_sim','create','-name','s4_collision_fixture',
                         '-file',str(fixture),'-x',str(fx),'-y',str(fy),'-z','.25'],
                        capture_output=True,text=True,timeout=28,check=False)
                    if created.returncode!=0 or 'entity creation successful' not in (created.stdout+created.stderr).lower():
                        raise RuntimeError('S4_GAZEBO_FIXTURE_NOT_CREATED:'+
                                           repr((created.stdout+created.stderr)[-350:]))
                    initial_scan_count=state['scan']
                    wait(lambda:state['scan']>=initial_scan_count+4 and
                         front_obstacle_points(s4['scan'])>=4 and
                         stop_polygon_points(s4['scan'])>=4,18,
                         'S4_PHYSICAL_FIXTURE_INSIDE_STOP_POLYGON')
                    print('S4_PHYSICAL_FIXTURE_LIDAR_POINTS='+str(front_obstacle_points(s4['scan']))+
                          ' STOP_RECT_POINTS='+str(stop_polygon_points(s4['scan'])),flush=True)
                    if s4_probe.get_subscription_count()<1:
                        raise RuntimeError('S4_CM_UPSTREAM_TOPIC_SUBSCRIBER_MISSING')
                    # Guarantee the robot has settled at the Nav2 return goal.
                    start_xy=state['odom']
                    start_t=time.monotonic()
                    marker=time.monotonic()
                    positive_probe=Twist()
                    positive_probe.linear.x=.08
                    while time.monotonic()-start_t<1.8:
                        s4_probe.publish(positive_probe)
                        spin_once(.12)
                    s4_probe.publish(Twist())
                    for _ in range(8):spin_once(.15)
                    stopped=any(t>=fixture_marker and a==CollisionMonitorState.STOP
                                and name=='S4ForwardStop' for t,a,name in s4['cm_states'])
                    outputs=[v for t,v in s4['cmd_out'] if t>=marker]
                    positive_input=any(t>=marker and v>=.075 for t,v in s4['cmd_in'])
                    moved=math.dist(start_xy,state['odom'])
                    if not positive_input or not stopped or len(outputs)<3:
                        raise RuntimeError('S4_CM_STOP_CHAIN_UNPROVEN:'+
                            json.dumps({'input_seen':positive_input,'cm_stop':stopped,
                                        'cmd_out_count':len(outputs),
                                        'front_points':front_obstacle_points(s4['scan']),
                                        'stop_rect_points':stop_polygon_points(s4['scan']),
                                        'state_messages':len(s4['cm_states']),
                                        'recent_states':s4['cm_states'][-12:],
                                        'cmd_in_count':len([1 for t,_ in s4['cmd_in'] if t>=marker]),
                                        'cmd_out_abs_max':max([abs(v) for v in outputs],default=None)}))
                    if max(abs(v) for v in outputs)>.025 or moved>.045:
                        raise RuntimeError('S4_CM_STOP_FAILED_TO_FILTER_OR_ROBOT_MOVED:'+
                            json.dumps({'cmd_out_max':max(abs(v) for v in outputs),
                                        'odom_motion_m':moved}))
                    result['s4_safety_stop']={
                        'fixture':'physical_gazebo_sdf_cylinder',
                        'gazebo_fixture_world_xy':[round(fx,3),round(fy,3)],
                        'scan_front_obstacle_points':front_obstacle_points(s4['scan']),
                        'cm_state':'STOP','polygon':'S4ForwardStop',
                        'upstream_positive_command_seen':True,
                        'filtered_output_max_abs_mps':round(max(abs(v) for v in outputs),4),
                        'physical_odom_motion_m':round(moved,4)}
                    result['kind']=('s4_real_gazebo_menu_speed_and_collision_stop'
                                    if args.menu_safety else 's4_collision_monitor_real_stop_only')
                    result['s4_complete']=bool(args.menu_safety)
                    args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                    print('S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS',flush=True)
                finally:
                    if s4_probe is not None:
                        s4_probe.publish(Twist())
                    gt.close()
            if args.s4_stop_only:
                # Standalone S4 safety boundary: prove real Gazebo LiDAR+CM STOP
                # without repeating previously GREEN full 5m NORMAL/SOUP trips.
                client=node.create_client(GetState,'/collision_monitor/get_state')
                def cm_active():
                    if not client.service_is_ready():return False
                    future=client.call_async(GetState.Request())
                    until=time.monotonic()+1.5
                    while time.monotonic()<until and not future.done():
                        spin_once(.15)
                    return future.done() and not future.exception() and (
                        future.result().current_state.id==State.PRIMARY_STATE_ACTIVE)
                wait(cm_active,120,'S4_CM_LIFECYCLE_ACTIVE')
                perform_s4_stop(result)
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
                if args.live_owner:
                    print('S5_OWNER_ARMED_NO_GOAL: confirm only after checking Gazebo/RViz pose and clear path.',flush=True)
                    # A blocking input() starves this same single ROS executor.
                    # Keep spinning /scan, /odom and TF while the operator
                    # examines Gazebo/RViz before typing YES.
                    try:
                        approval_wait_s=wait_for_owner_approval(spin_once)
                    except Exception:
                        result['s5_owner_approval']={'authorized':False,'goal_sent':False}
                        args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                        raise
                    print('S5_OWNER_GOALS_AUTHORIZED WAIT_SEC='+
                          str(round(approval_wait_s,3)),flush=True)
                    try:
                        fresh=wait_for_fresh_sensors(
                            spin_once,
                            lambda:(state['scan'],state['odom_count'],
                                    state['scan_t'],state['odom_t']))
                    except Exception:
                        result['s5_owner_approval']={
                            'authorized':True,'goal_sent':False,
                            'freshness_verified':False,
                            'wait_seconds':round(approval_wait_s,3),
                            'scan_age_sec':round(time.monotonic()-state['scan_t'],3),
                            'odom_age_sec':round(time.monotonic()-state['odom_t'],3)}
                        args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                        raise
                    result['s5_owner_approval']={
                        'authorized':True,'goal_sent':False,
                        'freshness_verified':True,
                        'wait_seconds':round(approval_wait_s,3),**fresh}
                    args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                    print('S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL_PASS'+
                          ' SCAN_AGE_SEC='+str(fresh['scan_age_sec'])+
                          ' ODOM_AGE_SEC='+str(fresh['odom_age_sec'])+
                          ' APPROVAL_WAIT_SEC='+str(round(approval_wait_s,3)),flush=True)
                if args.menu_safety and s4_speed_pub.get_subscription_count()<1:
                    raise RuntimeError('S4_NAV2_SPEED_LIMIT_SUBSCRIBER_ABSENT_NO_GOAL')
                def goto(target,heading,label,menu=None):
                    if not (state['map_to_odom'] and state['odom_to_base'] and
                            state['amcl_pose'] is not None and state['scan']>=3):
                        raise RuntimeError('NAV_PREGOAL_NOT_READY_'+label)
                    if time.monotonic()-state['scan_t']>8 or time.monotonic()-state['odom_t']>8:
                        raise RuntimeError('NAV_PREGOAL_SENSOR_STALE_'+label)
                    if args.menu_safety:
                        if menu not in ('NORMAL','SOUP'):
                            raise RuntimeError('S4_MISSING_MENU_ON_NAV_GOAL')
                        s4['active_menu']=menu
                        def send_speed_limit():
                            msg_limit=SpeedLimit()
                            msg_limit.header.stamp=node.get_clock().now().to_msg()
                            msg_limit.percentage=False
                            msg_limit.speed_limit=(NORMAL_LIMIT if menu=='NORMAL' else SOUP_LIMIT)
                            s4_speed_pub.publish(msg_limit)
                        send_speed_limit()
                        last_limit=time.monotonic()
                        # Drain callbacks so Controller Server applies the limit before Goal.
                        for _ in range(6):spin_once(.15)
                        print('S4_NAV2_ABSOLUTE_SPEED_LIMIT='+menu+' MPS='+
                              str(NORMAL_LIMIT if menu=='NORMAL' else SOUP_LIMIT),flush=True)
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
                        if args.menu_safety and time.monotonic()-last_limit>1.0:
                            send_speed_limit()
                            last_limit=time.monotonic()
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
                    if args.menu_safety:s4['active_menu']=None
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
                legs=[goto(contract['table3_map_xy'],-math.pi/2,'TABLE_3',
                           menu='NORMAL' if args.menu_safety else None),
                      goto(contract['pickup_map_xy'],0.,'PICKUP_RETURN',
                           menu='SOUP' if args.menu_safety else None)]
                # The preflight result is NO_GOAL only until the action legs finish.
                result['kind']='s3_real_gazebo_navigation_delivery_return'
                result['goal_sent']=True
                result['real_nav_legs']=legs
                result['delivery_return']=True
                args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                print('RESTAURANT_S3_NAV02_REAL_GAZEBO_DELIVERY_RETURN_PASS',flush=True)
                if args.menu_safety:
                    normal=measured_speed('NORMAL',s4['speed_samples']['NORMAL'])
                    soup=measured_speed('SOUP',s4['speed_samples']['SOUP'])
                    measured=compare_speeds(normal,soup)
                    result['s4_menu_speed']=measured
                    result['kind']='s4_gazebo_menu_speed_pending_safety_stop'
                    args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                    print('S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS N_P75_MPS='+
                          str(normal['p75_mps'])+' S_P75_MPS='+str(soup['p75_mps']),flush=True)

                    perform_s4_stop(result)
                    print('RESTAURANT_S4_MENU01_REAL_GAZEBO_PASS',flush=True)
                    if args.s5_integrated:
                        result['kind']='s5_live01_real_gazebo_integration'
                        result['s5_integrated']=bool(result.get('delivery_return')
                           and result.get('s4_menu_speed') and result.get('s4_safety_stop')
                           and result.get('manual_initial_pose_published') is False)
                        if not result['s5_integrated']:
                            raise RuntimeError('S5_INTEGRATED_EVIDENCE_INCOMPLETE')
                        args.evidence.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
                        print('S5_LIVE01_REAL_GAZEBO_L2_INTEGRATED_PASS',flush=True)
                        if args.live_owner:
                            print('S5_LIVE_GUI_HOLD: inspect Gazebo/RViz; Ctrl+C to close and package evidence.',flush=True)
                            while True:spin_once(.25)
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
            # Include recent lifecycle transitions; avoid preserving massive ROS logs.
            transitions=[line[:400] for line in lines
                         if any(w in line for w in ('lifecycle_manager_navigation',
                                                 'bt_navigator','planner_server'))
                         and any(k in line.lower() for k in
                                 ('configur','activat','transition','bond','error','fail'))
                         and 'sending signal' not in line.lower()]
            (args.log.parent/'ci-s3-summary.txt').write_text(
                'FIRST_60_DIAGNOSTIC_LINES\n'+'\n'.join(clues[:60])+
                '\nNAV2_TRANSITIONS_LAST_60\n'+'\n'.join(transitions[-60:])+
                '\nLAST_60_LINES\n'+'\n'.join(lines[-60:])+'\n')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--exercise-goals',action='store_true')
    p.add_argument('--menu-safety',action='store_true')
    p.add_argument('--s4-stop-only',action='store_true')
    p.add_argument('--no-initial-pose-publish',action='store_true')
    p.add_argument('--s5-integrated',action='store_true')
    p.add_argument('--gui',action='store_true')
    p.add_argument('--live-owner',action='store_true')
    p.add_argument('--robot-sdf',type=Path,required=True)
    p.add_argument('--params',type=Path,required=True)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--log',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    run(p.parse_args())

if __name__=='__main__':main()
