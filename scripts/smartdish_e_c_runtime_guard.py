#!/usr/bin/env python3
"""E Owner read-only consumer of C's pre-existing isolated CPU runtime.

Does not install packages, retrain, open Test4, read weights, or change ROS.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

PINS = {"torch": "2.5.1+cpu", "torchvision": "0.20.1+cpu",
        "numpy": "1.26.4", "Pillow": "10.2.0"}
PY_CHECK = """
import sys,torch,torchvision,numpy,PIL
assert sys.version_info[:2] == (3,12), "PYTHON_312_REQUIRED"
assert torch.__version__ == "2.5.1+cpu", "TORCH_VERSION_DRIFT"
assert torchvision.__version__ == "0.20.1+cpu", "VISION_VERSION_DRIFT"
assert numpy.__version__ == "1.26.4", "NUMPY_VERSION_DRIFT"
assert PIL.__version__ == "10.2.0", "PILLOW_VERSION_DRIFT"
assert torch.version.cuda is None, "C_RUNTIME_MUST_BE_CPU"
"""

class ContractBlocked(RuntimeError):
    pass

def inspect_venv(path):
    path = Path(path).expanduser()
    python = path / "bin/python"
    receipt = path / ".smartdish_c_v1_environment.json"
    site = path / "lib/python3.12/site-packages"
    if path.is_symlink() or not path.is_dir():
        raise ContractBlocked("C_VENV_MISSING_OR_SYMLINK")
    if (not python.is_file() or not receipt.is_file() or not site.is_dir()
            or (path / ".smartdish_c_v1_install_pending").exists()):
        raise ContractBlocked("C_VENV_INCOMPLETE")
    try:
        meta = json.loads(receipt.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise ContractBlocked("C_VENV_RECEIPT_UNREADABLE") from exc
    if (meta.get("status") != "C_V1_CPU_VENV_INSTALLED"
            or meta.get("isolated") is not True or meta.get("cpu_only") is not True
            or meta.get("training_executed") is not False
            or meta.get("test_opened") is not False
            or not re.fullmatch(r"[0-9a-f]{40}", str(meta.get("installer_source_pin", "")))):
        raise ContractBlocked("C_VENV_RECEIPT_POLICY_DRIFT")
    for name, expected in PINS.items():
        if meta.get(name) != expected:
            raise ContractBlocked("C_VENV_VERSION_DRIFT_" + name.upper())
    return python, site

def verify_runtime(venv, ros_python=Path("/usr/bin/python3"), runner=subprocess.run):
    python, site = inspect_venv(venv)
    if not ros_python.is_file():
        raise ContractBlocked("ROS_SYSTEM_PYTHON_NOT_FOUND")
    env = dict(os.environ)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    own_code = (
        "import pathlib,sys\n"
        "assert sys.prefix!=sys.base_prefix, 'VENV_INACTIVE'\n"
        "assert pathlib.Path(sys.prefix).resolve()==pathlib.Path("
        + repr(str(Path(venv).resolve())) + ").resolve(), 'WRONG_VENV'\n"
        + PY_CHECK)
    for label, exe, code, patch in (
        ("C_VENV", python, own_code, {}),
        ("ROS_C", ros_python,
         PY_CHECK + "\nimport rclpy\nfrom sensor_msgs.msg import Image\n",
         {"PYTHONPATH": str(site) + (":" + env["PYTHONPATH"]
                                   if env.get("PYTHONPATH") else "")}),
    ):
        try:
            result = runner([str(exe), "-c", code], capture_output=True,
                            text=True, timeout=60, env={**env, **patch})
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ContractBlocked(label + "_IMPORT_PROBE_UNAVAILABLE") from exc
        if result.returncode != 0:
            raise ContractBlocked(label + "_IMPORT_OR_ABI_FAILURE")
    return site

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--c-venv",type=Path,required=True)
    p.add_argument("--ros-python",type=Path,default=Path("/usr/bin/python3"))
    a=p.parse_args()
    try:
        site=verify_runtime(a.c_venv,a.ros_python)
    except ContractBlocked as exc:
        print("E_OWNER_C_RUNTIME_BLOCKED="+str(exc),file=sys.stderr)
        return 2
    print("E_OWNER_C_RUNTIME_REUSED_VERIFIED")
    print("E_OWNER_C_RUNTIME_SITE_PACKAGES="+str(site))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
