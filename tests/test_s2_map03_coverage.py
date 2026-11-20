"""S2-MAP-03 extended physical observation route is separate from released S2-MAP-02."""
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('s2map03',ROOT/'scripts/s2_map02_contract.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_existing_s2_map02_unchanged_and_new_route_is_physically_clear():
    assert m.SURVEY[0]==(-2.60,-2.20)
    assert len(m.SURVEY)==13
    assert len(m.OBSERVATION_SURVEY)==28
    assert m.OBSERVATION_SURVEY[0]==m.SURVEY[0]
    assert m.OBSERVATION_SURVEY[-1]==m.SURVEY[-1]
    assert 33.0 < m.route_length(m.SURVEY) < 34.0
    assert 57.0 < m.route_length(m.OBSERVATION_SURVEY) < 60.0
    world=ROOT/'src/restaurant_world/worlds/restaurant.sdf'
    assert not m.route_clearance(world,route=m.OBSERVATION_SURVEY,clearance=.40)

def test_enhanced_map_is_opt_in_and_no_occupancy_forgery():
    code=(ROOT/'scripts/ci_s2_map02.py').read_text()
    assert '--enhanced-survey' in code
    assert 'survey=OBSERVATION_SURVEY if args.enhanced_survey else SURVEY' in code
    assert 'S2_MAP03_COVERAGE_NOT_IMPROVED' in code
    assert 'reference_known_area_m2=26399*(0.05**2)' in code
    assert 'SAVE_MAP' in code and 'Transition.TRANSITION_ACTIVATE' in code
    assert 'pub=node.create_publisher(Twist' in code
    assert 'ground_truth.fresh()' in code
