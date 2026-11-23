"""D05 runner Git/CI fixtures. Only temp Git repositories, never real WSL2 dirs."""
import os
import subprocess
from pathlib import Path
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/smartdish_d_wsl2_one_shot.sh"


def call(*cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def git(*args):
    result = call("git", *map(str, args))
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def w(tmp_path):
    seed = tmp_path / "seed"
    (seed / "src/smartdish_service/smartdish_service").mkdir(parents=True)
    (seed / "src/smartdish_service/package.xml").write_text("<package/>")
    (seed / "src/smartdish_service/smartdish_service/ui_app.py").write_text("# fixture")
    (seed / "tests").mkdir()
    for n in ("test_smartdish_d_service.py", "test_smartdish_d_ui.py"):
        (seed / "tests" / n).write_text("def test_ok(): assert True\n")
    git("init", "-q", "-b", "feat/smartdish-d-service", seed)
    git("-C", seed, "config", "user.email", "ci@example.invalid")
    git("-C", seed, "config", "user.name", "CI Fixture")
    git("-C", seed, "add", ".")
    git("-C", seed, "commit", "-qm", "fixture")
    remote = tmp_path / "remote.git"
    git("clone", "-q", "--bare", seed, remote)
    setup = tmp_path / "setup.bash"
    setup.write_text("export ROS_DISTRO=jazzy\n")
    mock = tmp_path / "bin"
    mock.mkdir()
    files = {
        "colcon": """#!/bin/bash
set -e
if [ "$1" = list ]; then
 [ "$CI_D_NO_PACKAGE" = 1 ] || echo smartdish_service
 exit 0
fi
if [ "$CI_D_BUILD_FAIL" = 1 ]; then exit 55; fi
mkdir -p "$SMARTDISH_D_TEST_STATE_DIR/install/smartdish_service"
echo '# mock overlay' > "$SMARTDISH_D_TEST_STATE_DIR/install/local_setup.bash"
echo MOCK_BUILD_ONLY
""",
        "ros2": """#!/bin/bash
if [ "$1" = pkg ] && [ "$2" = prefix ]; then
 echo "$SMARTDISH_D_TEST_STATE_DIR/install/smartdish_service"
elif [ "$1" = pkg ] && [ "$2" = executables ]; then
 echo "smartdish_service smartdish_manager"
 echo "smartdish_service smartdish_ui"
elif [ "$1" = launch ]; then
 echo MOCK_GUI_LAUNCHED
else exit 88; fi
"""
    }
    for name, contents in files.items():
        p = mock / name
        p.write_text(contents)
        p.chmod(0o755)
    worktree = tmp_path / "d-worktree"
    env = dict(os.environ, HOME=str(tmp_path), PATH=str(mock) + ":" + os.environ["PATH"],
        CI_D_NO_PACKAGE="0", CI_D_BUILD_FAIL="0",
        SMARTDISH_D_TEST_MODE="1", SMARTDISH_D_TEST_WORKDIR=str(worktree),
        SMARTDISH_D_TEST_REPO_URL=remote.as_uri(),
        SMARTDISH_D_TEST_ROS_SETUP=str(setup),
        SMARTDISH_D_TEST_STATE_DIR=str(tmp_path / "state"),
        PYTHONDONTWRITEBYTECODE="1")
    return seed, remote, worktree, env, tmp_path


def execute(w, mode="--preflight", **kw):
    r = call("bash", str(SCRIPT), mode, env=dict(w[3], **kw))
    return r, r.stdout + r.stderr


def test_ci_d01_fresh_clone(w):
    r, out = execute(w)
    assert r.returncode == 0 and "SMARTDISH_D_GIT_PASS" in out, out


def test_ci_d02_existing_clone(w):
    assert execute(w)[0].returncode == 0
    r, out = execute(w)
    assert r.returncode == 0 and "Cloning into" not in out, out


def test_ci_d03_wrong_origin(w):
    wrong = w[4] / "wrong"
    git("init", "-q", "-b", "feat/smartdish-d-service", wrong)
    git("-C", wrong, "remote", "add", "origin", (w[4] / "other.git").as_uri())
    r, out = execute(w, SMARTDISH_D_TEST_WORKDIR=str(wrong))
    assert r.returncode != 0 and "WRONG_ORIGIN" in out
    assert (wrong / ".git").exists()


def test_ci_d04_dirty_workspace(w):
    assert execute(w)[0].returncode == 0
    f = w[2] / "KEEP.txt"
    f.write_text("must keep")
    r, out = execute(w)
    assert r.returncode != 0 and "DIRTY_WORKTREE" in out
    assert f.read_text() == "must keep"


def test_ci_d05_unknown_branch(w):
    r, out = execute(w, SMARTDISH_D_TEST_BRANCH="not-a-branch")
    assert r.returncode != 0 and "REMOTE_BRANCH_NOT_FOUND" in out
    assert "VERIFY_PASS" not in out


def test_ci_d06_missing_test(w):
    (w[0] / "tests/test_smartdish_d_ui.py").unlink()
    git("-C", w[0], "add", "-A")
    git("-C", w[0], "commit", "-qm", "deleted test")
    git("-C", w[0], "push", "-q", w[1], "feat/smartdish-d-service")
    r, out = execute(w, "--verify")
    assert r.returncode != 0 and "REQUIRED_SOURCE_MISSING" in out
    assert "MOCK_BUILD_ONLY" not in out


def test_ci_d07_no_discovered_package(w):
    r, out = execute(w, "--verify", CI_D_NO_PACKAGE="1")
    assert r.returncode != 0 and "PACKAGE_NOT_DISCOVERED" in out


def test_ci_d08_colcon_build_failure(w):
    r, out = execute(w, "--verify", CI_D_BUILD_FAIL="1")
    assert r.returncode != 0 and "COLCON_BUILD_FAILED" in out
    assert "MOCK_GUI_LAUNCHED" not in out


def test_ci_d09_normal_verify(w):
    r, out = execute(w, "--verify")
    assert r.returncode == 0, out
    for marker in ("SMARTDISH_D_PYTEST_PASS", "SMARTDISH_D_BUILD_PASS",
                   "SMARTDISH_D_PACKAGE_PASS", "SMARTDISH_D_VERIFY_PASS_NO_GOAL"):
        assert marker in out


def test_ci_d10_repeat_verify(w):
    r1, out1 = execute(w, "--verify")
    r2, out2 = execute(w, "--verify")
    assert r1.returncode == r2.returncode == 0, (out1, out2)
    assert "Cloning into" not in out2
    assert not git("-C", w[2], "status", "--porcelain", "--untracked-files=all")


def test_ci_d11_existing_s7_directory_untouched(w):
    s7 = w[4] / "samsung_AXI"
    s7.mkdir()
    (s7 / "PRESERVE.txt").write_text("existing work")
    assert execute(w)[0].returncode == 0
    assert (s7 / "PRESERVE.txt").read_text() == "existing work"


def test_ci_d12_remote_advance_blocks_without_merge(w):
    assert execute(w)[0].returncode == 0
    (w[0] / "README.md").write_text("remote changed")
    git("-C", w[0], "add", ".")
    git("-C", w[0], "commit", "-qm", "advance")
    git("-C", w[0], "push", "-q", w[1], "feat/smartdish-d-service")
    r, out = execute(w)
    assert r.returncode != 0 and "REMOTE_HEAD_CHANGED" in out
    assert not (w[2] / "README.md").exists()


def test_ci_d13_default_mode_is_safe_verify(w):
    p = call("bash", str(SCRIPT), env=w[3])
    output = p.stdout + p.stderr
    assert p.returncode == 0, output
    assert "SMARTDISH_D_MODE=--verify" in output
    assert "SMARTDISH_D_VERIFY_PASS_NO_GOAL" in output
