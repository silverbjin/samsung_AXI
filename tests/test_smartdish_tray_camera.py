"""A-11 ROS/Gazebo interface contracts (L0 only; not real camera evidence)."""
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from smartdish_tray_camera import (
    add_camera, verify_camera, standalone_camera_model, optional_robot_sdf,
    TOPIC, INFO_TOPIC, FRAME, WIDTH, HEIGHT, RATE,
)


def test_standalone_camera_contract_and_sdf_xml():
    cam = standalone_camera_model()
    s = cam.find("./link/sensor")
    verify_camera(s)
    assert s.get("type") == "camera"
    assert s.findtext("topic") == TOPIC
    assert s.findtext("gz_frame_id") == FRAME
    assert s.findtext("camera/image/format") == "R8G8B8"
    assert (WIDTH, HEIGHT, RATE) == (640, 480, 5)
    ET.fromstring(ET.tostring(cam))


def test_camera_duplicate_rejected():
    link = ET.Element("link")
    add_camera(link)
    with pytest.raises(ValueError, match="DUPLICATE"):
        add_camera(link)


def test_opt_in_robot_preserves_original_collision_inertia(tmp_path):
    src = tmp_path / "waffle.sdf"
    src.write_text("""<sdf version="1.8"><model name="turtlebot3_waffle_pi">
      <link name="camera_link"><collision name="base"><geometry>
      <box><size>1 1 1</size></box></geometry></collision>
      <inertial><mass>1</mass></inertial></link></model></sdf>""")
    out = tmp_path / "out.sdf"
    optional_robot_sdf(src, out)
    a = ET.parse(src).getroot()
    b = ET.parse(out).getroot()
    for tag in ("collision", "inertial"):
        assert [ET.tostring(x) for x in a.findall(".//" + tag)] == [
            ET.tostring(x) for x in b.findall(".//" + tag)]
    assert src.read_text() != out.read_text()
    with pytest.raises(ValueError, match="WILL_NOT_OVERWRITE"):
        optional_robot_sdf(src, out)


def test_bridge_only_gazebo_to_ros_and_c_b_compat():
    cfg = yaml.safe_load((ROOT / "config/smartdish_tray_bridge.yaml").read_text())
    names = {x["ros_topic_name"]: x for x in cfg}
    assert names[TOPIC]["ros_type_name"] == "sensor_msgs/msg/Image"
    assert names[TOPIC]["gz_type_name"] == "gz.msgs.Image"
    assert names[TOPIC]["direction"] == "GZ_TO_ROS"
    assert names[INFO_TOPIC]["ros_type_name"] == "sensor_msgs/msg/CameraInfo"
    assert names["/smartdish/tray/poses"]["gz_type_name"] == "gz.msgs.Pose_V"
    assert all(x["direction"] == "GZ_TO_ROS" for x in cfg)
    for i in (1,2,3):
        topic="/smartdish/tray/pose/dish_%02d"%i
        assert names[topic]["gz_topic_name"]=="/smartdish/tray/gz_pose/dish_%02d"%i
        assert names[topic]["ros_type_name"]=="tf2_msgs/msg/TFMessage"
    b = (ROOT / "ai/scripts/capture_tray_ros.py").read_text()
    c = (ROOT / "src/smartdish_ai/smartdish_ai/stability_inference_node.py").read_text()
    assert TOPIC in b and TOPIC in c
    assert "qos_profile_sensor_data" in b and "qos_profile_sensor_data" in c


def test_original_ai_off_files_not_edited_by_generator():
    src = (ROOT / "src/restaurant_bringup/config/bridge.yaml").read_text()
    assert TOPIC not in src
    assert (ROOT / "src/smartdish_robot/config/table_poses.yaml").exists()
