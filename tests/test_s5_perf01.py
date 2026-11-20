"""S5-PERF-01: read-only phase-aligned RTF + opt-in RGB-D candidate contracts."""
import importlib.util
from pathlib import Path
import subprocess
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]


def load(path,modname):
    spec=importlib.util.spec_from_file_location(modname,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_s5_phase_tags_are_taken_from_existing_goal_and_stop_markers():
    p=load(ROOT/'scripts/s5_perf_profile.py','s5_perf')
    assert p.phase_from_line('startup','S3_NAV02_REAL_GOAL_ACCEPTED=TABLE_3')=='normal_delivery'
    assert p.phase_from_line('normal_delivery','S3_NAV02_GOAL_SUCCEEDED=TABLE_3')=='table3_arrived'
    assert p.phase_from_line('table3_arrived','S3_NAV02_REAL_GOAL_ACCEPTED=PICKUP_RETURN')=='soup_return'
    assert p.phase_from_line('soup_return','S3_NAV02_GOAL_SUCCEEDED=PICKUP_RETURN')=='pickup_arrived'
    assert p.phase_from_line('pickup_arrived','S4_PHYSICAL_FIXTURE_LIDAR_POINTS=29 STOP_RECT_POINTS=29')=='safety_fixture'
    assert p.phase_from_line('safety_fixture','S4_COLLISION_MONITOR_REAL_SCAN_STOP_PASS')=='safety_pass'


def test_rtf_acceptance_requires_at_least_25_real_moving_samples():
    p=load(ROOT/'scripts/s5_perf_profile.py','s5_perf_summarize')
    no=p.summarize([])
    assert no['moving']['median'] is None
    assert no['moving_target_median_ge_90'] is False
    few=p.summarize([{'phase':'normal_delivery','rtf':.99}]*24)
    assert few['moving_target_median_ge_90'] is False
    good=p.summarize([{'phase':'normal_delivery','rtf':.95}]*15+
                     [{'phase':'soup_return','rtf':.91}]*15)
    assert good['moving_target_median_ge_90'] is True
    assert good['phase_normal_delivery']['sample_count']==15
    bad=p.summarize([{'phase':'normal_delivery','rtf':.7}]*35+
                    [{'phase':'soup_return','rtf':.99}]*5)
    assert bad['moving_target_median_ge_90'] is False
    assert 'NOT_CI_GPU_PROOF' in bad['claim']


def test_default_rgbd5_candidate_rgbd2_only_not_lidar_motor_or_world(tmp_path):
    module=load(ROOT/'scripts/prepare_waffle_rgbd.py','waffle_rgbd')
    source=tmp_path/'robot.sdf'
    source.write_text(
       '<sdf version="1.9"><model name="turtlebot3_waffle_pi">'
       '<link name="camera_link"/>'
       '<link name="camera_rgb_frame"><sensor name="camera" type="camera"/></link>'
       '<link name="base_scan"><sensor name="hls_lfcd_lds" type="gpu_lidar">'
       '<visualize>true</visualize></sensor></link>'
       '</model></sdf>')
    for hz in (2,5):
        out=tmp_path/f'rgbd_{hz}.sdf'
        if hz==5:module.build(source,out)
        else:module.build(source,out,rgbd_rate_hz=hz)
        root=ET.parse(out).getroot()
        camera=root.find(".//sensor[@name='restaurant_registered_rgbd']")
        assert camera is not None and camera.findtext('update_rate')==str(hz)
        assert camera.findtext('topic')=='restaurant/rgbd'
        assert camera.get('type')=='rgbd_camera'
        assert root.find(".//sensor[@name='camera']") is None
        assert root.findtext(".//sensor[@name='hls_lfcd_lds']/visualize")=='false'
    assert source.read_text().find('visualize>true')>0


def test_s5_opt_in_profile_does_not_mutate_existing_general_demo_contracts():
    wrapper=ROOT/'scripts/samsungaxi_wsl2_gui_acceptance_once.sh'
    core=ROOT/'scripts/restaurant_demo.sh'
    for path in (wrapper,core):
        subprocess.run(['bash','-n',str(path)],check=True)
    s=wrapper.read_text();t=core.read_text()
    assert '--perf-baseline' in s and '--perf-rgbd2' in s
    assert "S5_PERF_BLOCKED_PROFILE_WITH_NO_GOAL_PREFLIGHT" in s
    assert "S5_PERF_BLOCKED_PROFILE_SCRIPT_FETCH" in s
    assert "s5_perf_timeline.csv" in s and "s5_perf_summary.json" in s
    assert 'SAMSUNGAXI_DIAGNOSTIC_ZIP=' in s
    assert "if [[ \"$MODE\" == live ]]; then" in t
    assert 'RGBD_RATE_ARGS=(--rgbd-rate-hz 2)' in t
    assert 'S5_PERF_RGBD_RATE_HZ=5' in t and 'S5_PERF_RGBD_RATE_HZ=2' in t
    assert '--s5-integrated --gui --live-owner' in t
