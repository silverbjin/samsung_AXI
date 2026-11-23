"""S6 control-plane opt-in: small change, S5 defaults bit-for-bit preserved."""
from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('nav_params',ROOT/'scripts/prepare_nav2_params.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_s6_bt_ack_tune_has_bounded_change():
    original={'bt_navigator':{'ros__parameters':{'default_server_timeout':20}},
              'collision_monitor':{'ros__parameters':{'polygons':['S4ForwardStop']}}}
    normal=m.apply_s6_ack_ms(original,None)
    assert normal['bt_navigator']['ros__parameters']['default_server_timeout']==20
    changed=m.apply_s6_ack_ms(original,200)
    assert changed['bt_navigator']['ros__parameters']['default_server_timeout']==200
    assert changed['collision_monitor']['ros__parameters']['polygons']==['S4ForwardStop']
    for value in (19,501,-1):
        with pytest.raises(ValueError,match='OUT_OF_BOUNDS'):
            m.apply_s6_ack_ms(original,value)
    with pytest.raises(RuntimeError,match='TIMEOUT_MISSING'):
        m.apply_s6_ack_ms({'bt_navigator':{'ros__parameters':{}}},200)

def test_s5_nav2_immediate_and_s6_stagger_opt_in():
    s=(ROOT/'src/restaurant_bringup/launch/navigation.launch.py').read_text()
    assert "DeclareLaunchArgument('s6_stagger_nav_start',default_value='false')" in s
    assert 'UnlessCondition(LaunchConfiguration(\\'s6_stagger_nav_start\\'))' in s
    assert 'TimerAction(' in s and 'period=10.0' in s
    assert "condition=IfCondition(LaunchConfiguration('s6_stagger_nav_start'))" in s
    r=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert "nav_cmd.append('s6_stagger_nav_start:=true')" in r
    assert r.index("if args.s6_vision:",r.index("nav_cmd=")) < r.index("nav_cmd.append('s6_stagger_nav_start:=true')")
    o=(ROOT/'scripts/restaurant_demo.sh').read_text()
    assert 'NAV_AUTO_ARGS+=(--s6-bt-ack-ms 200)' in o
    assert '"$MODE" == live' in o
    assert 'SAMSUNGAXI_S6_VISION:-0' in o
