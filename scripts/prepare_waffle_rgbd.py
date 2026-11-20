#!/usr/bin/env python3
"""Create a local overlay from the *official* Waffle Pi SDF, never edit upstream.

Pattern derived from AXIA D08's registered rgbd_camera attachment. The
new restaurant topic/frame names are provisional until checked in live Gazebo.
"""
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET


def build(src: Path, dst: Path, rgbd_rate_hz: int = 5):
    if rgbd_rate_hz not in (2, 5):
        raise ValueError('S5_PERF_RGBD_RATE_MUST_BE_2_OR_5')
    tree = ET.parse(src)
    robot = tree.getroot().find('./model')
    if robot is None or robot.get('name')!='turtlebot3_waffle_pi':
        raise RuntimeError('EXPECTED_WAFFLE_PI_MODEL')
    camera = robot.find("./link[@name='camera_link']")
    if camera is None:
        raise RuntimeError('UPSTREAM_CAMERA_LINK_NOT_FOUND')
    if camera.find("./sensor[@name='restaurant_registered_rgbd']") is not None:
        raise RuntimeError('DUPLICATE_RGBD')
    # Keep the official drive/TF/IMU and 10Hz LiDAR measurement unchanged.
    # The Waffle Pi 30Hz RGB camera is redundant once registered RGB-D provides RGB.
    legacy = robot.find("./link[@name='camera_rgb_frame']")
    if legacy is None:
        raise RuntimeError('EXPECTED_OFFICIAL_CAMERA_RGB_LINK')
    cameras = legacy.findall("./sensor[@name='camera']")
    if len(cameras) != 1 or cameras[0].get('type') != 'camera':
        raise RuntimeError('EXPECTED_ONE_OFFICIAL_RGB_CAMERA')
    legacy.remove(cameras[0])
    lidar = robot.find("./link[@name='base_scan']/sensor[@name='hls_lfcd_lds']")
    if lidar is None or lidar.get('type') != 'gpu_lidar':
        raise RuntimeError('EXPECTED_OFFICIAL_GPU_LIDAR')
    viz = lidar.find('visualize')
    if viz is not None:
        viz.text = 'false'  # Ray overlay is not the actual /scan.
    sensor=ET.SubElement(camera,'sensor',{'name':'restaurant_registered_rgbd','type':'rgbd_camera'})
    ET.SubElement(sensor,'pose').text='0 0 0 0 0 0'
    ET.SubElement(sensor,'always_on').text='true'
    ET.SubElement(sensor,'update_rate').text=str(rgbd_rate_hz)
    ET.SubElement(sensor,'topic').text='restaurant/rgbd'
    ET.SubElement(sensor,'gz_frame_id').text='restaurant_rgbd_optical'
    cfg=ET.SubElement(sensor,'camera')
    ET.SubElement(cfg,'horizontal_fov').text='1.57'
    img=ET.SubElement(cfg,'image')
    ET.SubElement(img,'width').text='320'
    ET.SubElement(img,'height').text='240'
    ET.SubElement(img,'format').text='R8G8B8'
    clip=ET.SubElement(cfg,'clip')
    ET.SubElement(clip,'near').text='0.12'
    ET.SubElement(clip,'far').text='6.0'
    dst.parent.mkdir(parents=True,exist_ok=True)
    tree.write(dst,encoding='utf-8',xml_declaration=True)
    if len(ET.parse(dst).getroot().findall(".//sensor[@name='restaurant_registered_rgbd']"))!=1:
        raise RuntimeError('RGBD_OVERLAY_VALIDATION_FAILED')
    generated=ET.parse(dst).getroot()
    if generated.find(".//sensor[@name='camera']") is not None:
        raise RuntimeError('REDUNDANT_RGB_SENSOR_STILL_PRESENT')
    if generated.findtext(".//sensor[@name='hls_lfcd_lds']/visualize") != 'false':
        raise RuntimeError('LIDAR_RAY_VISUALIZATION_STILL_ON')
    print('RESTAURANT_RGBD_OVERLAY_STATIC_OK',dst)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--rgbd-rate-hz',type=int,choices=(2,5),default=5)
    a=p.parse_args()
    build(a.source,a.out,rgbd_rate_hz=a.rgbd_rate_hz)

if __name__=='__main__': main()
