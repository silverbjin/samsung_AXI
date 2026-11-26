#!/usr/bin/env python3
"""C01: run one ResNet18 baseline (frozen) or one small fine-tuning phase.

Production training only accepts PHYSICS_OBSERVED. Explicit --demo-fixtures
allows isolated B-generated MOCK_ONLY pipeline smoke, never a deployable model.
Neither mode accepts DACON generic structures or S7 plate-presence labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from ai.evaluation.dataset_contract import read_verified_split, summarize
from ai.evaluation.stability_model import LABELS, IMAGE_SIZE, MEAN, STD, new_resnet18, preprocess


def train(args):
    import torch
    import torch.nn as nn
    from PIL import Image
    from torch.utils.data import DataLoader, Dataset

    approval_metadata = None
    if not args.demo_fixtures:
        from ai.train.research_approval import approve_training
        approval_metadata = approve_training(
            args.root, args.split_manifest,
            getattr(args, "research_approval", None),
            getattr(args, "experiment_lock", Path("ai/docs/C_V1_EXPERIMENT_LOCK.json")),
            phase=args.phase, p0_report=getattr(args, "p0_report", None))
    rows = read_verified_split(args.split_manifest, args.root,
                               demo_fixtures=args.demo_fixtures,
                               training_only=not args.demo_fixtures)
    if args.phase == "finetune" and not args.init_checkpoint:
        raise ValueError("C_FINETUNE_BASELINE_CHECKPOINT_REQUIRED")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if not args.demo_fixtures:
        torch.use_deterministic_algorithms(True)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    class TrayDataset(Dataset):
        def __init__(self, split):
            self.items = [r for r in rows if r["split"] == split]
        def __len__(self):
            return len(self.items)
        def __getitem__(self, index):
            row = self.items[index]
            with Image.open(args.root / row["image_path"]) as image:
                tensor = preprocess(image)
            return tensor, LABELS.index(row["label"])

    loaders = {
        s: DataLoader(TrayDataset(s), batch_size=args.batch_size,
                      shuffle=(s == "train"), num_workers=0)
        for s in ("train", "val")
    }
    if args.phase == "frozen":
        model = new_resnet18(pretrained=not args.demo_fixtures)
        for name, param in model.named_parameters():
            param.requires_grad = name.startswith("fc.")
    else:
        from ai.evaluation.stability_model import load_checkpoint
        import torch
        metadata = torch.load(args.init_checkpoint, map_location="cpu", weights_only=True)
        current_sha = hashlib.sha256(args.split_manifest.read_bytes()).hexdigest()
        if metadata.get("split_manifest_sha256") != current_sha:
            raise ValueError("C_FINETUNE_SPLIT_SHA_MISMATCH")
        model, _ = load_checkpoint(args.init_checkpoint, allow_mock=args.demo_fixtures)
        for name, param in model.named_parameters():
            param.requires_grad = name.startswith(("layer4.", "fc."))
    model.to(args.device)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr)
    criterion = nn.CrossEntropyLoss()
    history = []
    best_val, best_state = float("inf"), None
    for epoch in range(args.epochs):
        epoch_log = {"epoch": epoch + 1}
        for split in ("train", "val"):
            model.train(split == "train")
            total_loss, seen, correct = 0.0, 0, 0
            for x, y in loaders[split]:
                x, y = x.to(args.device), y.to(args.device)
                with torch.set_grad_enabled(split == "train"):
                    logits = model(x)
                    loss = criterion(logits, y)
                    if split == "train":
                        optimizer.zero_grad()
                        loss.backward()
                        optimizer.step()
                n = y.size(0)
                total_loss += loss.item() * n
                seen += n
                correct += int((logits.argmax(dim=1) == y).sum())
            epoch_log[split] = {"loss": total_loss / seen, "accuracy": correct / seen,
                                "samples": seen}
        history.append(epoch_log)
        if epoch_log["val"]["loss"] < best_val:
            best_val = epoch_log["val"]["loss"]
            # Copy to CPU immediately so the best epoch cannot mutate.
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"architecture": "resnet18_single_rgb", "labels": list(LABELS),
                "image_size": IMAGE_SIZE, "mean": list(MEAN), "std": list(STD),
                "data_scope": "MOCK_ONLY" if args.demo_fixtures else "PHYSICS_OBSERVED",
                "weight_init": "RANDOM_DEMO_ONLY" if args.demo_fixtures and args.phase == "frozen" else "PRETRAINED_OR_FINETUNED",
                "phase": args.phase,
                "split_manifest_sha256": hashlib.sha256(args.split_manifest.read_bytes()).hexdigest(),
                "research_release_status": "UNREVIEWED_NOT_FOR_PRODUCT",
                "research_dataset_version": approval_metadata["dataset_version"] if approval_metadata else "MOCK_ONLY",
                "P1_plan_sha256": approval_metadata["plan_sha256"] if approval_metadata else "MOCK_ONLY",
                "model_state_dict": best_state}, args.out)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {"phase": args.phase, "seed": args.seed, "device": args.device,
              "data_scope": "MOCK_ONLY" if args.demo_fixtures else "PHYSICS_OBSERVED",
              "deployment_allowed": False,  # P2 training never equals P4 research release
              "training_evidence": "DEMO_PIPELINE_ONLY" if args.demo_fixtures else "REAL_TRAINING",
              "split_manifest_sha256": hashlib.sha256(args.split_manifest.read_bytes()).hexdigest(),
              "checkpoint_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
              "checkpoint": str(args.out), "dataset": summarize(rows),
              "epochs": history, "test_used_for_training": False,
              "P1_approval": approval_metadata or "MOCK_ONLY"}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'C_{"MOCK_ONLY_" if args.demo_fixtures else ""}{args.phase.upper()}_TRAINED ' + json.dumps({
        "checkpoint_sha256": report["checkpoint_sha256"], "val_loss": best_val}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-manifest", type=Path, default=Path("ai/data/split_manifest.csv"))
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--phase", choices=("frozen", "finetune"), required=True)
    p.add_argument("--demo-fixtures", action="store_true",
                   help="Opt-in B MOCK_ONLY samples; random init; never deployable")
    p.add_argument("--init-checkpoint", type=Path)
    p.add_argument("--p0-report", type=Path,
                   help="independent immutable Owner P0 report (no Test pixels read here)")
    p.add_argument("--research-approval", type=Path,
                   help="private C human approval for real Dataset v1 training; no auto-GO")
    p.add_argument("--experiment-lock", type=Path,
                   default=Path("ai/docs/C_V1_EXPERIMENT_LOCK.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    args = p.parse_args()
    if args.epochs < 1 or args.batch_size < 1 or args.lr <= 0:
        p.error("epochs, batch-size and lr must be positive")
    train(args)


if __name__ == "__main__":
    main()
