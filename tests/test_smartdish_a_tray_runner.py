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
    assert 'rclpy.init(args=None,domain_id=int(env["ROS_DOMAIN_ID"]))' in runner
    assert 'gz_call(env,WORLD,"pause: false")' in runner
    assert "save_unlabelled_frame" in runner
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
    assert "GZ_IMAGE_TOPIC_ADVERTISED" in src
    assert "A13_GAZEBO_DYNAMIC_POSE_BRIDGE_NO_DISH" in src
    assert "A13_TEN_SIM_SECONDS_OBSERVATION_TIMEOUT" in src
    assert "PHYSICS_OBSERVATION_PASS" in src
    assert 'ground_truth":"NOT_OPERATOR_APPROVED"' in src
