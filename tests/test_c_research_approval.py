"""Negative-only, no private data, no pretrained model download."""
import json
from pathlib import Path
import pytest
from ai.train.research_approval import approve_training
from ai.train.dataset_v1_gate import IntakeHold


def test_missing_approval_blocks_real_training(tmp_path):
    with pytest.raises(IntakeHold,match="C_V1_C_RESEARCH_APPROVAL_REQUIRED"):
        approve_training(tmp_path,tmp_path/"split.csv",None,tmp_path/"p1.json",phase="frozen")


def test_missing_plan_blocks_even_with_approval(tmp_path):
    p=tmp_path/"approval.json";p.write_text("{}")
    with pytest.raises(IntakeHold,match="C_V1_P1_PLAN_MISSING"):
        approve_training(tmp_path,tmp_path/"split.csv",p,tmp_path/"p1.json",phase="frozen")


def test_p1_mismatch_blocks_before_private_data(tmp_path):
    p=tmp_path/"approval.json";p.write_text("{}")
    plan=tmp_path/"p1.json";plan.write_text('{"status":"DUMMY"}')
    with pytest.raises(IntakeHold,match="C_V1_P1_PLAN_CONTRACT_INVALID"):
        approve_training(tmp_path,tmp_path/"split.csv",p,plan,phase="frozen")
