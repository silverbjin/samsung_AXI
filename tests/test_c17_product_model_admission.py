"""C17: external E product approval must gate C model load; no real checkpoints."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "smartdish_ai"))
from smartdish_ai import model_runtime
from smartdish_ai.inference_core import InferenceCore


def test_e_release_gate_exists_and_default_is_not_authorized():
    guard = getattr(model_runtime, "require_product_model_release", None)
    assert callable(guard), "C17_E_PRODUCT_RELEASE_GUARD_MISSING"
    assert getattr(model_runtime, "PRODUCT_APPROVED_CHECKPOINT_SHA256", "missing") is None
    with pytest.raises(PermissionError, match="C_PRODUCT_MODEL_NOT_APPROVED"):
        guard("6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c")


@pytest.mark.parametrize("checksum", ["", "not-sha", "0"*64, "F"*64])
def test_arbitrary_checkpoint_not_authorized(checksum):
    with pytest.raises(PermissionError, match="C_PRODUCT_MODEL_NOT_APPROVED"):
        model_runtime.require_product_model_release(checksum)


def test_p2_checkpoint_file_rejected_before_torch_or_image_load(tmp_path):
    raw = tmp_path / "c_v1_frozen_head.pt"
    raw.write_bytes(b"pretend-p2-checkpoint-with-self-approval")
    with pytest.raises(PermissionError, match="C_PRODUCT_MODEL_NOT_APPROVED"):
        model_runtime.load_predictor(raw)


def test_absent_model_stays_unknown_with_same_request_and_capture():
    core = InferenceCore(None, model_version="forged-approved", confidence_min=.8)
    core.cache_rgb(b"\x01\x02\x03" * 256, 16, 16, received_at=10)
    output = core.handle_request('{"request_id":"C17-1","capture_id":"FRAME-1"}', now=11)
    assert output == {
        "request_id":"C17-1","capture_id":"FRAME-1",
        "status":"UNKNOWN","confidence":None,"model_version":"none"}
    assert core.handle_request('{"request_id":"C17-1","capture_id":"FRAME-1"}', now=11) is None
