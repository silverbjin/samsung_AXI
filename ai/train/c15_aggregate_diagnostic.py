"""C15 evidence-only frozen-head diagnostic. Pure stdlib: never reads private Test.

The input is the redacted public aggregate snapshot from an owner SHA-pinned
P2 archive. Raw Test images, predictions and checkpoints are not inputs.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

P2_ARCHIVE_SHA="914b9ea89c78fb1a4c3cad82c4f2d25869d422e618d477236c89f6ecd30f0516"
P2_SUMMARY_SHA="945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864"
P1_PLAN_SHA="9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019"
CHECKPOINT_SHA="6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
DATASET_VERSION="c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606"

class AuditHold(ValueError):
    pass

def require(condition: bool, code: str) -> None:
    if not condition:
        raise AuditHold(code)

def checked_correct(acc: float, n: int, name: str) -> int:
    require(type(acc) in (float,int) and math.isfinite(acc) and 0<=acc<=1,
            "C15_INVALID_"+name+"_ACCURACY")
    correct=round(acc*n)
    require(abs(acc*n-correct)<1e-9, "C15_NOT_INTEGER_CORRECT_"+name)
    return correct

def audit(snapshot: dict) -> dict:
    """Derive only aggregate-backed observations; keep all unknowns unknown."""
    require(snapshot.get("schema")==1
        and snapshot.get("source_scope")=="OWNER_P2_PUBLIC_AGGREGATES_ONLY"
        and snapshot.get("source_archive_sha256")==P2_ARCHIVE_SHA
        and snapshot.get("source_summary_sha256")==P2_SUMMARY_SHA
        and snapshot.get("experiment_lock_sha256")==P1_PLAN_SHA
        and snapshot.get("dataset_version")==DATASET_VERSION
        and snapshot.get("checkpoint_sha256")==CHECKPOINT_SHA
        and snapshot.get("pretest_verdict")=="P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD",
        "C15_EVIDENCE_PROVENANCE_MISMATCH")
    require(snapshot.get("train")=={"STABLE":8,"UNSTABLE":3}
        and snapshot.get("val")=={"STABLE":2,"UNSTABLE":1}
        and snapshot.get("test_sealed_count")==4
        and snapshot.get("threshold")==.8
        and snapshot.get("selected_epoch")==3
        and snapshot.get("test_opened") is False
        and snapshot.get("test_used_for_training") is False
        and snapshot.get("test_evaluated") is False
        and snapshot.get("model_accepted") is False
        and snapshot.get("AI_OFF")=="PROTECTED"
        and snapshot.get("A19")=="NOT_AUTHORIZED"
        and snapshot.get("production_contact")=="HOLD"
        and snapshot.get("E_AI_ON")=="HOLD",
        "C15_LOCKED_SCOPE_OR_TEST_CHANGED")
    epochs=snapshot.get("epochs",[])
    require(len(epochs)==3 and [e.get("epoch") for e in epochs]==[1,2,3],
            "C15_EPOCH_COUNT_DRIFT")
    numbers=[]
    for e in epochs:
        record={"epoch":e["epoch"]}
        for split,n in (("train",11),("val",3)):
            x=e.get(split,{})
            require(x.get("samples")==n
                and type(x.get("loss")) in (int,float)
                and math.isfinite(x["loss"]) and x["loss"]>=0,
                "C15_"+split.upper()+"_AGGREGATE_DRIFT")
            correct=checked_correct(x.get("accuracy"),n,split.upper())
            record[split]={"samples":n,"correct":correct,
                           "accuracy":x["accuracy"],"cross_entropy":x["loss"]}
        numbers.append(record)
    val_losses=[e["val"]["cross_entropy"] for e in numbers]
    train_losses=[e["train"]["cross_entropy"] for e in numbers]
    require(snapshot.get("best_val_loss")==min(val_losses)
        and val_losses.index(min(val_losses))==2,
        "C15_BEST_EPOCH_CONTRACT_DRIFT")
    train_correct=numbers[-1]["train"]["correct"]
    val_correct=numbers[-1]["val"]["correct"]
    train_majority=8
    val_majority=2
    require(train_correct==4 and val_correct==1
        and train_majority>train_correct and val_majority>val_correct,
        "C15_OBSERVED_PERFORMANCE_NOT_MATCHING_EVIDENCE")
    return {
        "schema":1,"role":"C15_FROZEN_P2_AGGREGATE_DIAGNOSTIC",
        "verdict":"C15_EVIDENCE_DIAGNOSIS_COMPLETE_PERFORMANCE_HOLD",
        "source_p2_archive_sha256":P2_ARCHIVE_SHA,
        "source_p2_summary_sha256":P2_SUMMARY_SHA,
        "checkpoint_sha256":CHECKPOINT_SHA,
        "test_sealed_count":4,
        "train":{"n":11,"correct":train_correct,"accuracy":train_correct/11,
                 "majority_correct":train_majority,"majority_accuracy":train_majority/11},
        "validation":{"n":3,"correct":val_correct,"accuracy":val_correct/3,
                      "majority_correct":val_majority,"majority_accuracy":val_majority/3},
        "epoch_metrics":numbers,
        "best_epoch":3,"best_val_loss":min(val_losses),
        "train_loss_start":train_losses[0],"train_loss_end":train_losses[-1],
        "validation_loss_start":val_losses[0],"validation_loss_end":val_losses[-1],
        "classifier_trainable_parameters":1026,
        "frozen_backbone":True,"planned_optimizer_steps":9,
        "proven_findings":[
            "ONE_FROZEN_HEAD_RUN_COMPLETED_WITH_PREDECLARED_MIN_CE_SELECTION",
            "FINAL_TRAIN_AND_VAL_ACCURACY_BELOW_STABLE_MAJORITY_BASELINES",
            "TRAIN_AND_VAL_CROSS_ENTROPY_DECREASED_BUT_ACCURACY_REMAINED_LOW",
            "ONLY_THREE_VALIDATION_SAMPLES_ONE_UNSTABLE_SAMPLE",
            "STATIC_RGB_T0_PRECEDES_PHYSICS_OUTCOME"
        ],
        "not_determinable":[
            "CLASS_SPECIFIC_CONFUSION_OR_UNSTABLE_FALSE_NEGATIVES",
            "CALIBRATED_CONFIDENCE_OR_UNKNOWN_COVERAGE_AT_0_80",
            "FAMILY_PER_SAMPLE_ERRORS_OR_VISUAL_CAUSALITY",
            "CAUSE_OF_UNDERPERFORMANCE_WITHOUT_NEW_PRIVATE_PER_SAMPLE_EVIDENCE",
            "POST_TRAIN_CHECKPOINT_TRAIN_SET_ACCURACY"
        ],
        "candidate_explanations_not_proven":[
            "TINY_TRAIN_VAL_SUPPORT_AND_CLASS_IMBALANCE",
            "SHORT_FROZEN_LINEAR_HEAD_OPTIMIZATION",
            "WEAK_VISUAL_PREDICTABILITY_OF_POST_TORQUE_PHYSICS_AT_PRE_TORQUE_T0",
            "EXIF_RGB_CENTRE_CROP_OR_DOMAIN_SHIFT_MAY_DROP_RELEVANT_CUES",
            "WITHIN_FAMILY_SIMILARITY_OR_VISUAL_SHORTCUTS"
        ],
        "training_executed":False,"test_evaluated":False,
        "P3_test_authorized":False,"P3_test_opened":False,
        "retraining_authorized":False,"AI_OFF":"PROTECTED",
        "production_contact":"HOLD","A19":"NOT_AUTHORIZED",
        "E_AI_ON":"HOLD"
    }

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--snapshot",type=Path,default=Path("ai/docs/C_V1_P2_AGGREGATE_EVIDENCE_LOCK.json"))
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    report=audit(json.loads(args.snapshot.read_text(encoding="utf8")))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf8")
    print("C15_REVIEW "+json.dumps({"verdict":report["verdict"],"test_opened":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
