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
