"""A-PROD-03 backend geometry, named IDs and relative pose (L0 fixtures)."""
import math
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"src/smartdish_robot"))
from s6_scene import fixture_sdf
from smartdish_robot.product_gazebo_backend import (
    build_dish_sdf, parse_scene_models, relative_xyz, DISH_NAMES,
)
from smartdish_robot.product_contract import ContractError

def test_dynamic_dishes_reuse_s6_visuals():
    fixture=ET.fromstring(fixture_sdf()).find("model")
    for i,name in enumerate(DISH_NAMES):
        model=ET.fromstring(build_dish_sdf(fixture,i,(1.,2.,.5+i*.037),0.)).find("model")
        assert model.attrib["name"]==name
        assert model.findtext("static")=="false"
        assert model.findtext("link/gravity")=="true"
        assert float(model.findtext("link/inertial/mass"))==.22
        assert len(model.findall("link/visual"))==2
        assert float(model.findtext("link/collision/geometry/cylinder/radius"))==.245
        assert model.findtext("plugin/topic")=="/smartdish/product/gz_pose/"+name
        assert model.find("joint") is None
        for v in model.findall("link/visual"):
            original=fixture.find(f"./link/visual[@name='{v.attrib['name']}']")
            assert ET.tostring(v.find("geometry"))==ET.tostring(original.find("geometry"))

def test_scene_model_identity_not_link_id_or_index():
    sample='''name: "restaurant"
model {
  id: 31
  name: "table_3"
  link {
    id: 99
    name: "body"
  }
}
model {
  name: "waffle_pi"
  id: 41
}
'''
    assert parse_scene_models(sample)=={"table_3":31,"waffle_pi":41}
    with pytest.raises(ContractError):parse_scene_models(sample.replace("id: 41","id: 31"))
    with pytest.raises(ContractError):parse_scene_models(sample[:-2])

def test_inverse_quaternion_relative_pose():
    q=(0,0,math.sin(math.pi/4),math.cos(math.pi/4))
    assert relative_xyz((1,2,3),q,(1,3,3.5))==pytest.approx((1,0,.5))
    with pytest.raises(ContractError):relative_xyz((1,2,3),(0,0,0,0),(1,3,3.5))
