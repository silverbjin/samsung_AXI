"""C V1 explicit research approval P2: all tests use synthetic receipts only."""
import copy
from pathlib import Path
from types import SimpleNamespace
import pytest

from ai.train.dataset_v1_gate import VERSION, SPLIT_SHA, RELEASE_SHA, B_EXEC_SHA, IntakeHold
from ai.train.prepare_v1_research_approval import (
    prepare_approval, WEIGHT_SHA, PLAN_SHA, P1_OWNER_REPORT_SHA, ATTESTATION
)
from ai.train.train_classifier import enforce_locked_v1_args

ROOT = Path(__file__).resolve().parents[1]


def receipts():
    p0 = dict(verdict="CONTRACT_READY_HUMAN_REVIEW_REQUIRED",
              files_independently_hashed=42, dataset_version=VERSION,
              approved=18, excluded=2, family_count=5,
              preapproved_split_unchanged=True, training_permitted=False,
              test_opened_for_model_selection=False,
              production_contact="HOLD", AI_OFF="PROTECTED", A19="NOT_AUTHORIZED")
    p1 = dict(verdict="P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED",
              owner_p0_report_sha256="56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0",
              p1_plan_sha256=PLAN_SHA, dataset_version=VERSION, split_sha256=SPLIT_SHA,
              pretrained_weights_enum="ResNet18_Weights.IMAGENET1K_V1",
              pretrained_weights_sha256=WEIGHT_SHA,
              pretrained_weights_url="https://download.pytorch.org/models/resnet18-f37072fd.pth",
              pretrained_cached_bytes=46830571, torch_version="2.5.1+cpu",
              torchvision_version="0.20.1+cpu", pillow_version="10.2.0",
              pretrained_license_reviewed=False, C_research_approval_issued=False,
              training_permitted=False, training_executed=False, test_opened=False,
              production_contact="HOLD", AI_OFF="PROTECTED", A19="NOT_AUTHORIZED")
    plan = dict(status="PREDECLARED_NOT_APPROVED_TO_TRAIN",
                data={"version":VERSION, "release_sha256":RELEASE_SHA, "split_sha256":SPLIT_SHA},
                pretrained_weights={"enum":"ResNet18_Weights.IMAGENET1K_V1",
                                    "random_weight_fallback":False},
                execution={"phase":"frozen_head_only","device":"cpu","epochs":3,
                           "batch_size":4,"learning_rate":.0001,"seed":42,
                           "train_augmentation":"NONE","validation_augmentation":"NONE",
                           "test_augmentation":"NONE","max_frozen_runs":1,
                           "max_test_evaluations":1,"test_reselection_or_tuning":False,
                           "finetune":"NOT_AUTHORIZED_IN_V1_FIRST_PASS"},
                operational_inference={"confidence_min":0.8},
                policy={"production_contact":"HOLD","A19":"NOT_AUTHORIZED","AI_OFF":"PROTECTED"})
    return p0,p1,plan


def test_explicit_owner_approval_noncommercial_only():
    p0,p1,plan=receipts()
    a=prepare_approval(p0,p1,plan,ATTESTATION)
    assert a["decision"]=="C_P0_RESEARCH_TRAIN_GO"
    assert a["pretrained_license_reviewed"] is True
    assert a["commercial_use_approved"] is False
    assert a["weights_or_checkpoint_redistribution_approved"] is False
    assert a["test_evaluation_authorized"] is False
    assert a["AI_OFF"]=="PROTECTED" and a["A19"]=="NOT_AUTHORIZED"
    assert a["experiment_lock_sha256"]==PLAN_SHA
    assert a["p1_report_sha256"]==P1_OWNER_REPORT_SHA


@pytest.mark.parametrize("bad", ["", "COMMERCIAL", "NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH",
                                "RESEARCH_AND_PUBLIC_RELEASE"])
