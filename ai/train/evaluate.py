#!/usr/bin/env python3
"""C02: report single independent B `test` split exactly once per checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ai.evaluation.dataset_contract import LABEL_MAP, read_verified_split
from ai.evaluation.stability_model import load_checkpoint, predict_pil


def classification_metrics(truth: list[str], pred: list[str]) -> dict:
    labels = ("STABLE", "UNSTABLE")
    if not truth or len(truth) != len(pred):
        raise ValueError("C_EVALUATION_EMPTY_OR_MISALIGNED")
    if any(x not in labels for x in truth + pred):
        raise ValueError("C_EVALUATION_INVALID_LABEL")
    cm = [[sum(t == actual and p == predicted for t, p in zip(truth, pred))
           for predicted in labels] for actual in labels]
    supports = [sum(row) for row in cm]
    if not all(supports):
        raise ValueError("C_EVALUATION_CLASS_MISSING")
    f1 = []
    for i in range(2):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(2) if j != i)
        fn = sum(cm[i][j] for j in range(2) if j != i)
        denom = 2 * tp + fp + fn
        f1.append(2 * tp / denom if denom else 0.0)
    return {"accuracy": sum(cm[i][i] for i in range(2)) / len(truth),
            "macro_f1": sum(f1) / 2, "per_class_f1": dict(zip(labels, f1)),
            "labels_actual_rows_predicted_columns": list(labels),
            "confusion_matrix": cm, "support": dict(zip(labels, supports)),
            "sample_count": len(truth)}


def evaluate(args):
    from PIL import Image
    rows = read_verified_split(args.split_manifest, args.root, demo_fixtures=args.demo_fixtures)
    checkpoint_sha = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    import torch
    metadata = torch.load(args.checkpoint, weights_only=True, map_location="cpu")
    manifest_sha = hashlib.sha256(args.split_manifest.read_bytes()).hexdigest()
    if metadata.get("split_manifest_sha256") != manifest_sha:
        raise ValueError("C_EVALUATION_SPLIT_SHA_MISMATCH")
    model, model_version = load_checkpoint(args.checkpoint, device=args.device, allow_mock=args.demo_fixtures)
    truth, pred, scores = [], [], []
    for row in rows:
        if row["split"] != "test":
            continue
        with Image.open(args.root / row["image_path"]) as image:
            label, confidence = predict_pil(model, image, device=args.device)
        truth.append(row["label"])
        pred.append(label)
        scores.append(confidence)
    report = {"model_version": model_version, "checkpoint_sha256": checkpoint_sha,
              "split_manifest_sha256": manifest_sha, "metrics": classification_metrics(truth, pred),
              "test_confidences": scores, "test_predictions": pred,
              "data_scope": "MOCK_ONLY" if args.demo_fixtures else "PHYSICS_OBSERVED",
              "evaluation_scope": "MOCK_ONLY_SANITY_CHECK" if args.demo_fixtures else "INDEPENDENT_B_TEST",
              "performance_claim_allowed": not args.demo_fixtures}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(("C_MOCK_ONLY_TEST_EVALUATED " if args.demo_fixtures else "C_INDEPENDENT_TEST_EVALUATED ")
          + json.dumps(report["metrics"], sort_keys=True))
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-manifest", type=Path, default=Path("ai/data/split_manifest.csv"))
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    p.add_argument("--demo-fixtures", action="store_true", help="Opt-in MOCK_ONLY diagnostic metrics, not model performance")
    evaluate(p.parse_args())


if __name__ == "__main__":
    main()
