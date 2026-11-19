"""Minimal contract checks: cannot assert live WSL GPU or RTF."""
import subprocess
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]

def test_probe_non_mutating():
    p=ROOT/'scripts/wsl2_perf_doctor.sh'
    subprocess.run(['bash','-n',str(p)],check=True)
    s=p.read_text()
    assert 'free -h' in s and 'glxinfo -B' in s and '/dev/dxg' in s
    assert 'wsl --shutdown' not in s
    assert 'sudo apt-get' not in s and 'nvidia-smi' in s

def test_registered_rgbd_only_and_one_velocity_bridge():
    data=yaml.safe_load((ROOT/'src/restaurant_bringup/config/bridge.yaml').read_text())
    topics={x['ros_topic_name'] for x in data}
    for t in ('/restaurant/rgbd/image','/restaurant/rgbd/depth_image','/restaurant/rgbd/points','/scan'):
        assert t in topics
    assert '/camera/camera_info' not in topics
    assert len([x for x in data if x['ros_topic_name']=='/cmd_vel'])==1
    launch=(ROOT/'src/restaurant_bringup/launch/world.launch.py').read_text()
    assert 'image_bridge' not in launch

def test_mapping_has_headless_flag():
    s=(ROOT/'src/restaurant_bringup/launch/mapping.launch.py').read_text()
    assert "DeclareLaunchArgument('gui', default_value='true')" in s
    assert "'gui': LaunchConfiguration('gui')" in s
