#!/usr/bin/env python3
"""A-11: isolated tray RGB sensor SDF & opt-in robot overlay.

No change to the shipped S7 world, official Waffle, Nav2 or base bridge.
The independent tray lab uses the same sensor configuration; a robot
attachment without a physical tray does NOT prove equivalent sight lines.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

TOPIC = "/smartdish/tray/image_raw"
INFO_TOPIC = "/smartdish/tray/camera_info"
FRAME = "smartdish_tray_optical"
NAME = "smartdish_tray_rgb"
WIDTH, HEIGHT, RATE = 640, 480, 5
# Camera looks down: in Gazebo SDF, sensor +X camera-forward pitched +90 deg.
OVERHEAD_POSE = "0 0 1.50 0 1.57079632679 0"
# Prototype only; robot tray geometry is not part of main.
ROBOT_PROVISIONAL_POSE = "-0.15 0 0.45 0 1.20 3.14159265359"


def add_camera(link: ET.Element, pose: str = OVERHEAD_POSE) -> ET.Element:
    if link.find("./sensor[@name='%s']" % NAME) is not None:
        raise ValueError("A11_DUPLICATE_TRAY_RGB_CAMERA")
    s = ET.SubElement(link, "sensor", {"name": NAME, "type": "camera"})
    ET.SubElement(s, "pose").text = pose
    ET.SubElement(s, "always_on").text = "true"
    ET.SubElement(s, "update_rate").text = str(RATE)
    ET.SubElement(s, "topic").text = TOPIC
    ET.SubElement(s, "gz_frame_id").text = FRAME
    c = ET.SubElement(s, "camera")
    ET.SubElement(c, "horizontal_fov").text = "1.3962634"
    img = ET.SubElement(c, "image")
    ET.SubElement(img, "width").text = str(WIDTH)
    ET.SubElement(img, "height").text = str(HEIGHT)
    ET.SubElement(img, "format").text = "R8G8B8"
    clip = ET.SubElement(c, "clip")
    ET.SubElement(clip, "near").text = "0.05"
    ET.SubElement(clip, "far").text = "4.5"
    ET.SubElement(c, "camera_info_topic").text = INFO_TOPIC
    return s


def verify_camera(sensor: ET.Element) -> None:
    if sensor is None or sensor.attrib != {"name": NAME, "type": "camera"}:
        raise ValueError("A11_CAMERA_IDENTITY_MISMATCH")
    fields = {"topic": TOPIC, "gz_frame_id": FRAME, "update_rate": str(RATE),
              "./camera/image/width": str(WIDTH),
              "./camera/image/height": str(HEIGHT),
              "./camera/image/format": "R8G8B8"}
    for key, wanted in fields.items():
        if sensor.findtext(key) != wanted:
            raise ValueError("A11_CAMERA_CONTRACT_MISMATCH_" + key)


def optional_robot_sdf(source: Path, dest: Path) -> Path:
    """Camera-only opt-in Waffle Pi overlay, physical robot geometry unchanged.

    Camera field of view relative to a *future* tray is unverified; do not
    activate this in AI-OFF or treat images as approved B training samples.
    """
    root = ET.parse(source).getroot()
    model = root.find("./model[@name='turtlebot3_waffle_pi']")
    if model is None:
        raise ValueError("A11_EXPECTED_OFFICIAL_WAFFLE_PI")
    link = model.find("./link[@name='camera_link']")
    if link is None:
        raise ValueError("A11_CAMERA_LINK_MISSING")
    before = [ET.tostring(x) for x in root.findall(".//collision") + root.findall(".//inertial")]
    add_camera(link, ROBOT_PROVISIONAL_POSE)
    after = [ET.tostring(x) for x in root.findall(".//collision") + root.findall(".//inertial")]
    if before != after:
        raise ValueError("A11_ROBOT_BASE_PHYSICS_CHANGED")
    verify_camera(link.find("./sensor[@name='%s']" % NAME))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise ValueError("A11_SDF_WILL_NOT_OVERWRITE")
    ET.ElementTree(root).write(dest, encoding="utf-8", xml_declaration=True)
    return dest


def standalone_camera_model() -> ET.Element:
    model = ET.Element("model", name="smartdish_tray_observer")
    ET.SubElement(model, "static").text = "true"
    ET.SubElement(model, "pose").text = "0 0 0 0 0 0"
    link = ET.SubElement(model, "link", name="optical_mount")
    add_camera(link)
    verify_camera(link.find("sensor"))
    return model


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--robot-sdf", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    print("SMARTDISH_A11_OPTIONAL_ROBOT_SDF=" + str(optional_robot_sdf(a.robot_sdf, a.out)))


if __name__ == "__main__":
    main()
