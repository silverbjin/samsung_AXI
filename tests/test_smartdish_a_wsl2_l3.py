"""A-07 L0: WSL2 script contracts without starting Gazebo or authorizing goals."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from smartdish_a_wsl2_l3 import LEGS, assess_leg

RUNNER = ROOT / "scripts/smartdish_a_wsl2_one_shot.sh"
NODE = ROOT / "scripts/smartdish_a_wsl2_l3.py"


def ok_leg():
    return dict(result="SUCCEEDED", reason="", odom_count=20,
                scan_count=10, odom_max_m=1.25, amcl_error_m=.12)


def test_three_exact_nav2_legs_and_real_evidence_gate():
    assert LEGS == (("TO_TABLE", "T03"), ("TO_RETURN", "DISH_RETURN"),
                    ("TO_HOME", "HOME"))
    assert assess_leg(ok_leg()) == ""


@pytest.mark.parametrize("field,bad,reason", [
    ("result", "FAILED", "NAV2_RESULT_NOT_SUCCEEDED"),
    ("reason", "ABORTED", "NAV2_RESULT_NOT_SUCCEEDED"),
    ("odom_count", 0, "PHYSICAL_SENSOR_SAMPLES_MISSING"),
    ("scan_count", 0, "PHYSICAL_SENSOR_SAMPLES_MISSING"),
    ("odom_max_m", 0., "PHYSICAL_ODOM_MOVEMENT_NOT_PROVEN"),
    ("amcl_error_m", None, "MAP_FRAME_GOAL_ACCURACY_NOT_PROVEN"),
    ("amcl_error_m", 1.2, "MAP_FRAME_GOAL_ACCURACY_NOT_PROVEN"),
    ("amcl_error_m", float("nan"), "MAP_FRAME_GOAL_ACCURACY_NOT_PROVEN"),
])
def test_bad_or_missing_evidence_never_passes(field, bad, reason):
    item = ok_leg()
    item[field] = bad
    assert assess_leg(item) == reason


def test_script_syntax_and_help_never_start_gazebo():
    subprocess.run(["bash", "-n", str(RUNNER)], check=True, timeout=5)
    result = subprocess.run(["bash", str(RUNNER), "--help"],
                            text=True, capture_output=True, timeout=5)
    assert result.returncode == 0
    assert "--headless" in result.stdout
    assert "--gui" in result.stdout


def test_owner_runner_cannot_be_used_on_linux_ci():
    # This subprocess never builds ROS or launches Gazebo on a non-WSL2 runner.
    result = subprocess.run(["bash", str(RUNNER), "--headless"],
                            text=True, capture_output=True, timeout=12)
    assert result.returncode == 2
    assert "SMARTDISH_A_WSL2_BLOCKED_NO_GOAL" in result.stderr
    assert "SMARTDISH_A_WSL2_OWNER_L3_PASS" not in result.stdout


def test_real_owner_human_tty_and_pinned_map_are_not_bypassed():
    shell = RUNNER.read_text()
    node = NODE.read_text()
    assert "[[ -t 0 && -r /dev/tty && -w /dev/tty ]]" in shell
    assert 'grep -qiE' in shell and '/proc/sys/kernel/osrelease' in shell
    assert 'src/smartdish_robot/config/table_poses.yaml' in shell
    assert 'maps/candidates/s2_map03/restaurant_map.yaml' in shell
    assert 's6_stagger_nav_start:=true' in node
    assert 'SMARTDISH_A_WSL2_OWNER_L3_PASS' in shell
    assert 'HUMAN_OPERATOR_TYPED_TO_DEV_TTY' in node
    assert 'stdin=subprocess.DEVNULL' in node
    assert 'publisher.publish(msg)' in node
    assert 'wait_until(lambda: publisher.get_subscription_count() >= 1' in node
    assert 'SMARTDISH_A_WSL2_ROBOT_ONLY_3LEG_L3_PASS' in node
    assert 'YES-SMARTDISH-A-GOALS\\n' not in node
    assert '/cmd_vel' not in node


def test_error_bundle_present_on_preflight_rejection(tmp_path):
    # Package script body promises a final summary and compressed recent logs.
    text = RUNNER.read_text()
    assert 'smartdish_a_owner_evidence.tar.gz' in text
    assert 'summary.json' in text and 'l3_evidence.json' in text
    assert 'first_error' in text
