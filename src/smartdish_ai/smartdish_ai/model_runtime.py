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


def validate_research_checkpoint_metadata(ckpt):
    """Reject unreviewed/training-only weights even when a path is supplied."""
    validate_research_checkpoint_metadata(ckpt)
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
