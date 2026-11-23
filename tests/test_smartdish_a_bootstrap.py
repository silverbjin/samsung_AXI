"""A-08: bootstrap is one-command, fail-closed and no forced Git reset."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BOOT = ROOT / "scripts/smartdish_a_wsl2_bootstrap.sh"


def test_syntax_and_help_without_cloning():
    subprocess.run(["bash", "-n", str(BOOT)], check=True, timeout=6)
    r = subprocess.run(["bash", str(BOOT), "--help"], capture_output=True,
                       text=True, timeout=6)
    assert r.returncode == 0
    assert "--gui" in r.stdout and "--headless" in r.stdout
    assert "/dev/tty" in r.stdout
    assert "Default: WSLg" in r.stdout


def test_linux_ci_preflight_never_downloads_or_drives():
    r = subprocess.run(["bash", str(BOOT), "--headless"], capture_output=True,
                       text=True, timeout=8)
    assert r.returncode == 2
    assert "SMARTDISH_A_BOOTSTRAP_BLOCKED_NO_GOAL" in r.stderr
    assert "SMARTDISH_A_BOOTSTRAP_CLONE=" not in r.stdout


def test_only_owner_branch_ff_update_and_human_gate():
    text = BOOT.read_text()
    assert "feat/smartdish-a-robot" in text
    assert "\nMODE=--gui\n" in text
    assert "--headless  Explicit fallback" in text
    assert "https://github.com/silverbjin/samsung_AXI.git" in text
    assert 'TARGET="$HOME/samsung_AXI_A"' in text
    assert 'git -C "$TARGET" merge --ff-only FETCH_HEAD' in text
    assert 'SMARTDISH_A_BOOTSTRAP_HUMAN_TTY_APPROVAL_REQUIRED' in text
    assert 'exec bash scripts/smartdish_a_wsl2_one_shot.sh "$MODE"' in text
    for forbidden in ("reset --hard", "git clean -fd", "rm -rf",
                      "git push --force", "YES-SMARTDISH-A-GOALS\\n"):
        assert forbidden not in text
