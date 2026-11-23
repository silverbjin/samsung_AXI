"""ResNet18 single-view tray RGB classifier, isolated from legacy S6 classifier."""
from __future__ import annotations

import hashlib
from pathlib import Path

LABELS = ("STABLE", "UNSTABLE")  # B's label_map: STABLE=0, UNSTABLE=1
IMAGE_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)


def preprocess(image):
    """B's EXIF/RGB/fit order followed by ImageNet normalization."""
    from PIL import Image, ImageOps
    import torchvision.transforms.functional as F

    image = ImageOps.exif_transpose(image).convert("RGB")
    image = ImageOps.fit(image, (IMAGE_SIZE, IMAGE_SIZE), method=Image.Resampling.BILINEAR)
    return F.normalize(F.to_tensor(image), MEAN, STD)


def new_resnet18(*, pretrained: bool):
    import torch.nn as nn
    from torchvision.models import ResNet18_Weights, resnet18

    # No silent random-weight fallback: no internet/cache => explicit exception.
    model = resnet18(weights=ResNet18_Weights.DEFAULT if pretrained else None)
    model.fc = nn.Linear(model.fc.in_features, len(LABELS))
    return model


def load_checkpoint(path: Path, device: str = "cpu", *, allow_mock: bool = False):
    import torch

    if not path.is_file():
        raise FileNotFoundError("C_MODEL_WEIGHTS_MISSING")
    checkpoint = torch.load(path, map_location=device, weights_only=True)
    if (checkpoint.get("architecture") != "resnet18_single_rgb" or
            checkpoint.get("labels") != list(LABELS) or
            checkpoint.get("image_size") != IMAGE_SIZE or
            tuple(checkpoint.get("mean", [])) != MEAN or
            tuple(checkpoint.get("std", [])) != STD or
            checkpoint.get("data_scope") != ("MOCK_ONLY" if allow_mock else "PHYSICS_OBSERVED")):
        raise ValueError("C_MODEL_CONTRACT_MISMATCH")
    model = new_resnet18(pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    model.to(device).eval()
    return model, "resnet18-" + hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def predict_pil(model, image, device: str = "cpu") -> tuple[str, float]:
    import torch

    x = preprocess(image).unsqueeze(0).to(device)
    with torch.inference_mode():
        probabilities = torch.softmax(model(x), dim=1)[0]
    score, index = probabilities.max(dim=0)
    return LABELS[int(index)], float(score)