def test_broader_scope_denied(bad):
    p0,p1,plan=receipts()
    with pytest.raises(IntakeHold,match="C_V1_NONCOMMERCIAL_RESEARCH_SCOPE_NOT_ATTESTED"):
        prepare_approval(p0,p1,plan,bad)


@pytest.mark.parametrize(("key","value"), [
 ("verdict","HOLD"),("torch_version","2.5.2+cpu"),
 ("pretrained_weights_sha256","0"*64),("training_executed",True),
 ("test_opened",True),("pretrained_license_reviewed",True),
 ("AI_OFF","DISABLED"),("production_contact","PASS"),("A19","AUTHORIZED"),
 ("pretrained_cached_bytes",0)])
def test_untrusted_p1_denied(key,value):
    p0,p1,plan=receipts()
    p1[key]=value
    with pytest.raises(IntakeHold,match="C_V1_P1_OWNER_RECEIPT_MISMATCH"):
        prepare_approval(p0,p1,plan,ATTESTATION)


@pytest.mark.parametrize(("section","key","value"), [
 ("execution","epochs",4),("execution","batch_size",8),("execution","seed",43),
 ("execution","device","cuda"),("execution","learning_rate",.01),
 ("execution","finetune","ALLOWED"),("policy","A19","AUTHORIZED"),
 ("policy","AI_OFF","DISABLED")])
def test_plan_unlock_denied(section,key,value):
    p0,p1,plan=receipts()
    plan[section][key]=value
    with pytest.raises(IntakeHold):
        prepare_approval(p0,p1,plan,ATTESTATION)


def args(**kwargs):
    a=dict(demo_fixtures=False,phase="frozen",device="cpu",epochs=3,batch_size=4,
           lr=.0001,seed=42,init_checkpoint=None)
    a.update(kwargs)
    return SimpleNamespace(**a)


def test_real_train_exact_plan_args():
    _,_,plan=receipts()
    enforce_locked_v1_args(args(),plan)


@pytest.mark.parametrize(("key","value"), [
 ("phase","finetune"),("device","cuda"),("epochs",4),("batch_size",8),
 ("lr",.01),("seed",123),("init_checkpoint","old.pt")])
def test_real_train_cli_drift_denied(key,value):
    _,_,plan=receipts()
    with pytest.raises(IntakeHold,match="C_V1_FROZEN_RUN_HYPERPARAMETERS_CHANGED"):
        enforce_locked_v1_args(args(**{key:value}),plan)


def test_fixture_only_existing_training_path_unchanged():
    _,_,plan=receipts()
    enforce_locked_v1_args(args(demo_fixtures=True,epochs=7,phase="finetune"),plan)


def test_owner_runner_never_evaluates_test_or_uploads_model():
    s=(ROOT/"scripts/smartdish_c_v1_p2_frozen_owner_once.sh").read_text()
    assert 'source "$VENV/bin/activate"' in s
    assert 'python -m ai.train.train_classifier' in s and '--phase frozen' in s
    assert 'python -m ai.train.prepare_v1_research_approval' in s
    assert 'python -m ai.train.evaluate' not in s
    assert 'train --phase finetune' not in s
    assert 'with p.open("x"' in s
    assert 'tar -C "$OUT"' in s and 'checkpoint' not in s.split('tar -C "$OUT"')[1].split("sha256sum")[0]
    assert "P3_EVALUATION_EXECUTED" in s and "False" in s


def test_duplicate_p2_attempt_fails_before_private_train():
    s=(ROOT/"scripts/smartdish_c_v1_p2_frozen_owner_once.sh").read_text()
    assert "C_V1_P2_PREVIOUS_ATTEMPT_EXISTS_NO_AUTO_RETRY" in s
    assert s.index("C_V1_P2_PREVIOUS_ATTEMPT_EXISTS_NO_AUTO_RETRY") < s.index("python -m ai.train.prepare_v1_research_approval")
    assert "c_v1_p2_single_attempt_reserved.json" in s
