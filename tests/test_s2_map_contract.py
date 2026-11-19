"""Contract only: Gazebo L2 is the real proof, not these unit tests."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
SRC=Path(__file__).resolve().parents[1]/'scripts/ci_s2_map_smoke.py'
spec=importlib.util.spec_from_file_location('s2map',SRC)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def fake(value):
    return SimpleNamespace(info=SimpleNamespace(width=20,height=20,resolution=.05),data=[value]*400)
def test_reject_unknown_map():
    assert module.valid_grid(fake(0))
    assert not module.valid_grid(fake(-1))
def test_saved_map_must_have_real_image(tmp_path):
    p=tmp_path/'map.yaml'
    p.write_text('image: map.pgm\nresolution: .05\norigin: [0,0,0]\nnegate: 0\nfree_thresh: .25\noccupied_thresh: .65\n')
    try:module.check_map_yaml(p);assert False
    except RuntimeError:pass
    (tmp_path/'map.pgm').write_bytes(b'P5\n10 10\n255\n'+bytes(range(100)))
    assert module.check_map_yaml(p).is_file()
def test_real_ros_contract():
    s=SRC.read_text()
    for t in ('mapping.launch.py','/scan','/odom','/map_saver/save_map','nav2_map_server','restaurant/map_reloaded','RESTAURANT_S2_L2_REAL_GAZEBO_SLAM_SAVE_RELOAD_PASS_NO_NAV_GOAL'):
        assert t in s
    assert 'pub.publish(Twist())' in s
