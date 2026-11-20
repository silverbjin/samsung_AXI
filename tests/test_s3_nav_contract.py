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


def test_nav2_goal_rejected_before_lifecycle_active_is_prevented():
    text=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert "State.PRIMARY_STATE_ACTIVE" in text
    assert "'bt_navigator','planner_server','controller_server'" in text
    assert "'collision_monitor','behavior_server'" in text
    assert 'S3_NAV_LIFECYCLE_NOT_ALL_ACTIVE' in text
    assert text.index('S3_NAV02_LIFECYCLE_ACTIVE_PREGOAL') < text.index('action.send_goal_async(')


def test_success_evidence_identifies_real_goals_not_no_goal():
    code=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert "result['kind']='s3_real_gazebo_navigation_delivery_return'" in code
    assert code.index("result['kind']='s3_real_gazebo_navigation_delivery_return'") < code.index("result['delivery_return']=True")

def test_nav02_ci_uses_one_gazebo_session_for_pregoal_and_goals():
    workflow=(ROOT/'.github/workflows/restaurant-s3-ci.yml').read_text()
    assert "if: github.ref == 'refs/heads/s3/amcl-nav2-20261120'" in workflow
    assert "if: github.ref == 'refs/heads/s3/nav-delivery-20261120'" in workflow
    assert "if: github.ref == 'refs/heads/s4/menu-safety-20261120' || github.ref == 'refs/heads/main'" in workflow
    script=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert script.index('RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL') < script.index('if args.exercise_goals:')
    assert 'NAV2_TRANSITIONS_LAST_60' in script
