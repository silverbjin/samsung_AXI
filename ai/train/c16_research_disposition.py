"""C16 decision from C15 read-only public aggregates: no Test or new training."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from ai.train.c15_aggregate_diagnostic import audit,AuditHold

def decide(c15: dict)->dict:
    """Technical review (not a human P3 authorization or product/model approval)."""
    if c15.get("verdict")!="C15_EVIDENCE_DIAGNOSIS_COMPLETE_PERFORMANCE_HOLD":
        raise AuditHold("C16_C15_REVIEW_NOT_VERIFIED")
    if (c15.get("validation",{}).get("correct")!=1
        or c15.get("validation",{}).get("n")!=3
        or c15["validation"].get("majority_correct")!=2
        or c15.get("test_evaluated") is not False
        or c15.get("P3_test_opened") is not False
        or c15.get("P3_test_authorized") is not False
        or c15.get("retraining_authorized") is not False
        or c15.get("checkpoint_sha256")!="6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
        or c15.get("AI_OFF")!="PROTECTED"
        or c15.get("A19")!="NOT_AUTHORIZED"
        or c15.get("production_contact")!="HOLD"):
        raise AuditHold("C16_EVIDENCE_OR_PROTECTION_CONTRACT_CHANGED")
    return {
        "schema":1,"role":"C16_DATASET_V1_FIRST_FROZEN_PASS_TECHNICAL_REVIEW",
        "verdict":"C16_FIRST_RESEARCH_PASS_CLOSED_NEGATIVE_VALIDATION_RESULT",
        "c15_verdict":c15["verdict"],
        "owner_research_training_GO_already_consumed":True,
        "single_frozen_run_completed":True,
        "P0_private_intake":"PASS_REUSED",
        "P1_pretrained_cpu":"PASS_REUSED",
        "P2_training_execution":"PASS_REUSED",
        "P3_pretest_checkpoint_integrity":"PASS_REUSED",
        "research_model_acceptance":"HOLD_NOT_ACCEPTED",
        "C_RESEARCH_PILOT_ACCEPTED":False,
        "reason":"VALIDATION_1_OF_3_BELOW_MAJORITY_2_OF_3_AND_NO_RISK_METRICS",
        "first_pass_learning_outcome":"NEGATIVE_OR_INCONCLUSIVE_NOT_PRODUCT_EVIDENCE",
        "P3_test_approval_issued":False,
        "P3_test_opened":False,
        "P3_test_evaluated":False,
        "P3_recommendation":"KEEP_SEALED_NO_AUTOMATIC_EVALUATION",
        "checkpoint_SHA256":c15["checkpoint_sha256"],
        "threshold_locked":0.8,
        "retraining_authorized":False,"finetune_authorized":False,
        "A19_new_data_authorized":False,
        "split_change_authorized":False,
        "future_options":[
            {"id":"CLOSE_V1_FIRST_PASS","status":"DEFAULT_TECHNICAL_DISPOSITION",
             "condition":"retain frozen negative outcome, private checkpoint and sealed Test"},
            {"id":"FUTURE_V2_RESEARCH_CHANGE_REQUEST","status":"REQUIRES_NEW_PM_APPROVAL",
             "condition":"new data/feature/label rights and physically grounded validation; lock future protocol BEFORE new Test or training"},
            {"id":"P3_ONE_TIME_DESCRIPTIVE_TEST","status":"NOT_APPROVED",
             "condition":"separate explicit human Test GO and frozen checkpoint/0.80; descriptive-only; no tuning or product acceptance"}
        ],
        "D_E_handoff_scope":"CONTRACT_ONLY_UNKNOWN_AND_STAFF_CONFIRMATION",
        "product_model_handoff_authorized":False,
        "research_checkpoint_distribution_authorized":False,
        "AI_OFF":"PROTECTED","E_AI_ON":"HOLD",
        "A19":"NOT_AUTHORIZED","production_contact":"HOLD",
        "no_new_owner_WSL2_action_required":True
    }

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot",type=Path,default=Path("ai/docs/C_V1_P2_AGGREGATE_EVIDENCE_LOCK.json"))
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    verdict=decide(audit(json.loads(args.snapshot.read_text(encoding="utf8"))))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(verdict,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf8")
    print("C16_RESEARCH_REVIEW "+json.dumps({
        "verdict":verdict["verdict"],
        "P3_test_opened":verdict["P3_test_opened"],
        "E_AI_ON":verdict["E_AI_ON"]
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
