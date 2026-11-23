"""G07 RED injection: execute the real nested GUI guard, with fake Qt abort log.

AST extraction avoids importing ROS (unavailable in lightweight L0 CI). No
Gazebo, no subprocess, no Goal or ROS graph is started by these tests.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import time
import pytest

ROOT=Path(__file__).resolve().parents[1]

def isolated_real_spin(tmp_path,text,*,s6=True,gui=True,launcher_exit=None):
    log=tmp_path/'s6_nav2_launch.log'
    log.write_text(text)
    raw=ast.parse((ROOT/'scripts/ci_s3_amcl_smoke.py').read_text())
    matches=[node for node in ast.walk(raw)
             if isinstance(node,ast.FunctionDef) and node.name=='spin_once']
    assert len(matches)==1
    f=matches[0]
    module=ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[]))
    called={'spin':0,'goal':0}
    ns={
        'args':SimpleNamespace(s6_vision=s6,gui=gui,log=log),
        'gui_scan_last':[0.0],
        'time':time,
        'proc':SimpleNamespace(poll=lambda:launcher_exit,
                               returncode=launcher_exit),
        'node':object(),
        'rclpy':SimpleNamespace(spin_once=lambda *a,**k:called.__setitem__('spin',called['spin']+1))
    }
    exec(compile(module,str(ROOT/'scripts/ci_s3_amcl_smoke.py'),'exec'),ns)
    return ns['spin_once'],called

def test_real_s6_gui_guard_rejects_injected_qt_failure_before_any_spin(tmp_path):
    spin,called=isolated_real_spin(tmp_path,'[gazebo-2] [GUI] [QT] Failed to create OpenGL context\n')
    with pytest.raises(RuntimeError,match='S6_GUI_OPENGL_CONTEXT_CREATE_FAILED'):
        spin(.1)
    assert called=={'spin':0,'goal':0}

def test_real_s6_gui_guard_rejects_injected_abort(tmp_path):
    spin,called=isolated_real_spin(tmp_path,'[gazebo-2] Aborted (core dumped)\n')
    with pytest.raises(RuntimeError,match='S6_GUI_PROCESS_ABORTED'):
        spin(.1)
    assert called['goal']==0

def test_source_retains_legacy_unchanged_for_s5(tmp_path):
    spin,called=isolated_real_spin(tmp_path,'Failed to create OpenGL context\n',s6=False)
    spin(.1)
    assert called['spin']==1 and called['goal']==0

def test_headless_s6_does_not_falsely_fail_on_unrelated_gui_log(tmp_path):
    spin,called=isolated_real_spin(tmp_path,'Failed to create OpenGL context\n',gui=False)
    spin(.1)
    assert called['spin']==1 and called['goal']==0

def test_launch_exit_zero_is_not_a_goal_success(tmp_path):
    spin,called=isolated_real_spin(tmp_path,'',launcher_exit=0)
    with pytest.raises(RuntimeError,match='S3_NAV2_LAUNCH_EXITED:0'):
        spin(.1)
    assert called['spin']==0
