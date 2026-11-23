#!/usr/bin/env python3
"""Generate one local Nav2 params overlay; preserve official Jazzy stack.

Use the existing official Nav2 LaserScan voxel source for local costmap.
Keep the independent LiDAR Collision Monitor unchanged; verify live ROS/TF.
"""
import argparse
from pathlib import Path
import yaml


def apply_s6_ack_ms(params,ms):
    """S6-only BT action-server *acknowledgement* timeout; no safety relaxation."""
    if ms is None:return params
    if not isinstance(ms,int) or not 20<=ms<=500:
        raise ValueError('S6_BT_ACK_TIMEOUT_OUT_OF_BOUNDS')
    bt=params.get('bt_navigator',{}).get('ros__parameters',{})
    if 'default_server_timeout' not in bt:
        raise RuntimeError('S6_BT_DEFAULT_SERVER_TIMEOUT_MISSING')
    bt['default_server_timeout']=ms
    return params

def build(src:Path,dst:Path,auto_initial_pose=False,s6_bt_ack_ms=None):
    params=yaml.safe_load(src.read_text())
    voxel=params['local_costmap']['local_costmap']['ros__parameters']['voxel_layer']
    # Keep the official LaserScan source and its existing marking/clearing and
    # raytrace settings; do not bring PointCloud2 into 2D restaurant navigation.
    scan=voxel.get('scan')
    if not isinstance(scan,dict) or scan.get('data_type')!='LaserScan' or scan.get('topic') not in ('scan','/scan'):
        raise RuntimeError('S5_COSTMAP_OFFICIAL_LIDAR_SCAN_SOURCE_MISSING')
    voxel['observation_sources']='scan'
    voxel.pop('rgbd',None)  # Reapplying an overlay cannot retain stale RGB-D.

    if auto_initial_pose:
        # Map pickup is (0, 0, yaw=0); use official AMCL on GUI launch.
        amcl=params['amcl']['ros__parameters']
        amcl['set_initial_pose']=True
        amcl['initial_pose']={'x':0.0,'y':0.0,'z':0.0,'yaw':0.0}
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
    apply_s6_ack_ms(params,s6_bt_ack_ms)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text('# Official Nav2 Jazzy params with MINIMAL restaurant overlay.\n'
                   + yaml.safe_dump(params,sort_keys=False))
    print('S5_COSTMAP_SCAN_ONLY_STATIC_PASS',dst)
    print('RESTAURANT_NAV2_PARAMS_STATIC_OK',dst)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--auto-initial-pose',action='store_true')
    p.add_argument('--s6-bt-ack-ms',type=int,default=None)
    a=p.parse_args()
    build(a.source,a.out,auto_initial_pose=a.auto_initial_pose,
          s6_bt_ack_ms=a.s6_bt_ack_ms)

if __name__=='__main__':main()
