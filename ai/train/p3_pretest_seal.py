"""Read-only P3 checkpoint preflight. NEVER open test split or issue test GO."""
import argparse
import json
from pathlib import Path
from ai.train.dataset_v1_gate import require, IntakeHold, sha_file, VERSION, SPLIT_SHA

SUMMARY_SHA="945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864"
PLAN_SHA="9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019"
CHECKPOINT_SHA="6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
WEIGHT_SHA="f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec"

def check_summary(summary,plan):
    require(summary.get("verdict")=="P2_FROZEN_TRAINED_AWAIT_C_REVIEW"
        and summary.get("checkpoint_sha256")==CHECKPOINT_SHA
        and summary.get("P1_plan_sha256")==PLAN_SHA
        and summary.get("pretrained_weight_sha256")==WEIGHT_SHA
        and summary.get("phase")=="frozen" and summary.get("seed")==42
        and summary.get("data_scope")=="PHYSICS_OBSERVED"
        and summary.get("selected_epoch")==3
        and summary.get("split_counts")=={
          "train":{"STABLE":8,"UNSTABLE":3},
          "val":{"STABLE":2,"UNSTABLE":1},"test":{}}
        and summary.get("test_evaluated") is False
        and summary.get("test_used_for_training") is False
        and summary.get("C_RESEARCH_PILOT_ACCEPTED") is False
        and summary.get("checkpoint_distribution_authorized") is False
        and summary.get("AI_OFF")=="PROTECTED"
        and summary.get("production_contact")=="HOLD"
        and summary.get("A19")=="NOT_AUTHORIZED"
        and summary.get("E_AI_ON")=="HOLD",
        "C_V1_P3_P2_SUMMARY_CONTRACT_CHANGED")
    epochs=summary.get("epochs",[])
    require(len(epochs)==3
        and [e.get("epoch") for e in epochs]==[1,2,3]
        and all(e.get("train",{}).get("samples")==11
            and e.get("val",{}).get("samples")==3 for e in epochs)
        and summary.get("best_val_loss")==min(e["val"]["loss"] for e in epochs),
        "C_V1_P3_P2_EPOCH_SELECTION_CHANGED")
    require(plan.get("data",{}).get("version")==VERSION
        and plan.get("data",{}).get("split_sha256")==SPLIT_SHA
        and plan.get("execution",{}).get("max_test_evaluations")==1
        and plan.get("operational_inference",{}).get("confidence_min")==.8,
        "C_V1_P3_EXPERIMENT_LOCK_CHANGED")

def check_metadata(ckpt):
    require(ckpt.get("architecture")=="resnet18_single_rgb"
        and ckpt.get("labels")==["STABLE","UNSTABLE"]
        and ckpt.get("image_size")==224
        and tuple(ckpt.get("mean",()))==(.485,.456,.406)
        and tuple(ckpt.get("std",()))==(.229,.224,.225)
        and ckpt.get("data_scope")=="PHYSICS_OBSERVED"
        and ckpt.get("phase")=="frozen"
        and ckpt.get("weight_init")=="PRETRAINED_OR_FINETUNED"
        and ckpt.get("split_manifest_sha256")==SPLIT_SHA
        and ckpt.get("research_dataset_version")==VERSION
        and ckpt.get("P1_plan_sha256")==PLAN_SHA
        and ckpt.get("research_release_status")=="UNREVIEWED_NOT_FOR_PRODUCT",
        "C_V1_P3_CHECKPOINT_METADATA_CHANGED")
    state=ckpt.get("model_state_dict")
    require(isinstance(state,dict)
        and tuple(getattr(state.get("fc.weight"),"shape",()))==(2,512)
        and tuple(getattr(state.get("fc.bias"),"shape",()))==(2,),
        "C_V1_P3_CHECKPOINT_FC_SHAPE_CHANGED")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("p2-summary","checkpoint","experiment-lock","report"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args()
    result={"verdict":"HOLD","P3_test_opened":False,"P3_test_authorized":False,
            "training_executed":False,"model_accepted":False,
            "AI_OFF":"PROTECTED","A19":"NOT_AUTHORIZED","production_contact":"HOLD"}
    try:
        require(sha_file(a.p2_summary)==SUMMARY_SHA,"C_V1_P3_P2_SUMMARY_SHA_MISMATCH")
        require(sha_file(a.experiment_lock)==PLAN_SHA,"C_V1_P3_PLAN_SHA_MISMATCH")
        require(a.checkpoint.is_file() and not a.checkpoint.is_symlink(),
                "C_V1_P3_PRIVATE_CHECKPOINT_MISSING")
        require(sha_file(a.checkpoint)==CHECKPOINT_SHA,"C_V1_P3_CHECKPOINT_SHA_MISMATCH")
        summary=json.loads(a.p2_summary.read_text())
        plan=json.loads(a.experiment_lock.read_text())
        check_summary(summary,plan)
        import torch
        ckpt=torch.load(a.checkpoint,map_location="cpu",weights_only=True)
        check_metadata(ckpt)
        result.update(verdict="P3_PRETEST_CHECKPOINT_SHA_PASS_PERFORMANCE_HOLD",
            checkpoint_sha256=CHECKPOINT_SHA,p2_summary_sha256=SUMMARY_SHA,
            P1_plan_sha256=PLAN_SHA, selected_epoch=3,
            validation_accuracy=1/3,
            validation_majority_baseline_accuracy=2/3,
            model_performance_status="HOLD_BELOW_VALIDATION_MAJORITY_BASELINE")
    except (IntakeHold,KeyError,OSError,ValueError,TypeError,ImportError) as e:
        result["reason"]=str(e).split(" ")[0]
    a.report.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,sort_keys=True,ensure_ascii=False,indent=2)+"\n")
    print("C_V1_P3_PRETEST "+json.dumps(result,sort_keys=True))
    return 0 if result["verdict"].startswith("P3_PRETEST_CHECKPOINT_SHA_PASS") else 2

if __name__=="__main__":
    raise SystemExit(main())
