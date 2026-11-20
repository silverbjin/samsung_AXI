"""No synthetic AMCL success: verify native Nav2 real-sensor startup contract."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_s3_launch_respects_headless_mode_and_pinned_map():
    text=(ROOT/'src/restaurant_bringup/launch/navigation.launch.py').read_text()
    assert "DeclareLaunchArgument('gui',default_value='true')" in text
    assert "condition=IfCondition(LaunchConfiguration('gui'))" in text
    assert "'slam':'False'" in text
    assert "'use_composition':'False'" in text
    assert "LaunchConfiguration('map')" in text

def test_s3_actual_amcl_tfs_without_goal():
    text=(ROOT/'scripts/ci_s3_amcl_smoke.py').read_text()
    assert "'/amcl_pose'" in text and "'/initialpose'" in text
    assert "'/tf'" in text and "'/map'" in text and "'/scan'" in text
    assert "'navigate_to_pose'" in text and "goal_sent':False" in text
    assert 'RESTAURANT_S3_AMCL_L2_REAL_MAP_LOCALIZATION_PASS_NO_GOAL' in text
    assert "p.add_argument('--exercise-goals',action='store_true')" in text
    assert 'if args.exercise_goals:' in text
    assert "goal_sent':False" in text
    assert 'world_to_map' not in text or "validate_release" in text
