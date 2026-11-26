"""P4 runtime contract-only tests; no torch or image files needed."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/smartdish_ai'))
runtime=pytest.importorskip("smartdish_ai.model_runtime",reason="C full repo runtime available in GitHub CI")
validate_research_checkpoint_metadata,V1=runtime.validate_research_checkpoint_metadata,runtime.V1


def accepted_fake_metadata():
    return {"architecture":"resnet18_single_rgb", "labels":["STABLE","UNSTABLE"],
      "image_size":224,"mean":[.485,.456,.406],"std":[.229,.224,.225],
      "data_scope":"PHYSICS_OBSERVED", "research_release_status":"C_RESEARCH_PILOT_ACCEPTED",
      "research_dataset_version":V1,"E_AI_ON_approved":False,
      "production_contact":"HOLD",
      "research_usage_rights":"PROJECT_RESEARCH_ONLY_NO_PUBLIC_REDISTRIBUTION"}


def test_unreviewed_real_checkpoint_is_denied():
    c=accepted_fake_metadata();c["research_release_status"]="UNREVIEWED_NOT_FOR_PRODUCT"
    with pytest.raises(ValueError,match="C_MODEL_CONTRACT_MISMATCH"):
        validate_research_checkpoint_metadata(c)


def test_mock_or_ai_on_production_confusion_denied():
    for key,value in [("data_scope","MOCK_ONLY"),("E_AI_ON_approved",True),
                      ("production_contact","PASS"),
                      ("research_usage_rights","PUBLIC")]:
        c=accepted_fake_metadata();c[key]=value
        with pytest.raises(ValueError,match="C_MODEL_CONTRACT_MISMATCH"):
            validate_research_checkpoint_metadata(c)


def test_narrow_research_checkpoint_metadata_is_allowed_but_not_e_product():
    validate_research_checkpoint_metadata(accepted_fake_metadata())
