"""A-PROD-02 opt-in robot geometry and bridge contract, no physical PASS."""
from pathlib import Path
import sys
from xml.etree import ElementTree as ET
import pytest
import yaml
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from smartdish_product_robot import build_robot, build_bridge, TRAY_SIZE

BASE = """<sdf version="1.9"><model name="turtlebot3_waffle_pi"><link name="base_link"><inertial><mass>1</mass></inertial><collision name="original"/></link><link name="camera_link"/></model></sdf>"""

def test_physics_preserved_and_top_view():
    original = ET.fromstring(BASE)
    root = ET.fromstring(build_robot(BASE))
    m = root.find("model")
    assert ET.tostring(m.find("./link[@name='base_link']")) == ET.tostring(original.find("./model/link"))
    tray = m.find("./link[@name='smartdish_product_tray']")
    assert tray.find("./collision/geometry/box/size").text == " ".join(map(str, TRAY_SIZE))
    assert float(tray.findtext("inertial/mass")) > 0
    j = m.find("./joint[@name='smartdish_tray_fixed']")
    assert j.attrib["type"] == "fixed" and j.findtext("parent") == "base_link"
    assert j.findtext("child") == tray.attrib["name"]
    s = tray.find("sensor")
    assert s.findtext("pose") == "0 0 0.65 0 1.57079632679 0"
    assert s.findtext("camera/image/width") == "640"
    assert s.findtext("camera/image/height") == "480"
    assert s.findtext("update_rate") == "5"
    assert s.findtext("gz_frame_id") == "smartdish_tray_optical"
    with pytest.raises(ValueError):
        build_robot(ET.tostring(root, encoding="unicode"))

def test_bridge_keeps_clock_and_cmd_vel():
    base = yaml.safe_load((ROOT / "src/restaurant_bringup/config/bridge.yaml").read_text())
    new = build_bridge(base)
    assert new[:len(base)] == base
    assert len(new) == len(base) + 2
    assert [x["ros_topic_name"] for x in new].count("/clock") == 1
    image = [x for x in new if x["ros_topic_name"] == "/smartdish/tray/image_raw"]
    assert len(image) == 1 and image[0]["direction"] == "GZ_TO_ROS"
    with pytest.raises(ValueError):
        build_bridge(new)

def test_wrong_model_fails():
    with pytest.raises(ValueError):
        build_robot(BASE.replace("turtlebot3_waffle_pi", "other"))
