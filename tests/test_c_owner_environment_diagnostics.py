"""CI fixture-only tests: Owner environment doctor never trains or opens Test."""
from pathlib import Path
import subprocess
import pytest
from ai.train.owner_environment_diagnostics import (
    DiagnosticHold,verify_receipts,verify_environment,
    P0_SHA,PLAN_SHA,CKPT_SHA,WEIGHT_SHA,VERSION
)
ROOT=Path(__file__).resolve().parents[1]

def receipts():
    p0={"verdict":"CONTRACT_READY_HUMAN_REVIEW_REQUIRED",
        "files_independently_hashed":42,"dataset_version":VERSION}
    p1={"verdict":"P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED",
        "owner_p0_report_sha256":P0_SHA,"p1_plan_sha256":PLAN_SHA,
        "pretrained_weights_sha256":WEIGHT_SHA,
        "training_executed":False,"test_opened":False}
    p2={"verdict":"P2_FROZEN_TRAINED_AWAIT_C_REVIEW",
        "P1_plan_sha256":PLAN_SHA,"checkpoint_sha256":CKPT_SHA,
        "pretrained_weight_sha256":WEIGHT_SHA,"selected_epoch":3,
        "data_scope":"PHYSICS_OBSERVED","test_used_for_training":False,
        "test_evaluated":False,"C_RESEARCH_PILOT_ACCEPTED":False,
        "E_AI_ON":"HOLD","AI_OFF":"PROTECTED",
        "A19":"NOT_AUTHORIZED","production_contact":"HOLD"}
    return p0,p1,p2

def test_prior_receipts_reused():
    verify_receipts(*receipts())

@pytest.mark.parametrize(("idx","field","value"),[
 (0,"files_independently_hashed",41),
 (1,"pretrained_weights_sha256","0"*64),
 (1,"test_opened",True),(1,"training_executed",True),
 (2,"checkpoint_sha256","0"*64),(2,"selected_epoch",1),
 (2,"test_evaluated",True),(2,"P1_plan_sha256","0"*64),
 (2,"AI_OFF","DISABLED"),(2,"E_AI_ON","PASS"),
 (2,"A19","AUTHORIZED"),(2,"production_contact","PASS")])
def test_receipt_change_denied(idx,field,value):
    items=list(receipts());items[idx][field]=value
    with pytest.raises(DiagnosticHold):verify_receipts(*items)

def env():
    return {"venv_isolated":True,"python_version":"3.12.3",
            "torch":"2.5.1+cpu","torchvision":"0.20.1+cpu",
            "Pillow":"10.2.0","cuda_build":False,"wsl2":True}

def test_env_versions_locked():
    verify_environment(env())

@pytest.mark.parametrize(("field","value"),[
 ("venv_isolated",False),("python_version","3.11.9"),
 ("torch","2.6.0+cpu"),("torchvision","0.21.0+cpu"),
 ("Pillow","11.0.0"),("cuda_build",True),("wsl2",False)])
def test_env_drift_denied(field,value):
    e=env();e[field]=value
    with pytest.raises(DiagnosticHold):verify_environment(e)

def test_no_training_test_or_install_in_doctor():
    shell=(ROOT/"scripts/smartdish_c_v1_owner_diagnostics_once.sh").read_text()
    code=(ROOT/"ai/train/owner_environment_diagnostics.py").read_text()
    assert 'source "$VENV/bin/activate"' in shell
    assert "owner_environment_diagnostics" in shell
    assert "train_classifier" not in shell and "ai.train.evaluate" not in shell
    assert "pip install" not in shell and "apt-get" not in shell
    assert "read_verified_split" not in code
    assert "torch.load(" not in code and "predict_pil" not in code
    assert "P3_test_opened" in code
    assert "tar -C" in shell and "sha256sum" in shell

def test_bad_pin_fails_without_filesystem_writes(tmp_path):
    result=subprocess.run(["bash",str(ROOT/"scripts/smartdish_c_v1_owner_diagnostics_once.sh")],
          capture_output=True,text=True,env={"HOME":str(tmp_path),"PATH":"/usr/bin:/bin"})
    assert result.returncode==2
    assert "C_V1_DOCTOR_PIN_REQUIRED" in result.stderr
    assert list(tmp_path.iterdir())==[]

def test_future_owner_acceptance_bundles_doctor_automatically():
    # Owner already accepted 2026-11-27 P3 pretest: do NOT request another run.
    script=(ROOT/"scripts/smartdish_c_v1_p3_pretest_once.sh").read_text()
    assert 'python -m ai.train.owner_environment_diagnostics' in script
    assert 'python -m ai.train.p3_pretest_seal' in script
    assert script.index('python -m ai.train.owner_environment_diagnostics') < script.index('python -m ai.train.p3_pretest_seal')
    assert '--report "$OUT/environment_report.json"' in script
