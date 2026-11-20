"""S5 L0 regression: operator delay must not stop ROS callbacks or bypass safety."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SMOKE=ROOT/'scripts/ci_s3_amcl_smoke.py'

def test_s5_owner_no_blocking_input_while_ros_executor_waits():
    src=SMOKE.read_text()
    assert 'answer=input(' not in src, "RED: synchronous input() starves ROS callbacks"
    assert 'wait_for_owner_approval(' in src
    assert 'S5_OWNER_FRESH_SCAN_ODOM_AFTER_APPROVAL' in src

def test_s5_pre_goal_stale_gate_is_not_weakened():
    src=SMOKE.read_text()
    assert "time.monotonic()-state['scan_t']>8 or time.monotonic()-state['odom_t']>8" in src
    assert "NAV_PREGOAL_SENSOR_STALE_" in src
    assert "S5_OWNER_GOAL_CONFIRMATION_MISSING" in src
