#!/usr/bin/env python3
"""Generate one local Nav2 params overlay; preserve official Jazzy stack.

Connect RGB-D PointCloud2 to local costmap (scan remains in global+local+CM).
The resulting configuration MUST be checked with live ROS topic/TF and CM.
"""
import argparse
from pathlib import Path
import yaml


def build(src:Path,dst:Path):
    params=yaml.safe_load(src.read_text())
    voxel=params['local_costmap']['local_costmap']['ros__parameters']['voxel_layer']
    voxel['observation_sources']='scan rgbd'
    voxel['rgbd']={
        'topic':'/restaurant/rgbd/points', 'data_type':'PointCloud2',
        'marking':True,'clearing':False,
        'max_obstacle_height':1.6, 'obstacle_max_range':2.5,
        'obstacle_min_range':0.05,
    }
    # S4: external Nav2 SpeedLimit publisher is '/speed_limit' (absolute m/s).
    # Controller Server's official default is relative 'speed_limit', so pin it.
    params['controller_server']['ros__parameters']['speed_limit_topic']='/speed_limit'

    # Reuse official Nav2 Collision Monitor filtering cmd_vel_smoothed -> cmd_vel.
    # Keep the official FootprintApproach and add one minimal LiDAR stop zone.
    cm=params['collision_monitor']['ros__parameters']
    assert cm['cmd_vel_in_topic']=='cmd_vel_smoothed'
    assert cm['cmd_vel_out_topic']=='cmd_vel'
    assert 'FootprintApproach' in cm['polygons']
    cm['state_topic']='/collision_monitor_state'
    cm['polygons']=['S4ForwardStop']+list(cm['polygons'])
    cm['S4ForwardStop']={
        'type':'polygon',
        'points':'[[0.10,0.28],[0.58,0.28],[0.58,-0.28],[0.10,-0.28]]',
        'action_type':'stop','min_points':4,'visualize':False,'enabled':True
    }
    # Existing observation_sources=['scan'] and original source_timeout stay intact.
    # Explicitly declare Jazzy Twist behavior and the single collision-monitor output.
    params['controller_server']['ros__parameters']['enable_stamped_cmd_vel']=False
    params['collision_monitor']['ros__parameters']['enable_stamped_cmd_vel']=False
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text('# Official Nav2 Jazzy params with MINIMAL restaurant overlay.\n'
                   + yaml.safe_dump(params,sort_keys=False))
    print('RESTAURANT_NAV2_PARAMS_STATIC_OK',dst)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.source,a.out)

if __name__=='__main__':main()
