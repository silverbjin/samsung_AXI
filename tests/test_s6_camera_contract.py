"""S6-00/CAMERA-01: isolated contracts only; real image requires CI L2."""
from pathlib import Path
import importlib.util
from xml.etree import ElementTree as ET
import yaml

ROOT=Path(__file__).resolve().parents[1]
def load(path,name):
    s=importlib.util.spec_from_file_location(name,ROOT/path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_s6_dish_fixture_real_sdf_and_table_proximity():
    m=load('scripts/s6_scene.py','s6_fixture')
    root=ET.fromstring(m.fixture_sdf())
    assert root.find(".//model[@name='s6_stacked_dishes']") is not None
    names=[x.get('name') for x in root.findall('.//visual')]
    assert len(names)==6 and 'plate_0' in names and 'plate_2' in names
    assert abs(m.FIXTURE_WORLD_XY[0]-m.TABLE3_WORLD_XY[0])<.2
    assert abs(m.FIXTURE_WORLD_XY[1]-m.TABLE3_WORLD_XY[1])<.5
    assert all(float(x.findtext('geometry/cylinder/radius'))>0
               for x in root.findall('.//visual'))

def test_s6_lazy_bridge_keeps_identical_nav_and_cm_topics():
    a=yaml.safe_load((ROOT/'src/restaurant_bringup/config/bridge.yaml').read_text())
    b=yaml.safe_load((ROOT/'src/restaurant_bringup/config/bridge_vision_on_demand.yaml').read_text())
    a={e['ros_topic_name']:e for e in a}
    b={e['ros_topic_name']:e for e in b}
    protected={'/clock','/joint_states','/odom','/tf','/cmd_vel','/imu','/scan'}
    assert protected<=set(b)
    for topic in protected:assert b[topic]==a[topic]
    for topic in ('/restaurant/rgbd/image','/restaurant/rgbd/camera_info'):
        assert b[topic]['lazy'] is True
        assert b[topic]['direction']=='GZ_TO_ROS'
    assert '/restaurant/rgbd/points' not in b
    assert '/restaurant/rgbd/depth_image' not in b
    assert set(b)==protected|{'/restaurant/rgbd/image','/restaurant/rgbd/camera_info'}

def test_s6_world_launch_has_opt_in_preserving_s5_defaults():
    text=(ROOT/'src/restaurant_bringup/launch/world.launch.py').read_text()
    assert "default_value=os.path.join(here,'config','bridge.yaml')" in text
    assert "DeclareLaunchArgument('spawn_x',default_value='-2.60')" in text
    assert "DeclareLaunchArgument('spawn_y',default_value='-2.20')" in text
    assert "DeclareLaunchArgument('spawn_yaw',default_value='0')" in text

def test_s6_image_difference_is_not_misrepresented_as_ai():
    m=load('scripts/s6_camera_scene_ci.py','s6_capture')
    assert m.diff_fraction(bytes([0,0,0]*4),bytes([255,255,255]*4))==1.0
    assert m.diff_fraction(bytes([0,0,0]*4),bytes([0,0,0]*4))==0.0
    text=(ROOT/'scripts/s6_camera_scene_ci.py').read_text()
    assert "'vision_ai_inference':'NOT_RUN'" in text
    assert 'node.destroy_subscription(subscriber)' in text
    assert 'S6_00_REAL_GAZEBO_DISH_VISIBLE_PASS' in text
