"""Self-contained installed ROS runtime for training-compatible ResNet18 checkpoints.

The training evaluator uses the same size / labels / ImageNet normalization.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

LABELS = ("STABLE", "UNSTABLE")
IMAGE_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def load_predictor(model_path: Path):
    """Load only a real, validated checkpoint; returns (predictor, version)."""
    from io import BytesIO
    import torch
    import torch.nn as nn
    from PIL import Image, ImageOps
    import torchvision.transforms.functional as F
    from torchvision.models import resnet18

    if not model_path.is_file():
        raise FileNotFoundError("C_MODEL_WEIGHTS_MISSING")
    data = model_path.read_bytes()
    ckpt = torch.load(BytesIO(data), map_location="cpu", weights_only=True)
    if (ckpt.get("architecture") != "resnet18_single_rgb" or
            ckpt.get("labels") != list(LABELS) or
            ckpt.get("image_size") != IMAGE_SIZE or
            tuple(ckpt.get("mean", [])) != MEAN or
            tuple(ckpt.get("std", [])) != STD or
            ckpt.get("data_scope") != "PHYSICS_OBSERVED" or
            ckpt.get("research_release_status") != "C_RESEARCH_PILOT_ACCEPTED" or
            ckpt.get("research_dataset_version") !=
                "c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606"):
        raise ValueError("C_MODEL_CONTRACT_MISMATCH")
    model = resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.eval()
    version = "resnet18-" + hashlib.sha256(data).hexdigest()[:12]

    def predict(rgb: bytes, width: int, height: int):
        image = Image.frombytes("RGB", (width, height), rgb)
        image = ImageOps.fit(ImageOps.exif_transpose(image).convert("RGB"),
                             (IMAGE_SIZE, IMAGE_SIZE), method=Image.Resampling.BILINEAR)
        tensor = F.normalize(F.to_tensor(image), MEAN, STD).unsqueeze(0)
        with torch.inference_mode():
            scores = torch.softmax(model(tensor), dim=1)[0]
        confidence, idx = scores.max(dim=0)
        return LABELS[int(idx)], float(confidence)

    return predict, version
