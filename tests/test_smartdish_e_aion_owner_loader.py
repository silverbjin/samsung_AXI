"""V1 model exact-sha owner Gazebo scope; no private model, no torch import."""
import sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src/smartdish_ai"))
from smartdish_ai import model_runtime as m

def metadata():
    return dict(architecture="resnet18_single_rgb",labels=["STABLE","UNSTABLE"],
        image_size=224,mean=list(m.MEAN),std=list(m.STD),phase="frozen",
        weight_init="PRETRAINED_OR_FINETUNED",data_scope="PHYSICS_OBSERVED",
        research_release_status="UNREVIEWED_NOT_FOR_PRODUCT",
        research_dataset_version=m.OWNER_B_DATASET_V1_SHA256,
        split_manifest_sha256=m.OWNER_B_V1_SPLIT_MANIFEST_SHA256,
        P1_plan_sha256=m.OWNER_C_P1_PLAN_SHA256,
        model_state_dict={"fixture":None})

def test_default_C17_product_gate_stays_closed():
    assert m.PRODUCT_APPROVED_CHECKPOINT_SHA256 is None
    with pytest.raises(PermissionError,match="C_PRODUCT_MODEL_NOT_APPROVED"):
        m.require_product_model_release(m.OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256)

def test_exact_owner_scope_sha_or_block():
    m.require_owner_gazebo_integration_release(m.OWNER_GAZEBO_INTEGRATION_CHECKPOINT_SHA256)
    for bad in ("0"*64,"junk","",None):
        with pytest.raises(PermissionError,match="C_OWNER_INTEGRATION_CHECKPOINT_SHA_MISMATCH"):
            m.require_owner_gazebo_integration_release(bad)

def test_exact_research_p2_metadata_or_block():
    m.validate_owner_gazebo_integration_metadata(metadata())
    for key,value in (
        ("research_release_status","C_RESEARCH_PILOT_ACCEPTED"),
        ("data_scope","MOCK_ONLY"),("phase","finetune"),
        ("research_dataset_version","wrong"),("split_manifest_sha256","wrong"),
        ("P1_plan_sha256","wrong"),("model_state_dict",None)):
        v=metadata();v[key]=value
        with pytest.raises(ValueError,match="C_OWNER_INTEGRATION_METADATA_MISMATCH"):
            m.validate_owner_gazebo_integration_metadata(v)

def test_fake_weights_rejected_before_torch_import(tmp_path):
    f=tmp_path/"fake.pt";f.write_bytes(b"NO REAL WEIGHTS")
    with pytest.raises(PermissionError,match="C_OWNER_INTEGRATION_CHECKPOINT_SHA_MISMATCH"):
        m.load_predictor(f,owner_gazebo_integration=True)
    with pytest.raises(PermissionError,match="C_PRODUCT_MODEL_NOT_APPROVED"):
        m.load_predictor(f)
