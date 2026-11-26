"""A17 GPU-retention hypothesis test; never changes system configuration."""
from pathlib import Path
import os,re
CORE="/usr/lib/wsl/lib/libd3d12core.so"
BASELINE_OWNER_SHA="fb2952f63cf7b864ec3a7c5a54a47b9d98439c832b9ac9e0cb7f7821bfe2c671"
BASELINE_PIXEL="5a425c839947dc1bfb71e8b6c8d7636a4bf771b8cc9274c27067bb98fe490954"
def server_override(env):
    if env.get("LD_PRELOAD") or env.get("LD_AUDIT"):raise ValueError("A17_EXISTING_LOADER_OVERRIDE")
    if env.get("GALLIUM_DRIVER")!="d3d12" or env.get("LIBGL_ALWAYS_SOFTWARE") not in (None,"","0") or env.get("MESA_LOADER_DRIVER_OVERRIDE"):raise ValueError("A17_NATIVE_PROFILE_REQUIRED")
    if env.get("MESA_D3D12_DEFAULT_ADAPTER_NAME")!="NVIDIA":raise ValueError("A17_BASELINE_ADAPTER_DRIFT")
    return {"LD_PRELOAD":CORE}
def evaluate(row,maps,glx):
    # Corroboration: same-env GLX plus actual server loaded module paths.
    # No direct GL context instrumentation, no vendor fix claim.
    mapped=all(re.search(r"(?m)^.*\s"+re.escape(p)+r"$",maps) for p in (CORE,"/usr/lib/wsl/lib/libd3d12.so"))
    gpu=bool(re.search(r"OpenGL renderer string: D3D12 \(NVIDIA GeForce RTX 3060\)",glx)) and "Accelerated: yes" in glx
    frames=row.get("frames",[])
    image_ok=bool(frames) and any(x["stamp_ns"]>=1000000000 for x in frames) and all(x["sha256"]==BASELINE_PIXEL for x in frames)
    checks={"native_library_maps":mapped,"same_env_glx_native":gpu,"baseline_pixel_hash_match":image_ok,"actual_data":row.get("data")=="PASS","actual_clean_exit":row.get("cleanup")=="PASS" and row.get("server_rc")==0 and row.get("bridge_rc")==0 and row.get("shutdown_signal_sent") is True,"owned_stopped":row.get("all_owned_stopped") is True}
    return {"checks":checks,"verdict":"GPU_RETENTION_MINIMAL_MITIGATION_PASS" if all(checks.values()) else "GPU_RETENTION_MINIMAL_MITIGATION_HOLD","root_cause_scope":"UNMAPPED_D3D12_TSD_CALLBACK_STRONGLY_SUPPORTED_VENDOR_FIX_NOT_PROVEN","production_cleanup":"NOT_RUN"}
