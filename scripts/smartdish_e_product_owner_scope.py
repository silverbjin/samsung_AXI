"""Explicit WSL2 Owner-only scope; never emulate CI or authorize general product model."""
import os,re,subprocess,sys
from pathlib import Path
CI_L2_PIN="28dd5150b96ae842bebab1cd2ee1a3ce78cc4a33"
MODEL_SHA="6afdcfe526e6dfd7e19e934e9af405d13d2fc4f4f940291ec0ff97cfadd6ab7c"
MODEL_VERSION="resnet18-"+MODEL_SHA[:12]
OWNER_VERDICT="E_OWNER_WSL2_PRODUCT_L3_CANDIDATE"
OWNER_SCOPE="ACTUAL_E_SINGLE_WORLD_OWNER_PRIVATE_MODEL"
MODEL_SCOPE="OWNER_ACTUAL_PRIVATE_MODEL"

def check_identity(env,kernel,tty,pin,run_id):
    if (env.get("CI","").lower()=="true" or env.get("GITHUB_ACTIONS") or
        not env.get("WSL_DISTRO_NAME") or "microsoft" not in kernel.lower() or not tty or not env.get("DISPLAY")):
        raise RuntimeError("E_OWNER_WSL2_TTY_GUI_REQUIRED")
    if (not re.fullmatch("[0-9a-f]{40}",pin) or not re.fullmatch("[0-9]{8}T[0-9]{6}Z-[0-9]+",run_id) or
        env.get("SMARTDISH_E_OWNER_PRODUCT_RUN")!=run_id or env.get("SMARTDISH_E_SOURCE_SHA")!=pin or
        env.get("GZ_PARTITION")!="smartdish_a04_owner_"+run_id or env.get("SMARTDISH_E_OWNER_CONSENT")!="YES-E-PRODUCT-GO"):
        raise RuntimeError("E_OWNER_SESSION_IDENTITY")
    if not re.fullmatch("[0-9]+",env.get("ROS_DOMAIN_ID","")):
        raise RuntimeError("E_OWNER_DOMAIN_REQUIRED")

def require_owner(pin,run_id):
    check_identity(os.environ,Path("/proc/sys/kernel/osrelease").read_text(),os.isatty(0),pin,run_id)
    if Path(sys.executable).resolve()!=Path("/usr/bin/python3").resolve():
        raise RuntimeError("E_OWNER_ROS_PYTHON_REQUIRED")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True,timeout=10).strip()
    if actual!=pin or subprocess.check_output(["git","status","--porcelain","--untracked-files=no"],text=True,timeout=10).strip():
        raise RuntimeError("E_OWNER_SOURCE_PIN_DRIFT")
    if subprocess.run(["git","merge-base","--is-ancestor",CI_L2_PIN,pin],timeout=10).returncode:
        raise RuntimeError("E_OWNER_L2_ANCESTRY_REQUIRED")
    return True

def model_receipt(d):
    return (d.get("scope")==MODEL_SCOPE and d.get("private_model_loaded") is True and
            d.get("checkpoint_sha256")==MODEL_SHA and d.get("model_version")==MODEL_VERSION and
            d.get("test4_opened") is False and d.get("general_product_approved") is False)

def owner_request(d):
    return (d.get("schema_version")==2 and d.get("profile")=="OWNER_PRODUCT_RECOVERY" and
            d.get("table_id")=="T03" and d.get("ai_enabled") is True and
            type(d.get("table_wait_s")) is int and d["table_wait_s"]==10 and
            type(d.get("dropoff_wait_s")) is int and d["dropoff_wait_s"]==5)

C_VERSIONS={"torch":"2.5.1+cpu","torchvision":"0.20.1+cpu","numpy":"1.26.4","PIL":"10.2.0"}
def loaded_receipt(d):
    return (model_receipt(d) and d.get("versions")==C_VERSIONS and d.get("bytes")==44786668 and
            isinstance(d.get("installed_module_hashes"),dict) and
            set(d["installed_module_hashes"])=={"model_runtime","product_stability_inference_node","product_inference"} and
            all(isinstance(x,str) and re.fullmatch("[0-9a-f]{64}",x) for x in d["installed_module_hashes"].values()))
