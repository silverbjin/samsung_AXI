"""C16 research first-pass disposition. No private data/Test/weight access."""
import copy
import json
from pathlib import Path
import pytest
from ai.train.c15_aggregate_diagnostic import audit,AuditHold
from ai.train.c16_research_disposition import decide

ROOT=Path(__file__).resolve().parents[1]
SNAPSHOT=ROOT/"ai/docs/C_V1_P2_AGGREGATE_EVIDENCE_LOCK.json"

def approved_evidence():
    return audit(json.loads(SNAPSHOT.read_text(encoding="utf8")))

def test_c16_negative_first_pass_retained():
    d=decide(approved_evidence())
    assert d["verdict"]=="C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT"
    assert d["research_model_acceptance"]=="HOLD_NOT_ACCEPTED"
    assert d["C_RESEARCH_PILOT_ACCEPTED"] is False
    assert d["single_frozen_run_completed"] is True
    assert d["P3_test_approval_issued"] is False
    assert d["P3_test_opened"] is False and d["P3_test_evaluated"] is False
    assert d["retraining_authorized"] is False and d["finetune_authorized"] is False
    assert d["A19_new_data_authorized"] is False
    assert d["product_model_handoff_authorized"] is False
    assert d["D_E_handoff_scope"]=="CONTRACT_ONLY_UNKNOWN_AND_STAFF_CONFIRMATION"
    assert d["AI_OFF"]=="PROTECTED" and d["E_AI_ON"]=="HOLD"
    assert d["no_new_owner_WSL2_action_required"] is True
    assert [x["status"] for x in d["future_options"]]==[
        "DEFAULT_TECHNICAL_DISPOSITION","REQUIRES_NEW_PM_APPROVAL","NOT_APPROVED"]

@pytest.mark.parametrize(("target","value"),[
    ("verdict","PASS"),("P3_test_authorized",True),
    ("P3_test_opened",True),("retraining_authorized",True),
    ("test_evaluated",True),("checkpoint_sha256","0"*64),
    ("AI_OFF","DISABLED"),("A19","AUTHORIZED"),
    ("production_contact","PASS")])
def test_changed_gate_fails_closed(target,value):
    e=approved_evidence();e[target]=value
    with pytest.raises(AuditHold):decide(e)

def test_validation_result_cannot_be_falsely_upgraded():
    e=approved_evidence();e["validation"]["correct"]=2
    with pytest.raises(AuditHold):decide(e)

def test_no_read_test_train_or_model_import():
    src=(ROOT/"ai/train/c16_research_disposition.py").read_text()
    assert "torch.load(" not in src
    assert "read_verified_split(" not in src
    assert "predict_pil(" not in src
    assert "ai.train.evaluate" not in src
    assert "train_classifier" not in src
    assert "P3_ONE_TIME_DESCRIPTIVE_TEST" in src
