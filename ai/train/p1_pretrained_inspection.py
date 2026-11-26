"""Read-only P1 environment/pretrained ResNet18 V1 inspection, never training.

No network calls, download, model initialization, Test pixel access or license
acceptance. Produces private aggregate evidence for C Owner human review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from pathlib import Path

from ai.train.dataset_v1_gate import VERSION, SPLIT_SHA, IntakeHold, require, sha_file

OWNER_P0_REPORT_SHA = "56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0"
EXPECTED_WEIGHTS = "ResNet18_Weights.IMAGENET1K_V1"


def validate_prior_review(p0: dict, plan: dict) -> None:
    """Verify only aggregate Owner result + pre-registered plan, no Test data."""
    require(p0.get("verdict") == "CONTRACT_READY_HUMAN_REVIEW_REQUIRED"
            and p0.get("files_independently_hashed") == 42
            and p0.get("dataset_version") == VERSION
            and p0.get("approved") == 18 and p0.get("excluded") == 2
            and p0.get("family_count") == 5
            and p0.get("preapproved_split_unchanged") is True
            and p0.get("training_permitted") is False
            and p0.get("test_opened_for_model_selection") is False
            and p0.get("production_contact") == "HOLD"
            and p0.get("AI_OFF") == "PROTECTED"
            and p0.get("A19") == "NOT_AUTHORIZED",
            "C_V1_OWNER_P0_NOT_ACCEPTABLE")
    data = plan.get("data", {})
    exec_plan = plan.get("execution", {})
    weights = plan.get("pretrained_weights", {})
    require(plan.get("status") == "PREDECLARED_NOT_APPROVED_TO_TRAIN"
            and data.get("version") == VERSION and data.get("split_sha256") == SPLIT_SHA
            and weights.get("enum") == EXPECTED_WEIGHTS
            and weights.get("random_weight_fallback") is False
            and exec_plan.get("phase") == "frozen_head_only"
            and exec_plan.get("train_augmentation") == "NONE"
            and exec_plan.get("validation_augmentation") == "NONE"
            and exec_plan.get("test_augmentation") == "NONE"
            and exec_plan.get("max_frozen_runs") == 1
            and exec_plan.get("max_test_evaluations") == 1
            and exec_plan.get("test_reselection_or_tuning") is False
            and plan.get("policy", {}).get("production_contact") == "HOLD"
            and plan.get("policy", {}).get("A19") == "NOT_AUTHORIZED",
            "C_V1_P1_PLAN_NOT_FROZEN")


def inspect(p0_path: Path, plan_path: Path) -> dict:
    require(p0_path.is_file(), "C_V1_P0_REPORT_MISSING")
    require(sha_file(p0_path) == OWNER_P0_REPORT_SHA,
            "C_V1_P0_REPORT_SHA_MISMATCH")
    require(plan_path.is_file(), "C_V1_EXPERIMENT_LOCK_MISSING")
    p0 = json.loads(p0_path.read_text(encoding="utf-8"))
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_prior_review(p0, plan)

    import torch
    import torchvision
    from PIL import __version__ as pillow_version
    from torchvision.models import ResNet18_Weights
    enum = ResNet18_Weights.IMAGENET1K_V1
    cache_path = Path(torch.hub.get_dir()) / "checkpoints" / enum.url.rsplit("/", 1)[-1]
    require(cache_path.is_file(), "C_V1_PRETRAINED_CACHE_MISSING")
    digest = sha_file(cache_path)
    require(len(digest) == 64, "C_V1_PRETRAINED_SHA_UNAVAILABLE")

    return {
        "schema": 1, "role": "C_V1_P1_PRETRAINED_READ_ONLY",
        "verdict": "P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED",
        "owner_p0_report_sha256": OWNER_P0_REPORT_SHA,
        "p1_plan_sha256": sha_file(plan_path),
        "dataset_version": VERSION, "split_sha256": SPLIT_SHA,
        "pretrained_weights_enum": EXPECTED_WEIGHTS,
        "pretrained_weights_url": enum.url,
        "pretrained_weights_sha256": digest,
        "pretrained_cached_bytes": cache_path.stat().st_size,
        "torch_version": torch.__version__,
        "torchvision_version": torchvision.__version__,
        "pillow_version": pillow_version,
        "python_version": platform.python_version(),
        "system": platform.system(),
        "pretrained_license_reviewed": False,
        "C_research_approval_issued": False,
        "training_permitted": False,
        "training_executed": False,
        "test_opened": False,
        "production_contact": "HOLD",
        "AI_OFF": "PROTECTED",
        "A19": "NOT_AUTHORIZED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--p0-report", type=Path, required=True)
    parser.add_argument("--experiment-lock", type=Path,
                        default=Path("ai/docs/C_V1_EXPERIMENT_LOCK.json"))
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema": 1, "role": "C_V1_P1_PRETRAINED_READ_ONLY",
              "verdict": "HOLD", "training_permitted": False,
              "training_executed": False, "test_opened": False,
              "production_contact": "HOLD", "AI_OFF": "PROTECTED",
              "A19": "NOT_AUTHORIZED"}
    try:
        result.update(inspect(args.p0_report, args.experiment_lock))
    except (IntakeHold, OSError, ValueError, ImportError, RuntimeError) as exc:
        result["reason"] = str(exc).split(" ")[0]
        result["verdict"] = "HOLD"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
    print("C_V1_P1_READ_ONLY " + json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["verdict"] == "P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
