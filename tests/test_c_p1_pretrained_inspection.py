"""P1 pin/plan regression tests. No private Owner files, torch or model download."""
import copy

import pytest

from ai.train.dataset_v1_gate import IntakeHold, VERSION, SPLIT_SHA
from ai.train.p1_pretrained_inspection import validate_prior_review, classify_import_failure, package_inventory


def p0():
    return {
        "verdict": "CONTRACT_READY_HUMAN_REVIEW_REQUIRED",
        "files_independently_hashed": 42, "dataset_version": VERSION,
        "approved": 18, "excluded": 2, "family_count": 5,
        "preapproved_split_unchanged": True, "training_permitted": False,
        "test_opened_for_model_selection": False,
        "production_contact": "HOLD", "AI_OFF": "PROTECTED", "A19": "NOT_AUTHORIZED",
    }


def plan():
    return {
        "status": "PREDECLARED_NOT_APPROVED_TO_TRAIN",
        "data": {"version": VERSION, "split_sha256": SPLIT_SHA},
        "pretrained_weights": {"enum": "ResNet18_Weights.IMAGENET1K_V1",
                               "random_weight_fallback": False},
        "execution": {"phase": "frozen_head_only",
                      "train_augmentation": "NONE",
                      "validation_augmentation": "NONE",
                      "test_augmentation": "NONE",
                      "max_frozen_runs": 1, "max_test_evaluations": 1,
                      "test_reselection_or_tuning": False},
        "policy": {"production_contact": "HOLD", "A19": "NOT_AUTHORIZED"},
    }


def test_aggregate_contract_accepted_but_not_training_approved():
    validate_prior_review(p0(), plan())


@pytest.mark.parametrize(("key", "value"), [
    ("files_independently_hashed", 4),
    ("training_permitted", True),
    ("test_opened_for_model_selection", True),
    ("production_contact", "PASS"),
    ("AI_OFF", "DISABLED"),
    ("A19", "AUTHORIZED"),
])
def test_unauthorized_p0_denied(key, value):
    record = p0()
    record[key] = value
    with pytest.raises(IntakeHold, match="C_V1_OWNER_P0_NOT_ACCEPTABLE"):
        validate_prior_review(record, plan())


@pytest.mark.parametrize(("group", "key", "value"), [
    ("execution", "max_frozen_runs", 2),
    ("execution", "test_reselection_or_tuning", True),
    ("execution", "train_augmentation", "HFLIP"),
    ("pretrained_weights", "enum", "ResNet18_Weights.DEFAULT"),
    ("pretrained_weights", "random_weight_fallback", True),
    ("policy", "production_contact", "PASS"),
])
def test_plan_policy_change_denied(group, key, value):
    exp = plan()
    exp[group][key] = value
    with pytest.raises(IntakeHold, match="C_V1_P1_PLAN_NOT_FROZEN"):
        validate_prior_review(p0(), exp)

@pytest.mark.parametrize(("module", "reason"), [
    ("torch", "C_V1_TORCH_MISSING"),
    ("torchvision", "C_V1_TORCHVISION_MISSING"),
    ("PIL", "C_V1_PILLOW_MISSING"),
    ("random_helper", "C_V1_P1_DEPENDENCY_IMPORT_FAILED"),
])
def test_exact_missing_module_classification(module, reason):
    exc = ModuleNotFoundError("test only: no import is attempted", name=module)
    assert classify_import_failure(exc) == (reason, module)


def test_non_module_import_fail_is_not_mislabeled_as_missing_wheel():
    assert classify_import_failure(ImportError("test simulated incompatible wheel")) == (
        "C_V1_P1_DEPENDENCY_IMPORT_FAILED", None)


def test_metadata_only_package_inventory_has_no_training_side_effect():
    info = package_inventory()
    assert set(info) == {"torch", "torchvision", "PIL"}
    assert all(set(item) == {"import_spec_found", "distribution_version"} for item in info.values())
    assert all(type(item["import_spec_found"]) is bool for item in info.values())
