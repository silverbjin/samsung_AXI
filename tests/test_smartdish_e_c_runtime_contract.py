"""C runtime adoption contract: C's venv, not another pip installation."""
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"scripts/smartdish_e_c_runtime_guard.py"
spec=importlib.util.spec_from_file_location("runtime_guard",path)
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

def fixture(tmp_path):
    v=tmp_path/"smartdish-c-v1-py312-cpu"
    (v/"bin").mkdir(parents=True)
    (v/"lib/python3.12/site-packages").mkdir(parents=True)
    (v/"bin/python").write_text("# fake interpreter\n")
    metadata={"status":"C_V1_CPU_VENV_INSTALLED","isolated":True,
              "cpu_only":True,"training_executed":False,"test_opened":False,
              "installer_source_pin":"a"*40,**guard.PINS}
    (v/".smartdish_c_v1_environment.json").write_text(json.dumps(metadata))
    return v,metadata

def test_E_runner_consumes_C_venv_before_preflight_pass():
    script=(ROOT/"scripts/smartdish_e_owner_aion.sh").read_text()
    launch=(ROOT/"src/smartdish_service/launch/smartdish_e_owner_aion.launch.py").read_text()
    cnode=(ROOT/"src/smartdish_ai/smartdish_ai/stability_inference_node.py").read_text()
    assert 'C_VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"' in script
    assert script.index("smartdish_e_c_runtime_guard.py") < script.index(
        "E_OWNER_AION_PREFLIGHT_PASS_OWNER_SCOPE_NO_GOAL")
    assert "SMARTDISH_E_C_SITE_PACKAGES" in script
    assert "flock -n -s" in script
    assert "pip install" not in script and "apt-get" not in script
    assert "additional_env=c_env" in launch
    assert "E_OWNER_C_RUNTIME_CONTRACT_NOT_VERIFIED" in launch
    assert "E_OWNER_C_MODEL_LOAD_FAILED" in cnode

def test_missing_or_incomplete_C_venv_blocks(tmp_path):
    with pytest.raises(guard.ContractBlocked,match="C_VENV_MISSING"):
        guard.inspect_venv(tmp_path/"missing")
    assert list(tmp_path.iterdir())==[]
    v,_=fixture(tmp_path)
    (v/".smartdish_c_v1_install_pending").touch()
    with pytest.raises(guard.ContractBlocked,match="INCOMPLETE"):
        guard.inspect_venv(v)

@pytest.mark.parametrize("field,bad",[
    ("status","NO"),("isolated",False),("cpu_only",False),
    ("torch","2.6.0"),("torchvision","0.19.0"),
    ("numpy","2.0"),("Pillow","11.0"),
    ("training_executed",True),("test_opened",True),
    ("installer_source_pin","not-a-sha")])
def test_C_receipt_drift_blocks(tmp_path,field,bad):
    v,receipt=fixture(tmp_path)
    receipt[field]=bad
    (v/".smartdish_c_v1_environment.json").write_text(json.dumps(receipt))
    with pytest.raises(guard.ContractBlocked):
        guard.inspect_venv(v)

def test_C_venv_import_and_system_ROS_interpreter_are_both_probed(tmp_path):
    v,_=fixture(tmp_path)
    calls=[]
    def fake_run(command,**kwargs):
        calls.append((command,kwargs))
        return subprocess.CompletedProcess(command,0,"","")
    py=Path("/usr/bin/python3")
    if not py.exists():pytest.skip("No system Python")
    result=guard.verify_runtime(v,py,runner=fake_run)
    assert result==v/"lib/python3.12/site-packages"
    assert len(calls)==2
    assert calls[0][0][0]==str(v/"bin/python")
    assert calls[1][0][0]==str(py)
    assert calls[1][1]["env"]["PYTHONPATH"].startswith(str(result))
    assert "import rclpy" in calls[1][0][-1]

def test_torch_missing_in_C_venv_is_a_hard_block(tmp_path):
    v,_=fixture(tmp_path)
    def missing(command,**kwargs):
        return subprocess.CompletedProcess(command,1,"",
          "ModuleNotFoundError: No module named 'torch'")
    with pytest.raises(guard.ContractBlocked,match="C_VENV_IMPORT_OR_ABI_FAILURE"):
        guard.verify_runtime(v,Path("/usr/bin/python3"),runner=missing)


def test_immutable_pin_migration_is_ancestry_checked_and_non_destructive():
    script=(ROOT/"scripts/smartdish_e_owner_aion.sh").read_text()
    assert 'CURRENT_HEAD="$(git -C "$WORKDIR" rev-parse HEAD)"' in script
    assert '4dbdeca6a0a8f8120cb42a44bd589d356726eb5d' in script
    assert 'git -C "$WORKDIR" merge-base --is-ancestor "$CURRENT_HEAD" "$PIN"' in script
    assert 'git -C "$WORKDIR" checkout --quiet --detach "$PIN"' in script
    assert "E_OWNER_RUNTIME_PIN_FAST_FORWARD" in script
    assert "git reset --hard" not in script and "git clean" not in script
    assert "git checkout main" not in script


def test_owner_tray_reliability_inherits_A13_without_changing_default():
    import ast
    path = ROOT / "src/smartdish_ai/smartdish_ai/stability_inference_node.py"
    tree = ast.parse(path.read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "tray_image_reliability")
    ns = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)
    assert ns["tray_image_reliability"](True) == "RELIABLE"
    assert ns["tray_image_reliability"](False) == "BEST_EFFORT"
    assert ns["tray_image_reliability"]("true") == "BEST_EFFORT"


def test_installed_origin_guard_rejects_drift(tmp_path):
    p=ROOT/"scripts/smartdish_e_installed_origin.py"
    spec=importlib.util.spec_from_file_location("installed_origin",p)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    a=tmp_path/"source";b=tmp_path/"installed"
    a.write_text("exact source");b.write_text("exact source")
    assert module.same_bytes(a,b)==module.digest(a)
    b.write_text("old source")
    with pytest.raises(RuntimeError,match="INSTALLED_SOURCE_MISMATCH"):module.same_bytes(b,a)

def test_owner_runner_self_check_and_per_pin_build():
    script=(ROOT/"scripts/smartdish_e_owner_aion.sh").read_text()
    assert "316639a0a5c47121f3026c76e180efde3cea12d4" in script
    assert "RUNNER_BYTES_MISMATCH" in script
    assert 'STATE="$HOME/.local/state/smartdish-e-owner-aion/$PIN"' in script
    assert script.index("smartdish_e_installed_origin.py")<script.index("E_OWNER_AION_LAUNCHING_C_D_ONLY")
