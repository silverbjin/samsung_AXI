"""G02/G03: isolated profile selection and error classification."""
import importlib.util
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('probe',R/'scripts/s6_wslg_gl_probe.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_xcb_only_changes_qt_and_no_global_env():
    base={'DISPLAY':':0','WAYLAND_DISPLAY':'wayland-0','GALLIUM_DRIVER':'d3d12'}
    e=m.profile(base,'xcb')
    assert e['QT_QPA_PLATFORM']=='xcb'
    assert e['WAYLAND_DISPLAY']=='wayland-0'
    assert e['GALLIUM_DRIVER']=='d3d12'
    assert base.get('QT_QPA_PLATFORM') is None
    n=m.profile(base,'xcb_no_wayland')
    assert 'WAYLAND_DISPLAY' not in n
    assert base['WAYLAND_DISPLAY']=='wayland-0'
def test_render_backend_selector_no_machine_settings():
    base={'DISPLAY':':0','GALLIUM_DRIVER':'d3d12','MESA_D3D12_DEFAULT_ADAPTER_NAME':'NVIDIA'}
    sw=m.profile(base,'xcb_llvmpipe')
    assert sw['LIBGL_ALWAYS_SOFTWARE']=='1'
    assert 'GALLIUM_DRIVER' not in sw and 'MESA_D3D12_DEFAULT_ADAPTER_NAME' not in sw
    assert base['GALLIUM_DRIVER']=='d3d12'
def test_qt_first_failure_does_not_require_goal():
    assert m.classify('Failed to create OpenGL context',None,5)=='S6_GUI_OPENGL_CONTEXT_ERROR'
    assert m.classify('Aborted (core dumped)',-6,2)=='S6_GUI_CRASH'
    assert m.classify('some log',None,9)=='S6_GUI_STILL_RUNNING_VISUAL_NOT_VERIFIED'
    assert m.classify('no error',0,2)=='S6_GUI_EXITED_ZERO_VISUAL_NOT_VERIFIED'
