#!/usr/bin/env python3
"""Real ROS2 Gazebo S2: Scan/Odom/TF -> SLAM /map -> SaveMap -> Map Server reload.

This is one short safe physical mapping segment. Whole-room coverage is NOT asserted.
"""
import argparse
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

def valid_grid(m):
    i=m.info
    return i.width>=8 and i.height>=8 and i.resolution>0 and len(m.data)==i.width*i.height and sum(v>=0 for v in m.data)>=100

def check_map_yaml(path):
    import yaml
    v=yaml.safe_load(path.read_text())
    for key in ('image','resolution','origin','negate','occupied_thresh','free_thresh'):
        if key not in v:raise RuntimeError('MAP_YAML_FIELD_MISSING_'+key)
    image=(path.parent/v['image']).resolve()
    if not image.is_relative_to(path.parent.resolve()) or not image.is_file() or image.stat().st_size<100:
        raise RuntimeError('MAP_IMAGE_MISSING_OR_EMPTY')
    return image

def end_process(p):
    if p is None or p.poll() is not None:return
    for sig,timeout in ((signal.SIGINT,10),(signal.SIGTERM,5)):
        try:
            os.killpg(p.pid,sig);p.wait(timeout=timeout);return
        except (ProcessLookupError,subprocess.TimeoutExpired):pass
    os.killpg(p.pid,signal.SIGKILL);p.wait()

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--robot-sdf',type=Path,required=True)
    a.add_argument('--map-prefix',type=Path,required=True)
    a.add_argument('--log',type=Path,required=True)
    args=a.parse_args()
    if not args.robot_sdf.is_file():raise SystemExit('S2_BLOCKED_ROBOT_SDF_MISSING')
    args.log.parent.mkdir(parents=True,exist_ok=True)
    path=args.map_prefix.resolve();path.parent.mkdir(parents=True,exist_ok=True)
    import rclpy
    from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
    from geometry_msgs.msg import Twist
    from nav_msgs.msg import OccupancyGrid,Odometry
    from sensor_msgs.msg import LaserScan
    from rosgraph_msgs.msg import Clock
    from tf2_msgs.msg import TFMessage
    from nav2_msgs.srv import SaveMap
    from lifecycle_msgs.srv import ChangeState
    from lifecycle_msgs.msg import Transition
    state={'clock':False,'scan':0,'start':None,'position':None,'map':None,'tf':False,'reloaded':None}
    launch=reload_proc=node=pub=None
    initialized=False
    def on_odom(m):
        xy=(m.pose.pose.position.x,m.pose.pose.position.y)
        state['position']=xy
        if state['start'] is None:state['start']=xy
    def on_scan(m):
        if len(m.ranges)>10 and any(math.isfinite(x) for x in m.ranges):state['scan']+=1
    def on_tf(m):
        if any(t.header.frame_id=='map' and t.child_frame_id=='odom' for t in m.transforms):state['tf']=True
    def on_map(m):
        if valid_grid(m):state['map']=m
    def displacement():
        a,b=state['start'],state['position']
        return math.dist(a,b) if a is not None and b is not None else 0.0
    def spin_until(check,seconds,label):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if launch.poll() is not None:raise RuntimeError('MAPPING_LAUNCH_EXITED_'+str(launch.returncode))
            rclpy.spin_once(node,timeout_sec=.3)
            if check():return
        raise RuntimeError('TIMEOUT_WAIT_'+label)
    def call_service(client,req,label,timeout=25):
        if not client.wait_for_service(timeout_sec=timeout):raise RuntimeError('SERVICE_NOT_FOUND_'+label)
        fut=client.call_async(req)
        rclpy.spin_until_future_complete(node,fut,timeout_sec=timeout)
        if not fut.done() or fut.exception():raise RuntimeError('SERVICE_FAILED_'+label)
        return fut.result()
    try:
        with args.log.open('w') as out:
            launch=subprocess.Popen(['ros2','launch','restaurant_bringup','mapping.launch.py',
                                     'gui:=false','robot_sdf:='+str(args.robot_sdf.resolve())],
                                    stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
            rclpy.init(args=None);initialized=True
            node=rclpy.create_node('samsungaxi_s2_real_map_probe')
            q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
            subs=[
              node.create_subscription(Clock,'/clock',lambda m:state.update(clock=m.clock.sec>0),qos_profile_sensor_data),
              node.create_subscription(LaserScan,'/scan',on_scan,qos_profile_sensor_data),
              node.create_subscription(Odometry,'/odom',on_odom,qos_profile_sensor_data),
              node.create_subscription(OccupancyGrid,'/map',on_map,q),
              node.create_subscription(TFMessage,'/tf',on_tf,qos_profile_sensor_data),
              node.create_subscription(OccupancyGrid,'/restaurant/map_reloaded',lambda m:state.update(reloaded=m),q)]
            pub=node.create_publisher(Twist,'/cmd_vel',10)
            spin_until(lambda:state['clock'] and state['scan']>1 and state['position'] is not None and state['map'] is not None and state['tf'],175,'MAP_SCAN_ODOM_TF')
            print('S2_REAL_GAZEBO_SCAN_MAP_TF_RECEIVED',flush=True)
            forward=Twist();forward.linear.x=.09
            t0=time.monotonic()
            try:
                while time.monotonic()-t0<85 and displacement()<.38:
                    if launch.poll() is not None:raise RuntimeError('MAPPING_EXITED_DURING_MOTION')
                    pub.publish(forward);rclpy.spin_once(node,timeout_sec=.15)
                if displacement()<.30:raise RuntimeError('PHYSICAL_ODOM_NOT_MOVING_'+str(round(displacement(),3)))
            finally:
                for _ in range(5):pub.publish(Twist());rclpy.spin_once(node,timeout_sec=.15)
            for _ in range(12):rclpy.spin_once(node,timeout_sec=.2)
            print('S2_REAL_ODOM_DISPLACEMENT_M='+str(round(displacement(),3)),flush=True)
            save=node.create_client(SaveMap,'/map_saver/save_map')
            req=SaveMap.Request()
            req.map_topic='/map';req.map_url=str(path);req.image_format='pgm';req.map_mode='trinary';req.free_thresh=.25;req.occupied_thresh=.65
            if not call_service(save,req,'OFFICIAL_MAP_SAVER').result:raise RuntimeError('SAVE_MAP_RESULT_FALSE')
            yaml_file=path.with_suffix('.yaml')
            if not yaml_file.is_file():raise RuntimeError('MAP_YAML_FILE_NOT_CREATED')
            image=check_map_yaml(yaml_file)
            print('S2_OFFICIAL_SAVE_MAP_PASS='+str(yaml_file),flush=True)
            reload_proc=subprocess.Popen(['ros2','run','nav2_map_server','map_server','--ros-args',
                                          '-r','__node:=restaurant_map_reload',
                                          '-r','map:=/restaurant/map_reloaded',
                                          '-p','yaml_filename:='+str(yaml_file),'-p','use_sim_time:=true'],
                                         stdout=out,stderr=subprocess.STDOUT,start_new_session=True,env=os.environ.copy())
            lc=node.create_client(ChangeState,'/restaurant_map_reload/change_state')
            for transition,label in ((Transition.TRANSITION_CONFIGURE,'CONFIGURE'),(Transition.TRANSITION_ACTIVATE,'ACTIVATE')):
                request=ChangeState.Request();request.transition.id=transition
                if not call_service(lc,request,'MAP_RELOAD_'+label).success:raise RuntimeError('RELOAD_LIFECYCLE_'+label+'_REJECTED')
            spin_until(lambda:state['reloaded'] is not None and valid_grid(state['reloaded']),25,'MAP_SERVER_RELOAD')
            print('RESTAURANT_S2_L2_REAL_GAZEBO_SLAM_SAVE_RELOAD_PASS_NO_NAV_GOAL',flush=True)
    except Exception as e:
        print('RESTAURANT_S2_L2_BLOCKED='+str(e),file=sys.stderr,flush=True)
        raise
    finally:
        if pub is not None and node is not None:
            try:pub.publish(Twist());rclpy.spin_once(node,timeout_sec=.1)
            except Exception:pass
        end_process(reload_proc);end_process(launch)
        if node:node.destroy_node()
        if initialized and rclpy.ok():rclpy.shutdown()
        lines=args.log.read_text(errors='replace').splitlines() if args.log.exists() else []
        hints=[x[:300] for x in lines if any(q in x.lower() for q in ('error','warn','timeout','exception','failed','slam_toolbox'))]
        (args.log.parent/'ci-s2-summary.txt').write_text('FIRST_35_WARN_OR_ERROR\n'+'\n'.join(hints[:35])+'\nLAST_65_LINES\n'+'\n'.join(lines[-65:])+'\n')
if __name__=='__main__':main()
