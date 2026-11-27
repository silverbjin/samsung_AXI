"""Prepare a PRIVATE, scope-restricted P2 research approval using sealed P0/P1 receipts.

Does not train, open Test, alter B Dataset v1, download weights or grant model
redistribution rights. Only noncommercial internal educational research is in scope.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from ai.train.dataset_v1_gate import (
    VERSION, SPLIT_SHA, RELEASE_SHA, B_EXEC_SHA, IntakeHold, require, sha_file
)
from ai.train.p1_pretrained_inspection import (
    OWNER_P0_REPORT_SHA, validate_prior_review
)

P1_OWNER_REPORT_SHA = "8143ecc11a5b1a81cbbc6ca65d714eccd66b617e05467768478d7b16b59b1582"
WEIGHT_SHA = "f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec"
PLAN_SHA = "9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019"
ATTESTATION = "NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_NO_REDISTRIBUTION"
REVIEWER = "PROJECT_OWNER_EXPLICIT_CHAT_RESEARCH_APPROVAL_2026-11-27"
TERMS = (
    "https://docs.pytorch.org/vision/stable/models.html",
    "https://github.com/pytorch/vision/blob/main/LICENSE",
    "https://www.image-net.org/download",
)


def prepare_approval(p0: dict, p1: dict, plan: dict, attestation: str) -> dict:
    require(attestation == ATTESTATION,
            "C_V1_NONCOMMERCIAL_RESEARCH_SCOPE_NOT_ATTESTED")
    validate_prior_review(p0, plan)
    require(
        p1.get("verdict") == "P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED"
        and p1.get("owner_p0_report_sha256") == OWNER_P0_REPORT_SHA
        and p1.get("p1_plan_sha256") == PLAN_SHA
        and p1.get("dataset_version") == VERSION
        and p1.get("split_sha256") == SPLIT_SHA
        and p1.get("pretrained_weights_enum") == "ResNet18_Weights.IMAGENET1K_V1"
        and p1.get("pretrained_weights_sha256") == WEIGHT_SHA
        and p1.get("pretrained_weights_url")
          == "https://download.pytorch.org/models/resnet18-f37072fd.pth"
        and p1.get("pretrained_cached_bytes") == 46830571
        and p1.get("torch_version") == "2.5.1+cpu"
        and p1.get("torchvision_version") == "0.20.1+cpu"
        and p1.get("pillow_version") == "10.2.0"
        and p1.get("pretrained_license_reviewed") is False
        and p1.get("C_research_approval_issued") is False
        and p1.get("training_permitted") is False
        and p1.get("training_executed") is False
        and p1.get("test_opened") is False
        and p1.get("production_contact") == "HOLD"
        and p1.get("AI_OFF") == "PROTECTED"
        and p1.get("A19") == "NOT_AUTHORIZED",
        "C_V1_P1_OWNER_RECEIPT_MISMATCH")
    require(
        plan.get("data", {}).get("release_sha256") == RELEASE_SHA
        and plan.get("execution", {}).get("device") == "cpu"
        and plan.get("execution", {}).get("epochs") == 3
        and plan.get("execution", {}).get("batch_size") == 4
        and plan.get("execution", {}).get("learning_rate") == 1e-4
        and plan.get("execution", {}).get("seed") == 42
        and plan.get("execution", {}).get("finetune", "").startswith("NOT_AUTHORIZED")
        and plan.get("operational_inference", {}).get("confidence_min") == .8
        and plan.get("policy", {}).get("AI_OFF") == "PROTECTED"
        and plan.get("policy", {}).get("A19") == "NOT_AUTHORIZED",
        "C_V1_P2_LOCK_POLICY_CHANGED")
    return {
        "schema": 1, "decision": "C_P0_RESEARCH_TRAIN_GO",
        "decision_basis": "PROJECT_OWNER_EXPLICIT_RESEARCH_TRAINING_APPROVAL_2026-11-27",
        "reviewer": REVIEWER,
        "scope_attestation": ATTESTATION,
        "research_only": True,
        "commercial_use_approved": False,
        "weights_or_checkpoint_redistribution_approved": False,
        "AI_ON_product_approved": False,
        "safety_certification": False,
        "pretrained_license_reviewed": True,
        "rights_review_scope": "CONSERVATIVE_NONCOMMERCIAL_INTERNAL_EDUCATIONAL_RESEARCH_ONLY_NOT_LEGAL_CLEARANCE",
        "rights_review_sources": list(TERMS),
        "dataset_version": VERSION, "B_execution_pin": B_EXEC_SHA,
        "release_sha256": RELEASE_SHA, "split_sha256": SPLIT_SHA,
        "C_independent_files_verified": 42,
        "p0_report_sha256": OWNER_P0_REPORT_SHA,
        "p1_report_sha256": P1_OWNER_REPORT_SHA,
        "experiment_lock_sha256": PLAN_SHA,
        "pretrained_weight_sha256": WEIGHT_SHA,
        "training_phase": "frozen",
        "train": 11, "validation": 3, "test_sealed": 4,
        "max_frozen_runs": 1, "test_evaluation_authorized": False,
        "production_contact": "HOLD", "A19": "NOT_AUTHORIZED",
        "AI_OFF": "PROTECTED"
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--p0-report", type=Path, required=True)
    p.add_argument("--p1-report", type=Path, required=True)
    p.add_argument("--experiment-lock", type=Path, required=True)
    p.add_argument("--scope-attestation", type=str, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    # Do not read Test files or any private image: only previously approved receipts.
    require(sha_file(args.p0_report) == OWNER_P0_REPORT_SHA,
            "C_V1_P0_APPROVAL_RECEIPT_SHA_MISMATCH")
    require(sha_file(args.p1_report) == P1_OWNER_REPORT_SHA,
            "C_V1_P1_APPROVAL_RECEIPT_SHA_MISMATCH")
    require(sha_file(args.experiment_lock) == PLAN_SHA,
            "C_V1_P1_PLAN_PIN_CHANGED")
    obj = prepare_approval(
        json.loads(args.p0_report.read_text(encoding="utf-8")),
        json.loads(args.p1_report.read_text(encoding="utf-8")),
        json.loads(args.experiment_lock.read_text(encoding="utf-8")),
        args.scope_attestation)
    args.out.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Fail closed: private approval cannot be silently rewritten after first issue.
    with args.out.open("x", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    print("C_V1_LIMITED_RESEARCH_APPROVAL_SEALED "+json.dumps({
        "decision": obj["decision"], "scope": obj["scope_attestation"],
        "training_phase": obj["training_phase"], "p1_plan_sha256": PLAN_SHA,
        "pretrained_weight_sha256": WEIGHT_SHA,
        "test_evaluation_authorized": False, "AI_OFF": "PROTECTED"
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
