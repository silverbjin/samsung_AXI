"""SmartDish C single-shot read-only Owner diagnostics. No Test, training or downloads."""
import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
from pathlib import Path

P0_SHA="56951cab0e6f69f99d71b249cac53c555add5e2322d4b1febc04f369cfd3f3f0"
P1_SHA="8143ecc11a5b1a81cbbc6ca65d714eccd66b617e05467768478d7b16b59b1582"
P2_SHA="945f8f4aeb3b8a8e9cb1873f4353620dbd660765b3eb9688ab234a61f97a3864"
PLAN_SHA="9e3eb03172940ef04bdc016051e4dca2905a640bd658e1e919dd9ba70fc33019"
CKPT_SHA="6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
WEIGHT_SHA="f37072fd47e89c5e827621c5baffa7500819f7896bbacec160b1a16c560e07ec"
VERSION="c4c429b33faf22d904db9ddf2b7aa6e27ade12d70c7ecd407dff7c5cb9422606"

class DiagnosticHold(Exception):
    pass

def require(ok,code):
    if not ok: raise DiagnosticHold(code)

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def verify_receipts(p0,p1,p2):
    require(p0.get("verdict")=="CONTRACT_READY_HUMAN_REVIEW_REQUIRED"
        and p0.get("files_independently_hashed")==42
        and p0.get("dataset_version")==VERSION,
        "C_V1_DOCTOR_P0_CONTRACT_MISMATCH")
    require(p1.get("verdict")=="P1_WEIGHT_BYTES_READY_C_APPROVAL_REQUIRED"
        and p1.get("owner_p0_report_sha256")==P0_SHA
        and p1.get("p1_plan_sha256")==PLAN_SHA
        and p1.get("pretrained_weights_sha256")==WEIGHT_SHA
        and p1.get("training_executed") is False
        and p1.get("test_opened") is False,
        "C_V1_DOCTOR_P1_CONTRACT_MISMATCH")
    require(p2.get("verdict")=="P2_FROZEN_TRAINED_AWAIT_C_REVIEW"
        and p2.get("P1_plan_sha256")==PLAN_SHA
        and p2.get("checkpoint_sha256")==CKPT_SHA
        and p2.get("pretrained_weight_sha256")==WEIGHT_SHA
        and p2.get("selected_epoch")==3
        and p2.get("data_scope")=="PHYSICS_OBSERVED"
        and p2.get("test_used_for_training") is False
        and p2.get("test_evaluated") is False
        and p2.get("C_RESEARCH_PILOT_ACCEPTED") is False
        and p2.get("E_AI_ON")=="HOLD"
        and p2.get("AI_OFF")=="PROTECTED"
        and p2.get("A19")=="NOT_AUTHORIZED"
        and p2.get("production_contact")=="HOLD",
        "C_V1_DOCTOR_P2_CONTRACT_MISMATCH")

def verify_environment(env):
    require(env.get("venv_isolated") is True
        and env.get("python_version")=="3.12.3"
        and env.get("torch")=="2.5.1+cpu"
        and env.get("torchvision")=="0.20.1+cpu"
        and env.get("Pillow")=="10.2.0"
        and env.get("cuda_build") is False
        and env.get("wsl2") is True,
        "C_V1_DOCTOR_CPU_VENV_DRIFT")

def inspect(p0,p1,p2,plan,ckpt,venv):
    require(venv.is_dir() and (venv/".smartdish_c_v1_environment.json").is_file(),
            "C_V1_DOCTOR_VENV_MISSING")
    require(sys.prefix!=sys.base_prefix and Path(sys.prefix).resolve()==venv.resolve(),
            "C_V1_DOCTOR_VENV_NOT_ACTIVE")
    for name,path,expected in (
        ("P0",p0,P0_SHA),("P1",p1,P1_SHA),("P2",p2,P2_SHA),
        ("PLAN",plan,PLAN_SHA),("CHECKPOINT",ckpt,CKPT_SHA)):
        require(path.is_file() and not path.is_symlink(),
                "C_V1_DOCTOR_"+name+"_MISSING_OR_SYMLINK")
        require(digest(path)==expected,"C_V1_DOCTOR_"+name+"_SHA_MISMATCH")
    verify_receipts(json.loads(p0.read_text()),json.loads(p1.read_text()),
                    json.loads(p2.read_text()))
    plan_json=json.loads(plan.read_text())
    require(plan_json.get("data",{}).get("version")==VERSION
        and plan_json.get("operational_inference",{}).get("confidence_min")==.8
        and plan_json.get("policy",{}).get("AI_OFF")=="PROTECTED",
        "C_V1_DOCTOR_PLAN_CHANGED")
    import torch,torchvision,PIL
    kernel=platform.release().lower()
    env={"venv_isolated":True,"python_version":platform.python_version(),
         "torch":torch.__version__,"torchvision":torchvision.__version__,
         "Pillow":PIL.__version__,"cuda_build":torch.version.cuda is not None,
         "wsl2":"microsoft" in kernel and "wsl" in kernel}
    verify_environment(env)
    require(os.environ.get("TORCH_HOME")==str(Path.home()/".cache/smartdish-c-v1/torch"),
            "C_V1_DOCTOR_TORCH_CACHE_CHANGED")
    weight_path=Path(torch.hub.get_dir())/"checkpoints"/"resnet18-f37072fd.pth"
    require(weight_path.is_file() and not weight_path.is_symlink()
            and weight_path.stat().st_size==46830571,
            "C_V1_DOCTOR_WEIGHT_CACHE_MISSING")
    return {
        "verdict":"C_V1_OWNER_ENV_AND_RECEIPT_PASS_PREVIOUS_EVIDENCE_REUSED",
        "python":env,"available_disk_bytes":shutil.disk_usage(venv).free,
        "p0_report_sha256":P0_SHA,"p1_report_sha256":P1_SHA,
        "p2_summary_sha256":P2_SHA,"P1_plan_sha256":PLAN_SHA,
        "checkpoint_sha256":CKPT_SHA,
        "pretrained_weights_sha256":"PREVIOUS_P1_REPORT_REUSED_NOT_REHASHED",
        "P0_42_REEXECUTED":False,"P1_REEXECUTED":False,"P2_RETRAINED":False,
        "P3_test_opened":False,"P3_test_authorized":False,
        "model_performance_status":"HOLD_BELOW_VALIDATION_MAJORITY_BASELINE",
        "AI_OFF":"PROTECTED","production_contact":"HOLD","A19":"NOT_AUTHORIZED"
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("p0-report","p1-report","p2-summary","experiment-lock",
                 "checkpoint","venv","report"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args()
    result={"verdict":"HOLD","P3_test_opened":False,"P3_test_authorized":False,
            "P2_RETRAINED":False,"AI_OFF":"PROTECTED",
            "production_contact":"HOLD","A19":"NOT_AUTHORIZED"}
    try:
        result.update(inspect(a.p0_report,a.p1_report,a.p2_summary,
                              a.experiment_lock,a.checkpoint,a.venv))
    except (DiagnosticHold,OSError,ValueError,ImportError) as exc:
        result["reason"]=str(exc).split(" ")[0]
    a.report.parent.mkdir(parents=True,exist_ok=True)
    a.report.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("C_V1_OWNER_DOCTOR "+json.dumps(result,sort_keys=True))
    return 0 if result["verdict"].startswith("C_V1_OWNER_ENV_AND_RECEIPT_PASS") else 2

if __name__=="__main__":
    raise SystemExit(main())
