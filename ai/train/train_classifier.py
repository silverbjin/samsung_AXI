#!/usr/bin/env python3
"""C01: run one ResNet18 baseline (frozen) or one small fine-tuning phase.

Never trains on B contract fixtures, official DACON generic structure images,
or S7 STACKED/NOT_STACKED images. Run from repository root with python -m.
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

    rows = read_verified_split(args.split_manifest, args.root)
    if args.phase == "finetune" and not args.init_checkpoint:
        raise ValueError("C_FINETUNE_BASELINE_CHECKPOINT_REQUIRED")
    random.seed(args.seed)
    torch.manual_seed(args.seed)

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
        model = new_resnet18(pretrained=True)
        for name, param in model.named_parameters():
            param.requires_grad = name.startswith("fc.")
    else:
        from ai.evaluation.stability_model import load_checkpoint
        model, _ = load_checkpoint(args.init_checkpoint)
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
                "data_scope": "PHYSICS_OBSERVED", "phase": args.phase,
                "split_manifest_sha256": hashlib.sha256(args.split_manifest.read_bytes()).hexdigest(),
                "model_state_dict": best_state}, args.out)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    report = {"phase": args.phase, "seed": args.seed, "device": args.device,
              "split_manifest_sha256": hashlib.sha256(args.split_manifest.read_bytes()).hexdigest(),
              "checkpoint_sha256": hashlib.sha256(args.out.read_bytes()).hexdigest(),
              "checkpoint": str(args.out), "dataset": summarize(rows),
              "epochs": history, "test_used_for_training": False}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f'C_{args.phase.upper()}_TRAINED ' + json.dumps({
        "checkpoint_sha256": report["checkpoint_sha256"], "val_loss": best_val}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--split-manifest", type=Path, default=Path("ai/data/split_manifest.csv"))
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--phase", choices=("frozen", "finetune"), required=True)
    p.add_argument("--init-checkpoint", type=Path)
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
