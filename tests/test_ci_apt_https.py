"""Protect the CI-only HTTPS APT fallback after two observed port-80 failures."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_https_only_in_runtime_container():
    w=(ROOT/'.github/workflows/restaurant-ci.yml').read_text()
    step=w.split('name: Install official ROS 2 / Gazebo Harmonic runtime',1)[1]
    step=step.split('name: Checkout pinned official ROBOTIS',1)[0]
    assert '/etc/apt/sources.list.d/ubuntu.sources' in step
    assert 'https://archive.ubuntu.com/ubuntu' in step
    assert 'https://security.ubuntu.com/ubuntu' in step
    assert 'APT::Update::Error-Mode=any' in step
    assert 'Acquire::Retries=1' in step
    assert 'sudo ' not in step
    assert 'wsl --shutdown' not in step

def test_ros_and_gazebo_stages_unchanged():
    w=(ROOT/'.github/workflows/restaurant-ci.yml').read_text()
    assert 'python3 scripts/ci_s2_map_smoke.py' in w
    assert 'RESTAURANT_CI_L1_BUILD_PASS' in w
    assert 'ci_gazebo_smoke.py' in w
