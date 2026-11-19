"""Owner one-shot is static/argument-validated without WSL2 or ROS.

Actual Gazebo and the WSLg image remain integration/owner acceptance gates.
"""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / 'scripts' / 'owner_wsl2_once.sh'
CORE = ROOT / 'scripts' / 'restaurant_demo.sh'


def call(*args):
    return subprocess.run(['bash', str(OWNER), *args], capture_output=True, text=True, timeout=10)


def test_owner_syntax_and_selftest_no_ros_no_network():
    for path in [OWNER, CORE]:
        subprocess.run(['bash', '-n', str(path)], check=True)
    r = call('world', '--self-test', '--ref', 'a'*40)
    assert r.returncode == 0, r.stderr
    assert 'RESTAURANT_OWNER_WSL2_SELF_TEST_PASS_NO_ROS_NO_GOAL' in r.stdout


def test_invalid_ref_and_menu_block_before_side_effects():
    for args in [('demo', '--ref', 'branch-with-spaces'), ('demo', 'SPICY'), ('no-such-mode',)]:
        r = call(*args)
        assert r.returncode == 2, (args, r.stdout, r.stderr)


def test_safe_checkout_and_no_bypass():
    text = OWNER.read_text()
    assert 'status --porcelain' in text
    assert 'FETCH_HEAD' in text
    assert 'OWNER_PINNED_SHA' in text
    assert '--force' not in text.split('# Checkout without force.')[0]
    assert 'pkill' not in text and 'killall' not in text
    assert 'set +u\n# shellcheck disable=SC1091\nsource /opt/ros/jazzy/setup.bash\nset -u' in text


def test_world_uses_same_rgbd_overlay_as_ci():
    text = CORE.read_text()
    assert text.index('prepare_waffle_rgbd.py') < text.index('if [[ "$MODE" == world ]]')
    assert 'world.launch.py robot_sdf:="$ROBOT_SDF"' in text
    assert '45633014a14e8f438495b532a723e4ad45cbbd31' in text
