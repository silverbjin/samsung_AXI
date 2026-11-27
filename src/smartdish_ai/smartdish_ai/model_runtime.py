"""Self-contained installed ROS runtime for training-compatible ResNet18 checkpoints.

The training evaluator uses the same size / labels / ImageNet normalization.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import hmac

LABELS = ("STABLE", "UNSTABLE")
IMAGE_SIZE = 224
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)

# C17: product models MUST be admitted by a separately reviewed E release.
# Never fill this with an unaccepted C P2/P3 research checkpoint digest.
# This value is intentionally None for the accepted AI OFF S7 release.
PRODUCT_APPROVED_CHECKPOINT_SHA256 = None

# Owner-authorized internal Gazebo integration ONLY. Not a product quality PASS.
OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256 = "6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
OWNER_B_DATASET_V1_SHA256 = "c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606"
OWNER_B_V1_SPLIT_MANIFEST_SHA256 = "8a530b6a34788300bb507ea10aafd10a7ab5616a0c0ffc0f87b7ccf79d0db6d5"
OWNER_C_P1_PLAN_SHA256 = "9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019"


def require_product_model_release(checkpoint_sha256: str) -> None:
    """Require independent E product authorization in code, not self-claimed .pt metadata.

    The non-empty 64-digit digest can only be changed in a separately
    reviewed/approved product release; environment variables and model
    metadata cannot enable AI ON on their own.
    """
    pin = PRODUCT_APPROVED_CHECKPOINT_SHA256
    if (not isinstance(pin, str) or len(pin) != 64
            or any(c not in "0123456789abcdef" for c in pin)
            or not isinstance(checkpoint_sha256, str)
            or len(checkpoint_sha256) != 64
            or not hmac.compare_digest(checkpoint_sha256, pin)):
        raise PermissionError("C_PRODUCT_MODEL_NOT_APPROVED")


def require_owner_gazebo_integration_release(checkpoint_sha256: str) -> None:
    """Restrict experiment to one Owner-approved private checkpoint SHA."""
    if (not isinstance(checkpoint_sha256, str)
            or not hmac.compare_digest(
                checkpoint_sha256, OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256)):
        raise PermissionError("C_OWNER_INTEGRATION_CHECKPOINT_SHA_MISMATCH")


def validate_owner_gazebo_integration_metadata(ckpt: dict) -> None:
    """Real v1 P2 trainer metadata; do not fabricate research acceptance."""
    if (not isinstance(ckpt, dict)
            or ckpt.get("architecture") != "resnet18_single_rgb"
            or ckpt.get("labels") != list(LABELS)
            or ckpt.get("image_size") != IMAGE_SIZE
            or tuple(ckpt.get("mean", ())) != MEAN
            or tuple(ckpt.get("std", ())) != STD
            or ckpt.get("phase") != "frozen"
            or ckpt.get("weight_init") != "PRETRAINED_OR_FINETUNED"
            or ckpt.get("data_scope") != "PHYSICS_OBSERVED"
            or ckpt.get("research_release_status") != "UNREVIEWED_NOT_FOR_PRODUCT"
            or ckpt.get("research_dataset_version") != OWNER_B_DATASET_V1_SHA256
            or ckpt.get("split_manifest_sha256") != OWNER_B_V1_SPLIT_MANIFEST_SHA256
            or ckpt.get("P1_plan_sha256") != OWNER_C_P1_PLAN_SHA256
            or not isinstance(ckpt.get("model_state_dict"), dict)):
        raise ValueError("C_OWNER_INTEGRATION_METADATA_MISMATCH")


def validate_research_checkpoint_metadata(ckpt: dict) -> None:
    """Even E allowlisted files must have C human-accepted research provenance."""
    if (not isinstance(ckpt, dict)
            or ckpt.get("architecture") != "resnet18_single_rgb"
            or ckpt.get("labels") != list(LABELS)
            or ckpt.get("image_size") != IMAGE_SIZE
            or tuple(ckpt.get("mean", ())) != MEAN
            or tuple(ckpt.get("std", ())) != STD
            or ckpt.get("data_scope") != "PHYSICS_OBSERVED"
            or ckpt.get("research_release_status") != "C_RESEARCH_PILOT_ACCEPTED"
            or ckpt.get("research_usage_rights") != "PROJECT_RESEARCH_ONLY_NO_PUBLIC_REDISTRIBUTION"
            or ckpt.get("E_AI_ON_approved") is not False
            or ckpt.get("production_contact") != "HOLD"):
        raise ValueError("C_MODEL_CONTRACT_MISMATCH")


def load_predictor(model_path: Path, *, owner_gazebo_integration: bool = False):
    """Default C17 production deny; exact-SHA alternative for Owner Gazebo only."""
    if not model_path.is_file():
        raise FileNotFoundError("C_MODEL_WEIGHTS_MISSING")
    # Reject non-E-approved bytes *before* loading torch, deserializing or
    # constructing the inference model. Metadata inside the file is untrusted.
    data = model_path.read_bytes()
    checkpoint_sha256 = hashlib.sha256(data).hexdigest()
    if owner_gazebo_integration is True:
        require_owner_gazebo_integration_release(checkpoint_sha256)
    else:
        require_product_model_release(checkpoint_sha256)

    from io import BytesIO
    import torch
    import torch.nn as nn
    from PIL import Image, ImageOps
    import torchvision.transforms.functional as F
    from torchvision.models import resnet18

    ckpt = torch.load(BytesIO(data), map_location="cpu", weights_only=True)
    if owner_gazebo_integration is True:
        validate_owner_gazebo_integration_metadata(ckpt)
    else:
        validate_research_checkpoint_metadata(ckpt)
    model = resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, 2)
    model.load_state_dict(ckpt["model_state_dict"], strict=True)
    model.eval()
    version = "resnet18-" + checkpoint_sha256[:12]

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
