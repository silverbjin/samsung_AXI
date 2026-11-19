"""S2-MAP-02 offline route, real-map gating, and no synthetic map acceptance."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('map02',ROOT/'scripts/s2_map02_contract.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_survey_route_physically_clear_in_authored_sdf():
    assert len(m.SURVEY)>=8
    assert 15 < m.route_length() < 45
    assert not m.route_clearance(ROOT/'src/restaurant_world/worlds/restaurant.sdf')

def fake_grid(fill=0,w=180,h=160):
    origin=SimpleNamespace(position=SimpleNamespace(x=-4.5,y=-4),orientation=SimpleNamespace(z=0.,w=1.))
    info=SimpleNamespace(width=w,height=h,resolution=.05,origin=origin)
    return SimpleNamespace(info=info,data=[fill]*(w*h))

def test_fake_or_partial_map_never_passes_quality():
    import pytest
    with pytest.raises(ValueError,match='MAP_EMPTY'):
        m.coverage(fake_grid(-1))
    with pytest.raises(ValueError,match='MAP_INSUFFICIENT_FREE_OCCUPIED_EVIDENCE'):
        m.coverage(fake_grid(0))

def test_survey_required_real_coverage_dimensions():
    grid=fake_grid()
    for i in range(0,len(grid.data),13):grid.data[i]=100
    stats=m.coverage(grid)
    assert stats['known_span_x_m']>7
    assert stats['occupied']>120
    assert m.free_path_connected(grid,(-2,0),(2,0))
    for y in range(160):
        for x in (89,90):
            grid.data[y*180+x]=-1
    assert not m.free_path_connected(grid,(-2,0),(2,0))

def test_odom_reference_can_start_at_zero():
    assert m.from_world_to_odom(m.START,(0,0,0))==(0,0)
    assert m.from_world_to_odom((2.65,-1.82),(0,0,0))==(5.25,.3800000000000001) or abs(m.from_world_to_odom((2.65,-1.82),(0,0,0))[1]-.38)<1e-9

def test_no_mapping_or_nav_success_from_contract_only():
    code=(ROOT/'scripts/ci_s2_map02.py').read_text()
    assert 'RESTAURANT_S2_MAP02_L2_FULL_COVERAGE_PASS' in code
    assert 'from s2_map02_contract import' in code
    assert "'/map_saver/save_map'" in code
    assert 'nav2_map_server' in code
    assert 'while' in code


def test_s2_survey_uses_actual_gazebo_pose_but_preserves_odom_and_lidar():
    code=(ROOT/'scripts/ci_s2_map02.py').read_text()
    assert 'GazeboModelPose' in code and 'ground_truth.fresh()' in code
    assert 'ground_truth.pose' in code and 'world_to_map_point(' in code
    assert "Odometry,'/odom'" in code and "LaserScan,'/scan'" in code
    assert "front<.40" in code


def test_front_sector_positive_inf_means_no_detection_not_zero():
    from types import SimpleNamespace
    def scan(values):
        return SimpleNamespace(ranges=values,angle_min=0.0,
                               angle_increment=2*3.141592653589793/360,
                               range_min=.12,range_max=3.5)
    actual,stats=m.front_sector_clearance(scan([float('inf')]*360))
    assert actual==3.5 and stats['positive_inf']>=40
    blocked,stats=m.front_sector_clearance(scan([float('nan')]*360))
    assert blocked==0.0 and stats['invalid']>=40
    blocked,stats=m.front_sector_clearance(scan([0.0]*360))
    assert blocked==0.0
    bad=[float('inf')]*360
    bad[0]=.37
    actual,stats=m.front_sector_clearance(scan(bad))
    assert abs(actual-.37)<.001 and stats['finite']>=1
