"""DBG-17: no WSLg GUI proof from glxinfo or Cloud CI alone."""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from smartdish_a_tray_gui_preflight import (
    SDF,PROFILES,FATAL,gui_failure,gui_profile_env,
)
from smartdish_a_tray_release_gate import verify_gui_report


def test_xcb_scoped_to_gui_preserves_forced_nvidia_d3d12():
    source={"DISPLAY":":0","WAYLAND_DISPLAY":"wayland-0",
            "GALLIUM_DRIVER":"d3d12",
            "MESA_D3D12_DEFAULT_ADAPTER_NAME":"NVIDIA",
            "LIBGL_ALWAYS_INDIRECT":"0"}
    actual=gui_profile_env(source,"xcb")
    assert actual["QT_QPA_PLATFORM"]=="xcb"
    assert "WAYLAND_DISPLAY" not in actual
    assert actual["GALLIUM_DRIVER"]=="d3d12"
    assert actual["MESA_D3D12_DEFAULT_ADAPTER_NAME"]=="NVIDIA"
    assert actual["QSG_INFO"]=="1"
    assert source["WAYLAND_DISPLAY"]=="wayland-0"
    assert "QT_QPA_PLATFORM" not in source
    assert gui_profile_env(source,"native")["WAYLAND_DISPLAY"]=="wayland-0"
    with pytest.raises(RuntimeError,match="A13_GUI_XCB_DISPLAY_MISSING"):
        gui_profile_env({"WAYLAND_DISPLAY":"wayland-0"},"xcb")
    with pytest.raises(ValueError,match="A13_GUI_PROFILE_UNAPPROVED"):
        gui_profile_env(source,"secret")


def test_actual_wslg_qt_glx_crash_is_a_fatal_context_blocker():
    log="""D3D12: Removing Device.
glx: failed to create drisw screen
QGLXContext: Failed to create dummy context
Failed to create OpenGL context
QSGRenderLoop::handleContextCreationFailure
Aborted (Signal 6)"""
    assert FATAL.search(log)
    assert gui_failure(log,-6,5,8)=="A13_GUI_CONTEXT_CREATION_FAILED"
    assert gui_failure("",-6,5,8)=="A13_GUI_PROCESS_EXITED_RC=-6"
    assert gui_failure("",None,5,8)=="A13_GUI_STABILITY_WINDOW_INCOMPLETE"
    assert gui_failure("",None,9,8) is None


def build_gui_evidence(folder,sha,verdict="GAZEBO_GUI_PROCESS_STABLE_NO_GLX_ERROR",
                       lifetime=9.25):
    folder.mkdir()
    report={"schema":1,"source_sha":sha,"profile":"xcb",
            "verdict":verdict,"gazebo_server_ready":True,
            "gui_started":True,"all_owned_processes_stopped":True,
            "gui_survival_wall_s":lifetime}
    file_map={"gui_preflight_result.json":json.dumps(report).encode(),
              "gazebo_gui.log":b"GUI alive\n",
              "gazebo_server.log":b"world ready\n",
              "minimal_gui_world.sdf":SDF.encode()}
    rows="".join(hashlib.sha256(b).hexdigest()+"  "+name+"\n"
                 for name,b in sorted(file_map.items()))
    file_map["SHA256SUMS"]=rows.encode()
    archive=folder/"gui_preflight_evidence.tar.gz"
    with tarfile.open(archive,"w:gz") as tar:
        for name,body in file_map.items():
            info=tarfile.TarInfo(name)
            info.size=len(body)
            tar.addfile(info,io.BytesIO(body))
    result=folder/"gui_preflight_result.json"
    result.write_bytes(file_map["gui_preflight_result.json"])
    return result


def test_same_sha_real_gui_receipt_required(tmp_path):
    sha="a"*40
    path=build_gui_evidence(tmp_path/"good",sha)
    receipt=verify_gui_report(path,sha,"xcb")
    assert receipt["source_sha"]==sha
    assert len(receipt["archive_sha256"])==64
    assert receipt["profile"]=="xcb"
    with pytest.raises(RuntimeError,match="A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED"):
        verify_gui_report(path,"b"*40,"xcb")
    with pytest.raises(RuntimeError,match="A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED"):
        verify_gui_report(path,sha,"native")


def test_false_pass_blocked_and_evidence_hash_verified(tmp_path):
    sha="a"*40
    failed=build_gui_evidence(tmp_path/"crash",sha,verdict="FAIL")
    with pytest.raises(RuntimeError,match="A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED"):
        verify_gui_report(failed,sha,"xcb")
    short=build_gui_evidence(tmp_path/"short",sha,lifetime=3)
    with pytest.raises(RuntimeError,match="A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED"):
        verify_gui_report(short,sha,"xcb")
    good=build_gui_evidence(tmp_path/"different",sha)
    good.write_text(json.dumps({"source_sha":sha}))
    with pytest.raises(RuntimeError,match="A13_GUI_CONTEXT_PREFLIGHT_EVIDENCE_NOT_ACCEPTED"):
        verify_gui_report(good,sha,"xcb")


def test_qualification_must_preflight_before_expensive_physics():
    one=(ROOT/"scripts/smartdish_a_tray_one_shot.sh").read_text()
    assert one.index("gui_preflight.py")<one.index("smartdish_a_tray_live.py smoke")
    assert one.index("smartdish_a_tray_release_gate.py gui")<one.index("smartdish_a_tray_live.py smoke")
    assert one.index("smartdish_a_tray_live.py smoke")<one.index("smartdish_a_tray_live.py batch")
    release=(ROOT/"scripts/smartdish_a_tray_release_gate.py").read_text()
    assert 'obj.get("status")!="WSLG_GUI_PREFLIGHT_PASS"' in release
    assert "A13_FINAL_SENSOR_GUI_GATES_NOT_GREEN" in release
    assert "A13_SMOKE_INDEPENDENT_GATES_NOT_GREEN" in release
    live=(ROOT/"scripts/smartdish_a_tray_live.py").read_text()
    assert "sensor_physics_verdict" in live and "gui_verdict" in live
    assert "A13_GUI_FAILURE_SENSOR_CONTINUES=" in live
    assert live.index('(directory/"trial_summary.json").write_text')<live.index("raise RuntimeError(gui_failure_reason)")
    assert 'os.environ.get("SMARTDISH_A_TRAY_GUI_PROFILE","native")' in live
    preflight=(ROOT/"scripts/smartdish_a_tray_gui_preflight.py").read_text()
    assert '"-c","safe.directory="+str(root)' in preflight
    assert 'git config --global' not in preflight
    assert "pkill" not in preflight and "killall" not in preflight
    assert "A13_CAPTURE_AFTER_MATERIAL_FALL_REJECTED" in live
    assert 'ground_truth":"NOT_OPERATOR_APPROVED"' in live
