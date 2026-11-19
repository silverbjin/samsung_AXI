"""One delivery/return using official Nav2 Simple Commander (NOT tested in WSL2)."""
import argparse
import math
import time
from pathlib import Path

import rclpy
from rclpy.parameter import Parameter
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PoseStamped
from nav2_msgs.msg import SpeedLimit
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
import yaml

from .menu_policy import read_policy


def pose_from_data(nav, item):
    p=PoseStamped()
    p.header.frame_id='map'
    p.header.stamp=nav.get_clock().now().to_msg()
    p.pose.position.x=float(item['x'])
    p.pose.position.y=float(item['y'])
    yaw=float(item['yaw'])
    p.pose.orientation.z=math.sin(yaw/2.0)
    p.pose.orientation.w=math.cos(yaw/2.0)
    return p


class SensorEvidence:
    def __init__(self):
        self.scan_count=0
        self.odom=[]

    def scan_cb(self, msg:LaserScan):
        if msg.ranges: self.scan_count+=1

    def odom_cb(self, msg:Odometry):
        xy=(float(msg.pose.pose.position.x),float(msg.pose.pose.position.y))
        if not self.odom or math.dist(xy,self.odom[-1])>0.01:
            self.odom.append(xy)

    def displacement(self):
        if len(self.odom)<2:return 0.0
        return max(math.dist(self.odom[0],p) for p in self.odom)


def run(menu, auto_return=False):
    world_share=Path(get_package_share_directory('restaurant_world'))
    delivery_share=Path(get_package_share_directory('restaurant_delivery'))
    layout=yaml.safe_load((world_share/'config/tables.yaml').read_text())
    policies=yaml.safe_load((delivery_share/'config/menu.yaml').read_text())
    policy=read_policy(policies,menu)
    if layout.get('frame')!='map':raise RuntimeError('MAP_FRAME_REQUIRED')

    rclpy.init()
    nav=BasicNavigator(node_name='restaurant_delivery_navigator')
    nav.set_parameters([Parameter('use_sim_time',Parameter.Type.BOOL,True)])
    evidence=SensorEvidence()
    nav.create_subscription(Odometry,'/odom',evidence.odom_cb,10)
    nav.create_subscription(LaserScan,'/scan',evidence.scan_cb,10)
    pub=nav.create_publisher(SpeedLimit,'/speed_limit',10)

    def publish_limit():
        msg=SpeedLimit()
        msg.header.stamp=nav.get_clock().now().to_msg()
        msg.header.frame_id='map'
        msg.percentage=False
        msg.speed_limit=float(policy.max_speed_mps)
        pub.publish(msg)

    try:
        print('RESTAURANT_DELIVERY_STAGE=PREGOAL_NO_GOAL',flush=True)
        start=time.monotonic()
        while (evidence.scan_count<1 or not evidence.odom) and time.monotonic()-start < 40.0:
            rclpy.spin_once(nav,timeout_sec=0.25)
        if evidence.scan_count<1 or not evidence.odom:
            raise RuntimeError('PREGOAL_MISSING_REAL_SCAN_OR_ODOM')

        pickup=pose_from_data(nav,layout['pickup'])
        nav.setInitialPose(pickup)
        nav.waitUntilNav2Active(localizer='amcl')
        if nav.count_subscribers('/speed_limit')<1:
            raise RuntimeError('NAV2_SPEED_LIMIT_SUBSCRIBER_ABSENT_NO_GOAL')
        publish_limit()
        print(f'RESTAURANT_MENU={policy.name} SPEED_LIMIT_MPS={policy.max_speed_mps}',flush=True)
        for target,label in [(layout['table_3'],'TABLE_3'),(layout['pickup'],'PICKUP_RETURN')]:
            count_before=len(evidence.odom)
            # Reset segment reference; record genuine motion, not a Path-only display.
            segment_start=evidence.odom[-1] if evidence.odom else None
            goal=pose_from_data(nav,target)
            print(f'RESTAURANT_GOAL_SENT={label}',flush=True)
            nav.goToPose(goal)
            while not nav.isTaskComplete():
                publish_limit()  # repeated while the action is active, not a new /cmd_vel source
            result=nav.getResult()
            moved=max((math.dist(segment_start,p) for p in evidence.odom[count_before:]),default=0.0) if segment_start else 0.0
            print(f'RESTAURANT_GOAL_RESULT={label} RESULT={result} ODOM_MAX_DISPLACEMENT_M={moved:.2f}',flush=True)
            if result!=TaskResult.SUCCEEDED or moved<0.25:
                raise RuntimeError(f'GOAL_OR_PHYSICAL_ODOM_NOT_PROVEN:{label}')
            if label=='TABLE_3':
                print('RESTAURANT_DELIVERY_STATE=DELIVERED',flush=True)
                if not auto_return:
                    input('테이블 3 수령 확인 후 Enter를 누르세요 (자동 복귀는 --auto-return): ')
        print('RESTAURANT_DELIVERY_STATE=RETURNED',flush=True)
        print('RESTAURANT_S3_RESULT=PHYSICAL_ODOM_AND_ACTION_SUCCESS_CANDIDATE_NEEDS_GUI_CHECK',flush=True)
    except KeyboardInterrupt:
        nav.cancelTask()
        print('RESTAURANT_DELIVERY_ABORTED=CTRL_C',flush=True)
        raise
    finally:
        nav.destroy_node()
        if rclpy.ok():rclpy.shutdown()


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--menu',choices=['NORMAL','SOUP'],default='NORMAL')
    p.add_argument('--auto-return',action='store_true')
    args=p.parse_args()
    try:run(args.menu,args.auto_return)
    except (RuntimeError,EOFError) as e:
        print('RESTAURANT_DELIVERY_BLOCKED='+str(e),flush=True)
        raise SystemExit(1)

if __name__=='__main__':main()
