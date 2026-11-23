"""S4 L0 contract tests; actual PASS must come from real Gazebo L2."""
import importlib.util
from pathlib import Path
import pytest
import yaml
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s4test',ROOT/'scripts/s4_menu_contract.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_official_nav_overlay_speed_limit_and_cm_stop_zone():
    p=importlib.util.spec_from_file_location('nav_params',ROOT/'scripts/prepare_nav2_params.py')
    nav=importlib.util.module_from_spec(p);p.loader.exec_module(nav)
    source={'controller_server':{'ros__parameters':{}},
            'collision_monitor':{'ros__parameters':{
               'cmd_vel_in_topic':'cmd_vel_smoothed','cmd_vel_out_topic':'cmd_vel',
               'polygons':['FootprintApproach'],'FootprintApproach':{'action_type':'approach'},
               'observation_sources':['scan']}},
            'local_costmap':{'local_costmap':{'ros__parameters':{'voxel_layer':{
                'scan':{'topic':'scan','data_type':'LaserScan','marking':True,'clearing':True}}}}}}
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        here=Path(d);a=here/'src.yaml';b=here/'out.yaml'
        a.write_text(yaml.safe_dump(source));nav.build(a,b)
        after=yaml.safe_load(b.read_text())
    assert after['controller_server']['ros__parameters']['speed_limit_topic']=='/speed_limit'
    cm=after['collision_monitor']['ros__parameters']
    assert cm['polygons']==['S4ForwardStop','FootprintApproach']
    assert cm['S4ForwardStop']['action_type']=='stop' and cm['S4ForwardStop']['min_points']>=4
    assert cm['cmd_vel_out_topic']=='cmd_vel' and cm['cmd_vel_in_topic']=='cmd_vel_smoothed'
    assert cm['observation_sources']==['scan']
    voxel=after['local_costmap']['local_costmap']['ros__parameters']['voxel_layer']
    assert voxel['observation_sources']=='scan' and 'rgbd' not in voxel
    assert voxel['scan']['data_type']=='LaserScan'

def test_speed_policy_and_fail_closed_samples():
    config=yaml.safe_load((ROOT/'src/restaurant_delivery/config/menu.yaml').read_text())
    assert config['NORMAL']['max_speed_mps']==m.NORMAL_LIMIT
    assert config['SOUP']['max_speed_mps']==m.SOUP_LIMIT
    good_n=m.measured_speed('NORMAL',[.18,.2,.21,.22,.23,.22,.19,.2,.21,.22])
    good_s=m.measured_speed('SOUP',[.08,.09,.10,.11,.1,.09,.10,.1,.1,.09])
    assert m.compare_speeds(good_n,good_s)['p75_ratio_normal_to_soup']>1.35
    with pytest.raises(ValueError,match='INSUFFICIENT'):
        m.measured_speed('NORMAL',[.0,.01,.0])
    with pytest.raises(ValueError,match='NOT_MEASURABLY_SLOWER'):
        m.compare_speeds(good_n,dict(good_s,p75_mps=.18))
    with pytest.raises(ValueError,match='OVER_LIMIT'):
        m.compare_speeds(dict(good_n,p95_mps=.4),good_s)

def test_physical_fixture_and_real_scan_required():
    assert '<static>true</static>' in m.fixture_sdf()
    assert '<collision name="c">' in m.fixture_sdf()
    assert m.front_obstacle_points(None)==0
    assert m.stop_polygon_points(None)==0
    from types import SimpleNamespace
    scan=SimpleNamespace(ranges=[float('nan')]*360,angle_min=0.,
        angle_increment=2*3.141592653589793/360,range_min=.12,range_max=3.5)
    assert m.front_obstacle_points(scan)==0

def test_s4_opt_in_never_replaces_s3_goal_mode():
    s=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert '--menu-safety' in s
    assert 'if args.menu_safety:' in s
    assert 'S4_MENU_NORMAL_SOUP_REAL_ODOM_SPEED_PASS' in s
    assert 'S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS' in s
    assert 'send_goal_async' in s and 'GoalStatus.STATUS_SUCCEEDED' in s

def test_stop_transition_between_fixture_and_probe_is_not_lost():
    # Nav2 publishes CollisionMonitorState on polygon transitions, not every Twist.
    # Fixture may trigger STOP before the positive-input probe marker.
    script=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert 'fixture_marker=time.monotonic()' in script
    assert 't>=fixture_marker and a==CollisionMonitorState.STOP' in script
    assert 'S4_CM_STOP_NOT_CONFIRMED_BEFORE_PROBE' in script
    assert 'validate_stop_probe(' in script
    assert "result['s4_stop_timing']=timing" in script

def test_s4_stop_only_does_not_require_unneeded_nav_action_server():
    # Real Collision Monitor stop test has no navigation goals; CM ACTIVE is
    # checked separately. An action-server discovery timeout is unrelated.
    src=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert 'args.s4_stop_only or action.wait_for_server(timeout_sec=.25)' in src
    workflow=(ROOT/'.github/workflows/restaurant-s3-ci.yml').read_text()
    assert 'FLAGS=(--s4-stop-only)' in workflow
    assert 'FLAGS=(--exercise-goals --menu-safety)' not in workflow

def test_stop_probe_fails_closed_on_nonzero_output_after_confirmed_stop():
    states=[(1.1,1,'S4ForwardStop')]
    inputs=[(2.1,.08)]
    zeros=[(2.1,0.),(2.2,0.),(2.3,0.)]
    good=m.validate_stop_probe(states,inputs,zeros,1.0,2.0,0.0,1)
    assert good['preprobe_stop_confirmed'] is True
    assert good['filtered_output_max_abs_mps']==0.0
    with pytest.raises(ValueError,match='S4_CM_STOP_FAILED_TO_FILTER_OR_ROBOT_MOVED'):
        m.validate_stop_probe(states,inputs,[(2.1,.08),(2.2,0.),(2.3,0.)],1.0,2.0,.00021,1)
    with pytest.raises(ValueError,match='S4_CM_STOP_FAILED_TO_FILTER_OR_ROBOT_MOVED'):
        m.validate_stop_probe(states,inputs,zeros,1.0,2.0,.046,1)
    with pytest.raises(ValueError,match='S4_CM_STOP_CHAIN_UNPROVEN'):
        m.validate_stop_probe([(2.1,1,'S4ForwardStop')],inputs,zeros,1.0,2.0,0.0,1)
    with pytest.raises(ValueError,match='S4_CM_STOP_CHAIN_UNPROVEN'):
        m.validate_stop_probe(states+[(2.15,0,'')],inputs,zeros,1.0,2.0,0.0,1)
