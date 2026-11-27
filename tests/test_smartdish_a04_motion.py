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

def test_localization_map_does_not_project_high_only_obstacle(tmp_path):
    from smartdish_a04_motion import localization_map
    from smartdish_a04_clearance import read_map
    g={"floor":{"lo":[-5,-4.5,-.2],"hi":[5,4.5,0]},"lidar_model_z_m":.121,
       "world_sha256":"a"*64,
       "obstacles":[{"model":"high","shape":"box","lo":[-2.8,-2.4,.5],"hi":[-2.4,-2.,.8]},
                    {"model":"low","shape":"box","lo":[-.2,-.2,0],"hi":[.2,.2,.8]}]}
    cfg,a=read_map(localization_map(g,tmp_path))
    def cell(x,y):
        j=int((x-cfg["origin"][0])/.05);i=int((y-cfg["origin"][1])/.05)
        return a[i,j]
    assert cell(0,0)==0 # high-only obstacle absent from scan-plane AMCL map
    assert cell(2.6,2.2)==100

def test_dish_platform_vs_mast():
    dish="smartdish_product_dish_00::body::envelope"
    assert contact_category({},dish,"waffle_pi::smartdish_product_tray::platform_collision")=="TRAY_DISH"
    assert contact_category({},dish,"waffle_pi::smartdish_product_tray::mast_collision")=="UNEXPECTED"
