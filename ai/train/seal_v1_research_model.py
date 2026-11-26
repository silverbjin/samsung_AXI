#!/usr/bin/env python3
"""P4 research-only checkpoint handoff; requires explicit human review after Test.

This utility never claims safety certification or E AI ON product acceptance.
Only private Owner may execute after P0/P1/P2/P3; public CI never uses it.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from ai.train.dataset_v1_gate import VERSION, IntakeHold, require, sha_file


def seal(checkpoint:Path, test_report:Path, approval_file:Path, output:Path, report:Path):
    require(all(p.is_file() for p in (checkpoint,test_report,approval_file)),
            "C_V1_P4_INPUT_MISSING")
    require(not output.exists() and not report.exists(),
            "C_V1_P4_ARTIFACT_ALREADY_EXISTS")
    approval=json.loads(approval_file.read_text(encoding="utf-8"))
    require(approval.get("decision")=="C_RESEARCH_PILOT_ACCEPTED" and
            approval.get("checkpoint_sha256")==sha_file(checkpoint) and
            approval.get("single_test_report_sha256")==sha_file(test_report) and
            approval.get("dataset_version")==VERSION and
            approval.get("scope")=="FIXED_WORLD_Y_TORQUE_CONDITIONAL_STATIC_CYLINDER_RGB_T0_ONLY" and
            approval.get("production_contact")=="HOLD" and
            approval.get("AI_OFF")=="PROTECTED" and
            approval.get("E_AI_ON_approved") is False and
            isinstance(approval.get("reviewer"),str) and bool(approval["reviewer"].strip()),
            "C_V1_P4_HUMAN_RESEARCH_APPROVAL_REQUIRED")
    outcome=json.loads(test_report.read_text(encoding="utf-8"))
    require(outcome.get("evaluation_scope")=="INDEPENDENT_B_TEST" and
            outcome.get("pilot_risk_metrics",{}).get("sample_count")==4 and
            outcome.get("test_seal",{}).get("checkpoint_sha256")==sha_file(checkpoint),
            "C_V1_P4_SINGLE_TEST_REPORT_INVALID")
    import torch
    ckpt=torch.load(checkpoint,weights_only=True,map_location="cpu")
    require(ckpt.get("data_scope")=="PHYSICS_OBSERVED" and
            ckpt.get("research_dataset_version")==VERSION and
            ckpt.get("research_release_status")=="UNREVIEWED_NOT_FOR_PRODUCT" and
            ckpt.get("phase")=="frozen",
            "C_V1_P4_TRAINING_CHECKPOINT_INVALID")
    ckpt["research_release_status"]="C_RESEARCH_PILOT_ACCEPTED"
    ckpt["single_test_report_sha256"]=sha_file(test_report)
    ckpt["research_usage_rights"]="PROJECT_RESEARCH_ONLY_NO_PUBLIC_REDISTRIBUTION"
    ckpt["production_contact"]="HOLD"
    ckpt["E_AI_ON_approved"]=False
    output.parent.mkdir(parents=True,exist_ok=True)
    torch.save(ckpt,output)
    result={"status":"C_RESEARCH_PILOT_ACCEPTED",
            "research_only":True,"production_contact":"HOLD",
            "E_AI_ON_approved":False,"AI_OFF":"PROTECTED",
            "dataset_version":VERSION,
            "source_checkpoint_sha256":sha_file(checkpoint),
            "test_report_sha256":sha_file(test_report),
            "research_checkpoint_sha256":sha_file(output)}
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("checkpoint","test-report","approval","out","report"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    print("C_V1_P4_RESEARCH_SEAL "+json.dumps(seal(a.checkpoint,a.test_report,
                                                    a.approval,a.out,a.report)))


if __name__=="__main__":main()
