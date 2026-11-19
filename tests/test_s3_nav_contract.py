"""S3 full navigation must use the released SLAM map coordinate frame."""
from pathlib import Path
import importlib.util
import yaml
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('mapcontract',ROOT/'scripts/s3_map_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)

def test_delivery_goal_coordinates_match_s2_map_frame():
    path=ROOT/'src/restaurant_delivery/config/s3_map_waypoints.yaml'
    d=yaml.safe_load(path.read_text())
    assert d['frame']=='map' and d['source_map_run']=='44551726313'
    assert (d['pickup']['x'],d['pickup']['y'])==contract.MAP_PICKUP
    assert abs(d['table_3']['x']-contract.MAP_TABLE3[0])<1e-9
    assert abs(d['table_3']['y']-contract.MAP_TABLE3[1])<1e-9
    assert d['pickup']['x']!=contract.WORLD_PICKUP[0]

def test_delivery_manager_never_sends_world_frame_goal_as_map_pose():
    src=(ROOT/'src/restaurant_delivery/restaurant_delivery/delivery_manager.py').read_text()
    assert "s3_map_waypoints.yaml" in src
    assert "world_share/'config/tables.yaml'" not in src
    assert "waitUntilNav2Active(localizer='amcl')" in src

def test_nav_action_is_opt_in_and_requires_real_move_evidence():
    source=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert '--exercise-goals' in source
    assert "if args.exercise_goals:" in source
    assert 'send_goal_async' in source
    assert 'GoalStatus.STATUS_SUCCEEDED' in source
    assert 'RESTAURANT_S3_NAV02_REAL_GAZEBO_DELIVERY_RETURN_PASS' in source
    assert 'NAV_PHYSICAL_ODOM_INSUFFICIENT' in source
