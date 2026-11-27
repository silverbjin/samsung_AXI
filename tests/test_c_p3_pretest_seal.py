"""Fixture-only P3 pretest negatives. No torch needed, no Test access."""
from types import SimpleNamespace
import pytest
from ai.train.p3_pretest_seal import check_summary,check_metadata,CHECKPOINT_SHA,PLAN_SHA,WEIGHT_SHA
from ai.train.dataset_v1_gate import VERSION,SPLIT_SHA,IntakeHold

def fixture():
    epochs=[{"epoch":i,"train":{"samples":11},
             "val":{"samples":3,"loss":v}} for i,v in [(1,.8243),(2,.7779),(3,.7452)]]
    summary=dict(verdict="P2_FROZEN_TRAINED_AWAIT_C_REVIEW",
        checkpoint_sha256=CHECKPOINT_SHA,P1_plan_sha256=PLAN_SHA,
        pretrained_weight_sha256=WEIGHT_SHA,phase="frozen",seed=42,
        data_scope="PHYSICS_OBSERVED",selected_epoch=3,epochs=epochs,
        best_val_loss=.7452,
        split_counts={"train":{"STABLE":8,"UNSTABLE":3},
                      "val":{"STABLE":2,"UNSTABLE":1},"test":{}},
        test_evaluated=False,test_used_for_training=False,
        C_RESEARCH_PILOT_ACCEPTED=False,checkpoint_distribution_authorized=False,
        AI_OFF="PROTECTED",production_contact="HOLD",
        A19="NOT_AUTHORIZED",E_AI_ON="HOLD")
    plan={"data":{"version":VERSION,"split_sha256":SPLIT_SHA},
          "execution":{"max_test_evaluations":1},
          "operational_inference":{"confidence_min":.8}}
    ckpt=dict(architecture="resnet18_single_rgb",
        labels=["STABLE","UNSTABLE"],image_size=224,
        mean=[.485,.456,.406],std=[.229,.224,.225],
        data_scope="PHYSICS_OBSERVED",phase="frozen",
        weight_init="PRETRAINED_OR_FINETUNED",
        split_manifest_sha256=SPLIT_SHA,
        research_dataset_version=VERSION,P1_plan_sha256=PLAN_SHA,
        research_release_status="UNREVIEWED_NOT_FOR_PRODUCT",
        model_state_dict={"fc.weight":SimpleNamespace(shape=(2,512)),
                          "fc.bias":SimpleNamespace(shape=(2,))})
    return summary,plan,ckpt

def test_fixture_contract_pass_but_no_test_authorization():
    s,p,c=fixture()
    check_summary(s,p)
    check_metadata(c)

@pytest.mark.parametrize(("name","value"),[
    ("test_evaluated",True),("test_used_for_training",True),
    ("selected_epoch",2),("checkpoint_distribution_authorized",True),
    ("AI_OFF","DISABLED"),("A19","AUTHORIZED"),
    ("E_AI_ON","PASS"),("checkpoint_sha256","0"*64),
    ("best_val_loss",.01)])
def test_summary_tampering_denied(name,value):
    s,p,c=fixture();s[name]=value
    with pytest.raises(IntakeHold):check_summary(s,p)

@pytest.mark.parametrize(("name","value"),[
    ("phase","finetune"),("data_scope","MOCK_ONLY"),
    ("research_release_status","C_RESEARCH_PILOT_ACCEPTED"),
    ("labels",["UNSTABLE","STABLE"]),
    ("split_manifest_sha256","0"*64)])
def test_checkpoint_contract_denied(name,value):
    s,p,c=fixture();c[name]=value
    with pytest.raises(IntakeHold):check_metadata(c)

def test_head_shape_denied():
    s,p,c=fixture()
    c["model_state_dict"]["fc.weight"]=SimpleNamespace(shape=(3,512))
    with pytest.raises(IntakeHold,match="C_V1_P3_CHECKPOINT_FC_SHAPE_CHANGED"):
        check_metadata(c)

def test_test_threshold_cannot_be_modified():
    s,p,c=fixture();p["operational_inference"]["confidence_min"]=.65
    with pytest.raises(IntakeHold):check_summary(s,p)
