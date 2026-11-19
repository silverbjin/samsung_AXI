"""Gazebo Pose_V parser and GT/map calibration; no ROS/Gazebo runtime needed."""
import importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gt',ROOT/'scripts/s2_map02_gt_pose.py')
gt=importlib.util.module_from_spec(spec);spec.loader.exec_module(gt)
POSE='''pose {
 name: "waffle_pi"
 id: 75
 position {
  x: -3.186499
  y: 1.85599
 }
 orientation {
  x: 0.00187
  y: -0.00214
  z: 0.658367
  w: 0.752691
 }
}'''
def test_real_pose_v_parser():
    a=gt.parse_waffle_pose(POSE)
    assert abs(a[0]+3.186499)<.0001
    assert abs(a[1]-1.85599)<.0001
    assert 1.2<a[2]<1.6
    assert gt.parse_waffle_pose(POSE.replace('waffle_pi','chair_4')) is None
    observed=[]
    gt.stream_pose_v(iter((POSE+'\n').splitlines(True)),observed.append)
    assert len(observed)==1 and observed[0]==a
def test_world_to_map_anchor():
    assert gt.world_to_map_point((1.,2.),(0.,0.,0.),(0.,0.,0.),(0.,0.,0.))==(1.,2.)
    assert gt.world_to_map_point((1.,2.),(0.,0.,0.),(0.,0.,0.),(3.,4.,0.))==(4.,6.)
    assert gt.world_to_map_point((0.,0.),(1.,1.,0.),(0.,0.,0.),(0.,0.,0.))==(-1.,-1.)
