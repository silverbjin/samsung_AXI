#!/usr/bin/env bash
# Explicit one-shot installer for isolated SmartDish C Dataset v1 CPU environment.
# No ROS/system-site pip, no training, no B audit, no Test or Gazebo.
set -Eeuo pipefail
umask 077

if [[ "$#" == 1 && "$1" == "--help" ]]; then
  echo "Usage: SMARTDISH_C_PIN=<40-hex-C-SHA> bash installer.sh [--with-weights]"
  echo "Default: isolated CPU torch/vision/Pillow install only."
  echo "--with-weights: explicit official ImageNet ResNet18 V1 cache download & SHA check; NOT training approval."
  exit 0
fi
if [[ "$#" -gt 1 ]] || { [[ "$#" == 1 ]] && [[ "$1" != "--with-weights" ]]; }; then
  echo C_V1_INSTALL_BAD_ARGUMENT >&2; exit 2
fi
WEIGHTS=0
if [[ "$#" == 1 ]]; then WEIGHTS=1; fi
PIN="$(printenv SMARTDISH_C_PIN || true)"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo C_V1_INSTALL_IMMUTABLE_PIN_REQUIRED >&2; exit 2; }
PY=/usr/bin/python3
[[ -x "$PY" ]] || { echo C_V1_SYSTEM_PYTHON_NOT_FOUND >&2; exit 2; }
"$PY" -c 'import sys; assert sys.version_info[:2] == (3,12), "C_V1_PYTHON_312_REQUIRED"' ||
  { echo C_V1_PYTHON_312_REQUIRED >&2; exit 2; }
VENV="$HOME/.venvs/smartdish-c-v1-py312-cpu"
TORCH_CACHE="$HOME/.cache/smartdish-c-v1/torch"
EVIDENCE="$HOME/smartdish_c_v1_venv_install_evidence"
mkdir -p "$HOME/.venvs" "$EVIDENCE"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$EVIDENCE/$STAMP"
mkdir -p "$OUT"
finish() {
  rc="$?"
  trap - EXIT
  printf 'C_V1_INSTALL_EXIT_CODE=%s\nC_V1_INSTALL_PIN=%s\n' "$rc" "$PIN" > "$OUT/status.txt"
  tar -C "$OUT" --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -czf "$OUT.tar.gz" .
  sha256sum "$OUT.tar.gz" > "$OUT.tar.gz.sha256"
  echo "C_V1_INSTALL_RESULT exit_code=$rc archive=$OUT.tar.gz sidecar=$OUT.tar.gz.sha256"
  exit "$rc"
}
trap finish EXIT
command -v flock >/dev/null || { echo C_V1_FLOCK_REQUIRED >&2; exit 2; }
exec 9>"$HOME/.venvs/.smartdish-c-v1.install.lock"
flock -n 9 || { echo C_V1_INSTALL_ALREADY_RUNNING >&2; exit 2; }
# A separate path and explicit marker ensure another developer's venv is never overwritten.
if [[ -e "$VENV" && ! -f "$VENV/.smartdish_c_v1_environment.json" &&
      ! -f "$VENV/.smartdish_c_v1_install_pending" ]]; then
  echo C_V1_UNMANAGED_VENV_REFUSED >&2; exit 2
fi
mkdir -p "$VENV"
touch "$VENV/.smartdish_c_v1_install_pending"
if [[ ! -x "$VENV/bin/python" ]]; then
  "$PY" -m venv "$VENV" > "$OUT/venv_creation.log" 2>&1 ||
  { echo 'C_V1_VENV_MISSING: install python3.12-venv via Ubuntu apt (explicitly), then retry' >&2; exit 2; }
fi
export PYTHONNOUSERSITE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_INPUT=1
export PIP_CONFIG_FILE=/dev/null TORCH_HOME="$TORCH_CACHE"
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE PIP_INDEX_URL PIP_EXTRA_INDEX_URL
# Lock only the two compatible CPU builds; no automatic GPU/CUDA or ROS Python changes.
"$VENV/bin/python" -m pip install --no-cache-dir --only-binary=:all: \
  "Pillow==10.2.0" "numpy==1.26.4" > "$OUT/pip_basic.log" 2>&1 ||
  { echo C_V1_INSTALL_BASIC_DEPENDENCIES_FAILED >&2; exit 2; }
"$VENV/bin/python" -m pip install --no-cache-dir --only-binary=:all: \
  --index-url https://download.pytorch.org/whl/cpu \
  "torch==2.5.1" "torchvision==0.20.1" > "$OUT/pip_torch_cpu.log" 2>&1 ||
  { echo C_V1_INSTALL_TORCH_CPU_FAILED >&2; exit 2; }
