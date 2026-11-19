"""Gazebo-only world Pose input for S2 CI survey; never injected into ROS SLAM/TF."""
import math
import re
import subprocess
import threading
import time

_NUMBER=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'

def parse_waffle_pose(block):
    if not re.search(r'(?m)^\s*name:\s*"waffle_pi"\s*$',block):
        return None
    def section(kind):
        found=re.search(r'\b'+kind+r'\s*\{([^{}]*)\}',block,re.S)
        if found is None:raise ValueError('GZ_'+kind+'_MISSING')
        return found.group(1)
    def number(s,key,default=None):
        found=re.search(r'(?m)^\s*'+key+r':\s*('+_NUMBER+r')\s*$',s)
        if found is None:
            if default is not None:return default
            raise ValueError('GZ_'+key+'_MISSING')
        return float(found.group(1))
    position=section('position');rotation=section('orientation')
    x,y=number(position,'x'),number(position,'y')
    qx,qy=number(rotation,'x',0),number(rotation,'y',0)
    qz,qw=number(rotation,'z',0),number(rotation,'w',1)
    return (x,y,math.atan2(2*(qw*qz+qx*qy),1-2*(qy*qy+qz*qz)))

def stream_pose_v(lines,consume):
    in_pose=False;level=0;block=[]
    for line in lines:
        if not in_pose:
            if re.match(r'^\s*pose\s*\{\s*$',line):
                in_pose=True;block=[line];level=line.count('{')-line.count('}')
            continue
        block.append(line)
        level+=line.count('{')-line.count('}')
        if level<=0:
            content=''.join(block)
            in_pose=False;block=[]
            if '"waffle_pi"' in content:
                candidate=parse_waffle_pose(content)
                if candidate is not None:consume(candidate)

class GazeboModelPose:
    def __init__(self):
        self.pose=None
        self.updated=0.
        self.samples=0
        self.process=None
        self.thread=None
        self.error=None
    def start(self):
        self.process=subprocess.Popen(
            ['gz','topic','-e','-t','/world/restaurant/pose/info'],
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
            text=True,bufsize=1,start_new_session=True)
        def consume(pose):
            self.pose=pose
            self.updated=time.monotonic()
            self.samples+=1
        def worker():
            try:stream_pose_v(self.process.stdout,consume)
            except Exception as err:self.error=str(err)
        self.thread=threading.Thread(target=worker,daemon=True,name='samsungaxi_gt_pose')
        self.thread.start()
    def fresh(self,seconds=4.0):
        return (self.error is None and self.pose is not None and
                time.monotonic()-self.updated<seconds)
    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill();self.process.wait()
        if self.thread:self.thread.join(timeout=2)

def world_to_map_point(point,gt,odom,map_tf):
    """World to SLAM map using simultaneous live GT, wheel odom, and map->odom TF."""
    x0,y0,yaw0=gt
    tx,ty,tfyaw=map_tf
    ox,oy,oyaw=odom
    mx=tx+math.cos(tfyaw)*ox-math.sin(tfyaw)*oy
    my=ty+math.sin(tfyaw)*ox+math.cos(tfyaw)*oy
    rot=tfyaw+oyaw-yaw0
    dx=point[0]-x0;dy=point[1]-y0
    return (mx+math.cos(rot)*dx-math.sin(rot)*dy,
            my+math.sin(rot)*dx+math.cos(rot)*dy)
