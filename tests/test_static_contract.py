"""Small no-ROS contract tests; NOT a substitute for real Gazebo."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
import sys
import yaml
ROOT=Path(__file__).resolve().parents[1]

def module_from(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_world_collision_and_required_landmarks():
    root=ET.parse(ROOT/'src/restaurant_world/worlds/restaurant.sdf').getroot()
    assert root.find('./world').get('name')=='restaurant'
    models={m.get('name'):m for m in root.findall('.//world/model')}
    assert {'floor','kitchen_counter','table_3','human_proxy'}<=set(models)
    for name in ['kitchen_counter','table_3','human_proxy','west_wall']:
        assert models[name].find('.//collision/geometry') is not None
    assert len(root.findall('.//world/plugin[@name="gz::sim::systems::Sensors"]'))==1

def test_pose_and_menu_policy_static():
    table=yaml.safe_load((ROOT/'src/restaurant_world/config/tables.yaml').read_text())
    assert table['frame']=='map'
    assert abs(table['pickup']['x']+2.6)<1e-6
    assert table['table_3']['y']>-2.8
    sys.path.insert(0,str(ROOT/'src/restaurant_delivery/restaurant_delivery'))
    from menu_policy import read_policy
    menu=yaml.safe_load((ROOT/'src/restaurant_delivery/config/menu.yaml').read_text())
    assert read_policy(menu,'SOUP').max_speed_mps < read_policy(menu,'NORMAL').max_speed_mps

def test_single_twist_bridge_no_twiststamped():
    data=yaml.safe_load((ROOT/'src/restaurant_bringup/config/bridge.yaml').read_text())
    pubs=[x for x in data if x.get('ros_topic_name')=='/cmd_vel']
    assert len(pubs)==1
    assert pubs[0]['ros_type_name']=='geometry_msgs/msg/Twist'
    assert pubs[0]['direction']=='ROS_TO_GZ'

def test_overlay_rgbd_generation(tmp_path):
    src=tmp_path/'source.sdf'
    src.write_text('''<sdf version="1.8"><model name="turtlebot3_waffle_pi">
        <link name="camera_link"/>
        <link name="camera_rgb_frame"><sensor name="camera" type="camera"/></link>
        <link name="base_scan"><sensor name="hls_lfcd_lds" type="gpu_lidar"><visualize>true</visualize><update_rate>10</update_rate></sensor></link>
        </model></sdf>''')
    mod=module_from(ROOT/'scripts/prepare_waffle_rgbd.py','overlay_test')
    out=tmp_path/'overlay.sdf'
    mod.build(src,out)
    node=ET.parse(out).getroot().find('.//sensor')
    assert node is not None and node.get('type')=='rgbd_camera'
    assert node.findtext('gz_frame_id')=='restaurant_rgbd_optical'
    root=ET.parse(out).getroot()
    assert root.find(".//sensor[@name='camera']") is None
    assert root.findtext(".//sensor[@name='hls_lfcd_lds']/visualize") == 'false'
    assert root.findtext(".//sensor[@name='hls_lfcd_lds']/update_rate") == '10'

def test_nav_params_scan_only_preserves_official_source(tmp_path):
    base={
      'local_costmap':{'local_costmap':{'ros__parameters':{'voxel_layer':{'observation_sources':'scan',
                       'scan':{'topic':'scan','data_type':'LaserScan',
                               'marking':True,'clearing':True}}}}},
      'controller_server':{'ros__parameters':{}},
      'collision_monitor':{'ros__parameters':{
          'observation_sources':['scan'],
          'cmd_vel_in_topic':'cmd_vel_smoothed','cmd_vel_out_topic':'cmd_vel',
          'polygons':['FootprintApproach'],
          'FootprintApproach':{'action_type':'approach'}}}
    }
    src=tmp_path/'nav2.yaml'
    src.write_text(yaml.safe_dump(base))
    mod=module_from(ROOT/'scripts/prepare_nav2_params.py','nav2_overlay_test')
    out=tmp_path/'generated.yaml'
    mod.build(src,out)
    d=yaml.safe_load(out.read_text())
    voxel=d['local_costmap']['local_costmap']['ros__parameters']['voxel_layer']
    assert voxel['observation_sources']=='scan'
    assert voxel['scan']=={'topic':'scan','data_type':'LaserScan','marking':True,'clearing':True}
    assert 'rgbd' not in voxel
    assert d['collision_monitor']['ros__parameters']['observation_sources']==['scan']
