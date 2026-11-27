import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a04_motion import clearance_world,dish_measure,contact_category,gate_paths
def test_clearance_positive_and_collision():
    g={"floor":{"lo":[-5,-5,-.2],"hi":[5,5,0]},"obstacles":[{"model":"table","collision":"box","lo":[1,1,0],"hi":[2,2,.7]}]}
    assert clearance_world(g,(0,0),0)[1]>.5
    assert clearance_world(g,(1,1),0)[1]<0
def test_relative_measure():
    r={"xyz":[1,2,0],"q":[0,0,0,1]};d={"xyz":[1,2,.4635],"q":[0,0,0,1]}
    m=dish_measure(r,d,0)
    assert m["center_m"]==0 and m["z_error_m"]<1e-9 and m["tilt_rad"]==0
def test_contact_classification():
    assert contact_category({"model":"floor"},"waffle_pi::wheel_left_link::wheel_left_collision","floor::body::floor_collision")=="GROUND_SUPPORT"
    assert contact_category({"model":"floor"},"smartdish_product_dish_00::body::envelope","floor::body::floor_collision")=="UNEXPECTED"
def test_no_path_no_motion():
    with pytest.raises(RuntimeError,match="ACTUAL_PATH_CLEARANCE_GATE"):gate_paths({"paths":[]})

@pytest.mark.parametrize("wheel",["wheel_left_link::wheel_left_collision","wheel_right_link::wheel_right_collision",
                                "caster_back_left_link::collision","caster_back_right_link::collision"])
def test_actual_support_pair_symmetric(wheel):
    a="waffle_pi::"+wheel;b="floor::body::floor_collision"
    assert contact_category({"model":"floor"},b,a)=="GROUND_SUPPORT"
    assert contact_category({"model":"turtlebot3_waffle_pi"},a,b)=="GROUND_SUPPORT"
    assert contact_category({"model":"table_3"},a,"table_3::body::table_3_collision")=="UNEXPECTED"
def test_base_floor_is_not_allowed_support():
    assert contact_category({"model":"floor"},"waffle_pi::base_link::base_collision","floor::body::floor_collision")=="UNEXPECTED"
