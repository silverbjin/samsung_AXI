#!/usr/bin/env python3
"""CI ONLY: physically survey restaurant using real Gazebo scan/odom/SLAM.

No simulated /map publisher; no Nav2 Goal. Uses fixed SDF-vetted movement
segments for mapping evidence, not a replacement for Nav2 planning.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from s2_map02_contract import (
    START,SURVEY,TABLE3_APPROACH,coverage,from_world_to_odom,
    map_coordinates,free_path_connected,route_clearance,
)
from ci_s2_map_smoke import end_process,check_map_yaml

def angle(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def wrap(a):
    return math.atan2(math.sin(a),math.cos(a))
def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def short_log(p,dst):
    lines=p.read_text(errors='replace').splitlines() if p.is_file() else []
    hints=[x[:450] for x in lines if any(k in x.lower() for k in ('error','warn','fail','exception','timeout','slam_toolbox'))]
    dst.write_text('FIRST_40_DIAGNOSTIC_LINES\n'+'\n'.join(hints[:40])+'\nLAST_70_LINES\n'+'\n'.join(lines[-70:])+'\n')

def run(args):
    import rclpy
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import OccupancyGrid,Odometry
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import LaserScan
    from tf2_msgs.msg import TFMessage
    from nav2_msgs.srv import SaveMap
    from lifecycle_msgs.srv import ChangeState
    from lifecycle_msgs.msg import Transition

    root=Path(__file__).resolve().parents[1]
    world=root/'src/restaurant_world/worlds/restaurant.sdf'
    violations=route_clearance(world)
    if violations:raise RuntimeError('SURVEY_COLLISION_GEOMETRY:'+str(violations[:2]))
    if not args.robot_sdf.is_file():raise RuntimeError('ROBOT_SDF_MISSING')
    prefix=args.map_prefix.resolve()
    prefix.parent.mkdir(parents=True,exist_ok=True)
    args.log.parent.mkdir(parents=True,exist_ok=True)
    state={'clock':False,'scan_count':0,'scan_t':0.,'scan':None,
           'initial':None,'odom':None,'odom_t':0.,
           'map':None,'map_count':0,'tf':None,'reloaded':None}
    launched=reload_proc=node=pub=None
    started=False
    finished=[]
    def odom_cb(m):
        xy=(m.pose.pose.position.x,m.pose.pose.position.y,angle(m.pose.pose.orientation))
        state['odom']=xy;state['odom_t']=time.monotonic()
        if state['initial'] is None:state['initial']=xy
    def scan_cb(m):
        if len(m.ranges)>=10 and any(math.isfinite(x) and x>0 for x in m.ranges):
            state['scan_count']+=1;state['scan_t']=time.monotonic();state['scan']=m
    def map_cb(m):
        state['map']=m;state['map_count']+=1
    def tf_cb(m):
        for t in m.transforms:
            if t.header.frame_id=='map' and t.child_frame_id=='odom':
                state['tf']=(t.transform.translation.x,t.transform.translation.y,angle(t.transform.rotation))
    def spin_once(dt=.13):
        if launched is not None and launched.poll() is not None:
            raise RuntimeError('GAZEBO_SLAM_LAUNCH_EXITED:'+str(launched.returncode))
        rclpy.spin_once(node,timeout_sec=dt)
    def wait_for(fn,seconds,label):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            spin_once()
            if fn():return
        raise RuntimeError('TIMEOUT_'+label)
    def stop():
        if pub is None:return
        for _ in range(5):
            pub.publish(Twist())
            try:rclpy.spin_once(node,timeout_sec=.09)
            except Exception:break
    def front_distance(scan):
        if scan is None:return math.inf
        result=[]
        for i,d in enumerate(scan.ranges):
            a=wrap(scan.angle_min+i*scan.angle_increment)
            if abs(a)<=.40 and math.isfinite(d) and d>0:
                result.append(d)
        return min(result,default=math.inf)
    def drive(target_world,step):
        tx,ty=from_world_to_odom(target_world,state['initial'])
        deadline=time.monotonic()+140
        best=math.inf;progress_t=time.monotonic()
        while time.monotonic()<deadline:
            spin_once(.09)
            if not state['odom']:continue
            x,y,yaw=state['odom']
            distance=math.hypot(tx-x,ty-y)
            if distance<.16:
                stop();finished.append(dict(step=step,world=list(target_world),error_m=round(distance,3)))
                print('S2_MAP02_WAYPOINT_PASS='+str(step)+' ERROR_M='+str(round(distance,3)),flush=True)
                return
            if time.monotonic()-state['scan_t']>7 or time.monotonic()-state['odom_t']>7:
                raise RuntimeError('SCAN_OR_ODOM_STALE_'+str(step))
            if distance < best-.045:best=distance;progress_t=time.monotonic()
            if time.monotonic()-progress_t>22:
                raise RuntimeError('WAYPOINT_STALL_'+str(step)+' remaining='+str(round(distance,3)))
            desired=math.atan2(ty-y,tx-x)
            diff=wrap(desired-yaw)
            cmd=Twist()
            if abs(diff)>.22:
                cmd.angular.z=max(-.7,min(.7,1.7*diff))
            else:
                if front_distance(state['scan'])<.40:
                    raise RuntimeError('LIDAR_FORWARD_CLEARANCE_BLOCKED_'+str(step))
                cmd.linear.x=min(.23,max(.10,.8*distance))
                cmd.angular.z=max(-.48,min(.48,1.2*diff))
            pub.publish(cmd)
        raise RuntimeError('WAYPOINT_DEADLINE_'+str(step))
    def call(client,request,label,sec=30):
        if not client.wait_for_service(timeout_sec=sec):raise RuntimeError('SERVICE_ABSENT_'+label)
        future=client.call_async(request)
        rclpy.spin_until_future_complete(node,future,timeout_sec=sec)
        if not future.done() or future.exception():raise RuntimeError('SERVICE_FAILED_'+label)
        return future.result()
    try:
        with args.log.open('w') as out:
            launched=subprocess.Popen(
                ['ros2','launch','restaurant_bringup','mapping.launch.py',
                 'gui:=false','robot_sdf:='+str(args.robot_sdf.resolve())],
                stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
            rclpy.init(args=None);started=True
            node=rclpy.create_node('samsungaxi_s2_map02_ci_survey')
            qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,
                           durability=DurabilityPolicy.TRANSIENT_LOCAL)
            node.create_subscription(Clock,'/clock',lambda m:state.update(clock=m.clock.sec>0),qos_profile_sensor_data)
            node.create_subscription(LaserScan,'/scan',scan_cb,qos_profile_sensor_data)
            node.create_subscription(Odometry,'/odom',odom_cb,qos_profile_sensor_data)
            node.create_subscription(TFMessage,'/tf',tf_cb,qos_profile_sensor_data)
            node.create_subscription(OccupancyGrid,'/map',map_cb,qos)
            node.create_subscription(OccupancyGrid,'/restaurant/map02_reloaded',lambda m:state.update(reloaded=m),qos)
            pub=node.create_publisher(Twist,'/cmd_vel',10)
            wait_for(lambda:state['clock'] and state['scan_count']>=3 and state['map'] is not None
                     and state['tf'] is not None and state['initial'] is not None,200,'SENSOR_SLAM_MAP_TF')
            print('S2_MAP02_ACTUAL_GAZEBO_SURVEY_STARTED',flush=True)
            try:
                for i,target in enumerate(SURVEY[1:],1):drive(target,i)
            finally:
                stop()
            before=state['map_count']
            wait_for(lambda:state['map_count']>=before+2,35,'SLAM_FINAL_UPDATE')
            metrics=coverage(state['map'])
            pickup=map_coordinates(from_world_to_odom(START,state['initial']),state['tf'])
            target=map_coordinates(from_world_to_odom(TABLE3_APPROACH,state['initial']),state['tf'])
            if not free_path_connected(state['map'],pickup,target):
                raise RuntimeError('PICKUP_TO_TABLE3_FREE_SPACE_DISCONNECTED_OR_UNKNOWN')
            metrics.update(route_waypoints=len(finished),route_length_m=round(sum(math.dist(a,b) for a,b in zip(SURVEY,SURVEY[1:])),3),
                           pickup_free_connected_to_table3=True,sensor_scans=state['scan_count'])
            print('S2_MAP02_COVERAGE='+json.dumps(metrics,sort_keys=True),flush=True)
            save=node.create_client(SaveMap,'/map_saver/save_map')
            req=SaveMap.Request()
            req.map_topic='/map';req.map_url=str(prefix);req.image_format='pgm';req.map_mode='trinary'
            req.free_thresh=.25;req.occupied_thresh=.65
            if not call(save,req,'SAVE_MAP').result:raise RuntimeError('SAVE_MAP_FALSE')
            yaml_file=prefix.with_suffix('.yaml')
            image=check_map_yaml(yaml_file)
            reload_proc=subprocess.Popen(
                ['ros2','run','nav2_map_server','map_server','--ros-args',
                 '-r','__node:=restaurant_map02_reload','-r','map:=/restaurant/map02_reloaded',
                 '-p','yaml_filename:='+str(yaml_file),'-p','use_sim_time:=true'],
                stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
            client=node.create_client(ChangeState,'/restaurant_map02_reload/change_state')
            for transition,label in ((Transition.TRANSITION_CONFIGURE,'CONFIGURE'),(Transition.TRANSITION_ACTIVATE,'ACTIVATE')):
                r=ChangeState.Request();r.transition.id=transition
                if not call(client,r,'RELOAD_'+label).success:raise RuntimeError('RELOAD_REJECTED_'+label)
            wait_for(lambda:state['reloaded'] is not None and len(state['reloaded'].data)==len(state['map'].data),35,'RELOADED_GRID')
            if not free_path_connected(state['reloaded'],pickup,target):
                raise RuntimeError('RELOADED_MAP_FREE_PATH_INVALID')
            quality=prefix.parent/'map02_quality.json'
            quality.write_text(json.dumps({
                'scope':'real_gazebo_survey_slam_toolbox_save_reload',
                'not_guaranteed':'Nav2_AMCL_or_complete_coverage_of_every_corner',
                'world_sha256':sha256(world),'sdf_sha256':sha256(args.robot_sdf),
                'map_yaml_sha256':sha256(yaml_file),'map_image_sha256':sha256(image),
                'map':metrics,'waypoints':finished
            },indent=2,sort_keys=True)+'\n')
            print('RESTAURANT_S2_MAP02_L2_FULL_COVERAGE_PASS='+str(quality),flush=True)
    except Exception as exc:
        print('RESTAURANT_S2_MAP02_BLOCKED='+str(exc),file=sys.stderr,flush=True)
        raise
    finally:
        stop()
        end_process(reload_proc);end_process(launched)
        if node is not None:node.destroy_node()
        if started and rclpy.ok():rclpy.shutdown()
        short_log(args.log,args.log.parent/'ci-s2-map02-summary.txt')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--robot-sdf',type=Path,required=True)
    p.add_argument('--map-prefix',type=Path,required=True)
    p.add_argument('--log',type=Path,required=True)
    args=p.parse_args()
    run(args)

if __name__=='__main__':main()
