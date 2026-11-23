"""S7-01 RED→GREEN: startup dish geometry and original world are isolated."""
from pathlib import Path
from xml.etree import ElementTree as ET
import hashlib
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from s7_scene import build_world,validate_world,generate
BASE=ROOT/'src/restaurant_world/worlds/restaurant.sdf'

def test_optin_stacked_and_negative_empty_preserve_source(tmp_path):
    original=BASE.read_bytes();sha=hashlib.sha256(original).hexdigest()
    pos=generate(BASE,tmp_path/'stacked.sdf','stacked')
    neg=generate(BASE,tmp_path/'empty.sdf','empty')
    assert hashlib.sha256(BASE.read_bytes()).hexdigest()==sha
    assert pos['fixture_count']==1 and neg['fixture_count']==0
    assert pos['source_sha256']==neg['source_sha256']==sha
    stacked=ET.parse(tmp_path/'stacked.sdf')
    model=stacked.find(".//world/model[@name='s6_stacked_dishes']")
    assert model is not None
    assert model.findtext('pose')=='2.65 -2.91 0 0 0 0'
    assert len(model.findall('./link/visual'))==6
    assert len(model.findall('./link/collision'))==6
    assert ET.parse(tmp_path/'empty.sdf').find(".//model[@name='s6_stacked_dishes']") is None
    assert ET.parse(BASE).find(".//model[@name='s6_stacked_dishes']") is None

def test_duplicate_missing_table_and_wrong_geometry_fail_closed():
    original=BASE.read_text()
    stacked=build_world(original,'stacked')
    with pytest.raises(ValueError,match='FIXTURE_COUNT_MISMATCH'):
        build_world(stacked,'stacked')
    with pytest.raises(ValueError,match='TABLE3_MISSING'):
        validate_world(original.replace('name="table_3"','name="table_three"'),'empty')
    with pytest.raises(ValueError,match='POSE_MISMATCH'):
        validate_world(stacked.replace('2.65 -2.91 0 0 0 0','3.0 -2.91 0 0 0 0'),'stacked')

def test_launch_defaults_unchanged_unless_s7_world_file_passed():
    w=(ROOT/'src/restaurant_bringup/launch/world.launch.py').read_text()
    n=(ROOT/'src/restaurant_bringup/launch/navigation.launch.py').read_text()
    assert "DeclareLaunchArgument('world_file', default_value=world_file)" in w
    assert "'gz_args': ['-r -s -v2 ', LaunchConfiguration('world_file')]" in w
    assert "default_value=os.path.join(world_pkg,'worlds','restaurant.sdf')" in n
    assert "'world_file':LaunchConfiguration('world_file')" in n
    assert 'on_exit_shutdown' in w and 's6_stagger_nav_start' in n
