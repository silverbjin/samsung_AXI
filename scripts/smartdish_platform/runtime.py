"""Process-local renderer and compute profiles; never mutate parent env."""
import os

def renderer_env(source, software):
    result=dict(source)
    if software:
        result.update(GALLIUM_DRIVER="llvmpipe",LIBGL_ALWAYS_SOFTWARE="1",QT_QPA_PLATFORM="xcb")
        result.pop("MESA_D3D12_DEFAULT_ADAPTER_NAME",None)
        result.pop("WAYLAND_DISPLAY",None)
    return result

def gui_profile(source, profile):
    if profile not in ("native","xcb","xcb_software"):
        raise ValueError("PLATFORM_GUI_PROFILE_UNKNOWN")
    env=dict(source)
    if profile!="native":
        if not env.get("DISPLAY"): raise ValueError("PLATFORM_DISPLAY_MISSING")
        env["QT_QPA_PLATFORM"]="xcb"
        env.pop("WAYLAND_DISPLAY",None)
    env["QSG_INFO"]="1"
    return renderer_env(env,profile=="xcb_software")

def workload_env(source, role, *, gpu=False):
    if role not in ("A","B","C","D","E"): raise ValueError("PLATFORM_ROLE_UNKNOWN")
    if gpu and role=="B": raise ValueError("PLATFORM_B_OFFLINE_CPU_ONLY")
    env=dict(source)
    if role=="B" or (role=="C" and not gpu):
        env["CUDA_VISIBLE_DEVICES"]=""
        env["HIP_VISIBLE_DEVICES"]=""
    return env
