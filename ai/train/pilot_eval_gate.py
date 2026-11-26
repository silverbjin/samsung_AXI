"""V1 research pilot: human-sealed Test opening and transparent small-N metrics."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from ai.train.dataset_v1_gate import SPLIT_SHA, VERSION, IntakeHold, require, sha_file


def authorize_test_once(checkpoint: Path, manifest: Path, plan: Path,
                        approval_file: Path | None, lock_path: Path | None) -> dict:
    """Reserve the single permitted Test evaluation BEFORE loading Test images.

    A failed run leaves the lock in place: human review is required for retry.
    Approval and lock stay private; never commit them to the public repo.
    """
    require(approval_file is not None and approval_file.is_file() and
            lock_path is not None, "C_V1_TEST_APPROVAL_AND_LOCK_REQUIRED")
    require(checkpoint.is_file() and manifest.is_file() and plan.is_file(),
            "C_V1_TEST_SEAL_INPUT_MISSING")
    checkpoint_sha, split_sha, plan_sha = sha_file(checkpoint), sha_file(manifest), sha_file(plan)
    require(split_sha == SPLIT_SHA, "C_V1_TEST_SPLIT_SHA_CHANGED")
    plan_json = json.loads(plan.read_text(encoding="utf-8"))
    require(plan_json.get("data", {}).get("version") == VERSION and
            plan_json.get("execution", {}).get("max_test_evaluations") == 1 and
            plan_json.get("operational_inference", {}).get("confidence_min") == 0.8,
            "C_V1_TEST_PLAN_INVALID")
    approval = json.loads(approval_file.read_text(encoding="utf-8"))
    require(approval.get("decision") == "C_P3_SINGLE_TEST_GO" and
            approval.get("checkpoint_sha256") == checkpoint_sha and
            approval.get("split_sha256") == split_sha and
            approval.get("P1_plan_sha256") == plan_sha and
            approval.get("dataset_version") == VERSION and
            approval.get("threshold") == 0.8 and
            isinstance(approval.get("reviewer"), str) and bool(approval["reviewer"].strip()),
            "C_V1_TEST_SEAL_INVALID")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lock_path.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps({"state": "TEST_OPEN_RESERVED_ONCE",
                "checkpoint_sha256": checkpoint_sha, "P1_plan_sha256": plan_sha,
                "dataset_version": VERSION, "threshold": 0.8},sort_keys=True)+"\n")
    except FileExistsError as exc:
        raise IntakeHold("C_V1_TEST_ALREADY_OPENED_OR_PREVIOUS_FAILED") from exc
    return {"checkpoint_sha256": checkpoint_sha,"P1_plan_sha256": plan_sha,
            "dataset_version":VERSION,"threshold":0.8}


def pilot_metrics(truth: list[str], predicted: list[str], confidence: list[float],
                  *, threshold: float = 0.80) -> dict:
    """Raw all-sample binary matrix plus separate abstention/coverage accounting."""
    labels = ("STABLE", "UNSTABLE")
    require(len(truth) == len(predicted) == len(confidence) and len(truth) == 4,
            "C_V1_TEST_EXACTLY_FOUR_REQUIRED")
    require(set(truth) == set(labels) and all(x in labels for x in predicted) and
            all(type(s) in (int, float) and 0 <= s <= 1 for s in confidence),
            "C_V1_TEST_PREDICTION_INVALID")
    tp = sum(t == "UNSTABLE" and p == "UNSTABLE" for t,p in zip(truth,predicted))
    tn = sum(t == "STABLE" and p == "STABLE" for t,p in zip(truth,predicted))
    fp = sum(t == "STABLE" and p == "UNSTABLE" for t,p in zip(truth,predicted))
    fn = sum(t == "UNSTABLE" and p == "STABLE" for t,p in zip(truth,predicted))
    def f1(p, r): return 2*p*r/(p+r) if p+r else 0.0
    prec_u = tp/(tp+fp) if tp+fp else 0.0
    rec_u = tp/(tp+fn) if tp+fn else 0.0
    prec_s = tn/(tn+fn) if tn+fn else 0.0
    rec_s = tn/(tn+fp) if tn+fp else 0.0
    statuses = [p if s >= threshold else "UNKNOWN" for p,s in zip(predicted,confidence)]
    covered = sum(s != "UNKNOWN" for s in statuses)
    covered_correct = sum(s == t for s,t in zip(statuses,truth) if s != "UNKNOWN")
    return {"positive_label": "UNSTABLE", "sample_count":4,
            "raw_counts": {"TP":tp,"TN":tn,"FP":fp,"FN":fn},
            "raw_confusion_matrix_actual_rows_predicted_columns": [[tn,fp],[fn,tp]],
            "accuracy_closed_set": (tp+tn)/4,
            "per_class": {
                "STABLE":{"precision":prec_s,"recall":rec_s,"f1":f1(prec_s,rec_s)},
                "UNSTABLE":{"precision":prec_u,"recall":rec_u,"f1":f1(prec_u,rec_u)}},
            "balanced_accuracy":(rec_s+rec_u)/2,
            "macro_f1":(f1(prec_s,rec_s)+f1(prec_u,rec_u))/2,
            "threshold":threshold,"unknown_count":4-covered,"coverage":covered/4,
            "covered_accuracy":covered_correct/covered if covered else None,
            "unstable_to_stable_closed_set":fn,
            "unstable_to_stable_above_threshold":sum(t=="UNSTABLE" and p=="STABLE" and
                                                     s>=threshold for t,p,s in zip(truth,predicted,confidence)),
            "majority_baseline_descriptive_only":.75,
            "safety_certification":False,"generalization_certification":False,
            "test_used_for_model_selection":False}
