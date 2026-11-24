"""A-13 runner preflight, GUI default, no global ROS kill, no AI-off mutation."""
import ast
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BO=ROOT/"scripts/smartdish_a_tray_bootstrap.sh"
ONE=ROOT/"scripts/smartdish_a_tray_one_shot.sh"
RUN=ROOT/"scripts/smartdish_a_tray_live.py"


def test_shell_syntax_and_help_no_side_effects():
    for path in (BO,ONE):
        subprocess.run(["bash","-n",str(path)],check=True,timeout=10)
    p=subprocess.run(["bash",str(BO),"--help"],capture_output=True,text=True,timeout=5)
    assert p.returncode==0
    assert "Default GUI" in p.stdout
    assert "batch" in p.stdout


def test_non_wsl2_bootstrap_blocks_before_clone():
    p=subprocess.run(["bash",str(BO)],capture_output=True,text=True,timeout=10)
    assert p.returncode==2
    assert "SMARTDISH_A_TRAY_BOOTSTRAP_BLOCKED" in p.stderr
    assert "clone" not in p.stdout


def test_only_new_branch_and_unmodified_control():
    s=BO.read_text(); runner=RUN.read_text(); sh=ONE.read_text()
    assert "feat/smartdish-a-tray-camera" in s
    assert 'merge --ff-only' in s and 'GOT" == "$PIN' in s
    assert "MODE=--gui" in s and "MODE=--gui" in sh
    assert "p.set_defaults(gui=True)" in runner
    assert "SMARTDISH_A_TRAY_SOURCE_SHA" in s and "SMARTDISH_A_TRAY_SOURCE_SHA" in sh
    assert "pause: true multi_step: 5" in runner
    assert "verify_timing(**timing)" not in runner
    assert "verify_timing(stamp, observation_start_ns, observation_end_ns" in runner
    assert 'rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]))' in runner
    assert 'gz_call(env,WORLD,"pause: false")' in runner
    assert "save_unlabelled_frame" in runner
    # Guard logic moved to a pure function so L0 proves behavior, not text.
    assert "pre_event_ready(state[\"frame\"],state[\"sim_ns\"]," in runner
    assert "ROBOT_ONLY" not in runner
    assert "smartdish_a_tray_evidence.tar.gz" in runner
    assert all(token not in s+runner+sh for token in ("pkill", "killall", "rm -rf", "git reset --hard"))
    for protected in ("scripts/smartdish_e_wsl2_one_shot.sh",
                      "src/smartdish_robot/smartdish_robot/navigation_adapter.py",
                      "src/restaurant_world/worlds/restaurant.sdf"):
        assert (ROOT/protected).is_file()
    ast.parse(runner)


def test_real_physics_and_image_required_no_mock_success():
    src=RUN.read_text()
    assert "ROBOT_ONLY_REAL_GAZEBO" not in src
    assert "A13_PRE_EVENT_GAZEBO_CAMERA_NO_IMAGE" in src
    assert "A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED" in src
    assert "A13_CAMERA_FIRST_FRAME_DIAGNOSTICS" in src
    assert "A13_CAMERA_READY_DIAGNOSTICS" in src
    assert "ros_zero_stamp_callbacks" in src
    assert "gz_image_frame_probe_exit" in src
    assert "A13_GUI_ACTIVE_BUT_NO_LIVE_RGB_FRAMES" in src
    assert "A13_GAZEBO_GUI_START_FAILED_RC" in src
    assert "A13_RENDER_ENV_DIAGNOSTICS" in src
    assert "image_probe_report" in src
    assert 'env["LIBGL_ALWAYS_SOFTWARE"]=env.get(' not in src
    assert "node.count_publishers(TOPIC)" in src
    assert 'if camera_ready():' in src
    assert "A13_GAZEBO_NAMED_POSE_BRIDGE_NO_DISH" in src
    assert '"/smartdish/tray/pose/"+name' in src
    assert "A13_TEN_SIM_SECONDS_OBSERVATION_TIMEOUT" in src
    assert "PHYSICS_OBSERVATION_PASS" in src
    assert 'ground_truth":"NOT_OPERATOR_APPROVED"' in src

def test_pre_event_frame_requires_named_poses_and_monotonic_sim_clock():
    from types import SimpleNamespace
    import sys
    sys.path.insert(0,str(ROOT/"scripts"))
    from smartdish_a_tray_live import pre_event_ready

    msg=SimpleNamespace(header=SimpleNamespace(
        stamp=SimpleNamespace(sec=0,nanosec=200_000_000)))
    assert not pre_event_ready(None,200_000_000,{"dish_01":{}},["dish_01"])
    assert not pre_event_ready(msg,199_000_000,{"dish_01":{}},["dish_01"])
    assert not pre_event_ready(msg,200_000_000,{},["dish_01"])
    assert pre_event_ready(msg,200_000_000,{"dish_01":{}},["dish_01"])
    msg.header.stamp.nanosec=0
    assert not pre_event_ready(msg,200_000_000,{"dish_01":{}},["dish_01"])

def test_image_probe_requires_actual_bytes_not_exit_code(tmp_path):
    import sys
    sys.path.insert(0,str(ROOT/"scripts"))
    from smartdish_a_tray_live import image_probe_report
    p=tmp_path/"probe.txt"
    assert image_probe_report(p,0)["bytes"]==0
    assert not image_probe_report(p,0)["contains_image_dimensions"]
    p.write_bytes(b'header { stamp: 1 } width: 640 height: 480 data: "x"')
    d=image_probe_report(p,0)
    assert d["bytes"]>0 and d["contains_image_dimensions"]
    assert len(d["sha256"])==64

def test_gui_gate_requires_real_frames_and_two_cold_runs():
    wf=(ROOT/".github/workflows/smartdish-a-tray-ci.yml").read_text()
    assert "tray-l2-gui:" in wf
    assert "needs: tray-l2" in wf
    assert "SMARTDISH_A_TRAY_L2_GUI_COLD_2_OF_2_PASS" in wf
    assert "image_received_count" in wf
    assert "gui_active_during_physics" in wf
    assert "xvfb-run -a" in wf
    assert "smartdish_a_tray_evidence.tar.gz" in wf
