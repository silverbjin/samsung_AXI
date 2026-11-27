"""Installer is explicit, isolated; P1 auto-activates existing venv without installing."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts/smartdish_c_v1_install_cpu_venv.sh"
P1 = ROOT / "scripts/smartdish_c_v1_p1_pretrained_once.sh"


def test_installer_has_explicit_cpu_pins_and_no_global_pip():
    src = INSTALL.read_text()
    assert "torch==2.5.1" in src and "torchvision==0.20.1" in src
    assert "Pillow==10.2.0" in src and "numpy==1.26.4" in src
    assert "https://download.pytorch.org/whl/cpu" in src
    assert '$VENV/bin/python" -m pip install' in src
    assert "/usr/bin/python3" in src and " -m venv " in src
    assert "--system-site-packages" not in src
    assert "pip install --user" not in src and "sudo pip" not in src
    assert "C_V1_UNMANAGED_VENV_REFUSED" in src
    assert "flock -n" in src


def test_installer_weights_are_explicit_opt_in():
    src = INSTALL.read_text()
    assert '"--with-weights"' in src
    assert 'if [[ "$WEIGHTS" == 1 ]]' in src
    assert "resnet18-f37072fd.pth" in src
    assert "pretrained_license_reviewed" in src
    assert "training_executed" in src and "False" in src


def test_runner_sources_dedicated_venv_and_never_installs():
    src = P1.read_text()
    assert 'source "$VENV/bin/activate"' in src
    assert 'python -m ai.train.p1_pretrained_inspection' in src
    assert 'export TORCH_HOME="$HOME/.cache/smartdish-c-v1/torch"' in src
    assert "C_V1_P1_VENV_NOT_INSTALLED" in src
    assert "pip install" not in src and "apt-get" not in src
    assert "python3 -m ai.train.train_classifier" not in src
    assert "python -m ai.train.evaluate" not in src


def test_installer_help_does_not_mutate_or_install(tmp_path):
    result = subprocess.run(["bash", str(INSTALL), "--help"],
                            capture_output=True, text=True, env={"HOME": str(tmp_path)})
    assert result.returncode == 0
    assert "--with-weights" in result.stdout
    assert not list(tmp_path.iterdir())


def test_missing_pin_does_not_create_environment(tmp_path):
    result = subprocess.run(["bash", str(INSTALL)], capture_output=True,
                            text=True, env={"HOME": str(tmp_path), "PATH": "/usr/bin:/bin"})
    assert result.returncode == 2
    assert "C_V1_INSTALL_IMMUTABLE_PIN_REQUIRED" in result.stderr
    assert not list(tmp_path.iterdir())