"$VENV/bin/python" -m pip check > "$OUT/pip_check.log" 2>&1 ||
  { echo C_V1_INSTALL_PIP_CHECK_FAILED >&2; exit 2; }

# Metadata and import verification: no model instantiation, no training.
"$VENV/bin/python" - "$VENV" "$OUT/install_receipt.json" <<'PY'
import json,sys
from pathlib import Path
import torch,torchvision,numpy,PIL
from torchvision.models import ResNet18_Weights
root=Path(sys.argv[1]).resolve()
assert Path(sys.prefix).resolve()==root and sys.prefix!=sys.base_prefix, "C_V1_VENV_MISMATCH"
assert torch.__version__.split("+")[0]=="2.5.1", "C_V1_TORCH_VERSION_MISMATCH"
assert torchvision.__version__.split("+")[0]=="0.20.1", "C_V1_TORCHVISION_VERSION_MISMATCH"
assert torch.version.cuda is None, "C_V1_UNEXPECTED_CUDA_BUILD"
assert numpy.__version__=="1.26.4" and PIL.__version__=="10.2.0", "C_V1_IMAGE_DEPS_DRIFT"
weights=ResNet18_Weights.IMAGENET1K_V1
assert weights.url.endswith("/resnet18-f37072fd.pth"), "C_V1_RESNET18_WEIGHTS_ENUM_DRIFT"
receipt={"schema":1,"status":"C_V1_CPU_VENV_INSTALLED","isolated":True,"cpu_only":True,
"python":sys.version.split()[0],"torch":torch.__version__,
"torchvision":torchvision.__version__,"numpy":numpy.__version__,
"Pillow":PIL.__version__,"pretrained_enum":"ResNet18_Weights.IMAGENET1K_V1",
"pretrained_license_reviewed":False,"training_permitted":False,
"training_executed":False,"test_opened":False}
Path(sys.argv[2]).write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
PY

if [[ "$WEIGHTS" == 1 ]]; then
  # Explicit opt-in only: download official weight bytes to SmartDish C's private
  # Torch cache; verify the upstream filename's published SHA prefix + full SHA.
  "$VENV/bin/python" - "$OUT/weight_cache.json" <<'PY'
import hashlib,json,os,tempfile,urllib.request
from pathlib import Path
from urllib.parse import urlparse
import torch
from torchvision.models import ResNet18_Weights
url=ResNet18_Weights.IMAGENET1K_V1.url
assert urlparse(url).netloc=="download.pytorch.org" and url.endswith("/resnet18-f37072fd.pth")
dest=Path(torch.hub.get_dir())/"checkpoints"/"resnet18-f37072fd.pth"
dest.parent.mkdir(parents=True,exist_ok=True)
if not dest.exists():
    fd,name=tempfile.mkstemp(prefix=".c-v1-weight-",dir=dest.parent)
    os.close(fd)
    try:
        with urllib.request.urlopen(url,timeout=90) as src,open(name,"wb") as out:
            while True:
                chunk=src.read(1024*1024)
                if not chunk:break
                out.write(chunk)
        h=hashlib.sha256(Path(name).read_bytes()).hexdigest()
        assert h.startswith("f37072fd"),"C_V1_OFFICIAL_WEIGHTS_SHA_PREFIX_MISMATCH"
        os.replace(name,dest)
    finally:
        if Path(name).exists():Path(name).unlink()
h=hashlib.sha256(dest.read_bytes()).hexdigest()
assert h.startswith("f37072fd"),"C_V1_CACHED_WEIGHTS_SHA_PREFIX_MISMATCH"
Path(__import__("sys").argv[1]).write_text(json.dumps({
"enum":"ResNet18_Weights.IMAGENET1K_V1","full_sha256":h,
"size_bytes":dest.stat().st_size,
"license_reviewed":False,"training_permitted":False},indent=2)+"\n")
PY
fi
"$PY" - "$OUT/install_receipt.json" "$VENV/.smartdish_c_v1_environment.json" "$PIN" <<'PY'
import json,sys
from pathlib import Path
obj=json.loads(Path(sys.argv[1]).read_text())
obj["installer_source_pin"]=sys.argv[3]
Path(sys.argv[2]).write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY
rm -f "$VENV/.smartdish_c_v1_install_pending"
echo "C_V1_CPU_VENV_INSTALLED path=$VENV pretrained_optional_download=$WEIGHTS training=NOT_RUN"
