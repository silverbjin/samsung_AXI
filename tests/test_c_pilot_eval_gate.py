"""Never opens real Test; verifies numerical/approval contracts with mock arrays."""
from pathlib import Path
import pytest
from ai.train.pilot_eval_gate import authorize_test_once, pilot_metrics
from ai.train.dataset_v1_gate import IntakeHold


def test_requires_single_test_approval_before_open(tmp_path):
    with pytest.raises(IntakeHold,match="C_V1_TEST_APPROVAL_AND_LOCK_REQUIRED"):
        authorize_test_once(tmp_path/"model.pt",tmp_path/"split.csv",tmp_path/"plan.json",
                            None,tmp_path/"test.lock")


def test_report_tp_tn_fp_fn_and_abstention():
    r=pilot_metrics(["STABLE","STABLE","STABLE","UNSTABLE"],
                    ["STABLE","UNSTABLE","STABLE","STABLE"],
                    [.90,.55,.99,.95])
    assert r["raw_counts"]=={"TP":0,"TN":2,"FP":1,"FN":1}
    assert r["raw_confusion_matrix_actual_rows_predicted_columns"]==[[2,1],[1,0]]
    assert r["unknown_count"]==1 and r["coverage"]==.75
    assert r["unstable_to_stable_above_threshold"]==1
    assert r["safety_certification"] is False


def test_reject_non_four_test_rows():
    with pytest.raises(IntakeHold,match="C_V1_TEST_EXACTLY_FOUR_REQUIRED"):
        pilot_metrics(["STABLE"],["STABLE"],[.9])


def test_unknown_threshold_applies_without_retraining():
    r=pilot_metrics(["STABLE","STABLE","STABLE","UNSTABLE"],
                    ["STABLE","STABLE","STABLE","UNSTABLE"],
                    [.79,.79,.79,.79])
    assert r["coverage"]==0 and r["covered_accuracy"] is None
    assert r["raw_counts"]=={"TP":1,"TN":3,"FP":0,"FN":0}


def test_immutable_test_open_is_one_shot(tmp_path,monkeypatch):
    import hashlib,json
    from ai.train import pilot_eval_gate as gate
    from ai.train.dataset_v1_gate import VERSION
    ck=tmp_path/"model.pt";ck.write_bytes(b"FAKE_CHECKPOINT_CONTRACT_ONLY")
    split=tmp_path/"split.csv";split.write_text("FAKE_LOCK_TEST_NO_REAL_ROWS")
    plan=tmp_path/"plan.json"
    plan.write_text(json.dumps({"data":{"version":VERSION},
        "execution":{"max_test_evaluations":1},
        "operational_inference":{"confidence_min":0.8}}))
    sh=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    monkeypatch.setattr(gate,"SPLIT_SHA",sh(split))
    approval=tmp_path/"approval.json"
    approval.write_text(json.dumps({"decision":"C_P3_SINGLE_TEST_GO",
       "checkpoint_sha256":sh(ck),"split_sha256":sh(split),
       "P1_plan_sha256":sh(plan),"dataset_version":VERSION,
       "threshold":0.8,"reviewer":"unit-test-synthetic"}))
    lock=tmp_path/"test.lock"
    assert gate.authorize_test_once(ck,split,plan,approval,lock)["threshold"]==.8
    with pytest.raises(IntakeHold,match="C_V1_TEST_ALREADY_OPENED_OR_PREVIOUS_FAILED"):
        gate.authorize_test_once(ck,split,plan,approval,lock)
