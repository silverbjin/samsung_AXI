"""S6 G04: launch code should preserve S5 and isolate GUI without bypassing Goal."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(path):return (ROOT/path).read_text()
def test_s6_gui_launch_scoped_default_legacy_and_server_shutdown():
    w=read('src/restaurant_bringup/launch/world.launch.py')
    n=read('src/restaurant_bringup/launch/navigation.launch.py')
    assert 'GroupAction(' in w and 'scoped=True' in w
    assert "SetEnvironmentVariable(name='QT_QPA_PLATFORM',value='xcb'" in w
    assert "'on_exit_shutdown': 'true'" in w
    assert "'on_exit_shutdown':LaunchConfiguration('s6_gui_exit_shutdown')" in w
    assert "DeclareLaunchArgument('s6_gui_xcb',default_value='false')" in w
    assert "DeclareLaunchArgument('s6_gui_exit_shutdown',default_value='true')" in w
    for arg in ('s6_gui_xcb','s6_gui_exit_shutdown'):
        assert "DeclareLaunchArgument('"+arg+"'" in n
        assert "'"+arg+"':LaunchConfiguration('"+arg+"')" in n
def test_s6_gui_failure_detected_before_goal_and_no_d3d12_auto():
    s=read('scripts/ci_s3_amcl_smoke.py')
    assert "if args.s6_vision and args.gui" in s
    assert "'s6_gui_xcb:=true'" in s
    assert "'s6_gui_exit_shutdown:=false'" in s
    assert "raise RuntimeError('S6_GUI_OPENGL_CONTEXT_CREATE_FAILED')" in s
    assert "if proc.poll() is not None:raise RuntimeError('S3_NAV2_LAUNCH_EXITED:" in s
    o=read('scripts/samsungaxi_wsl2_gui_acceptance_once.sh')
    assert "S6_WSLG_GPU_ROUTE=INHERITED_NO_D3D12_AUTO_OVERRIDE" in o
    assert "first=S6_GUI_OPENGL_CONTEXT_CREATE_FAILED" in o
    assert "phase=GAZEBO_GUI_INITIALIZATION" in o
    assert 'YES-S5-LIVE-GOALS' in read('scripts/owner_wsl2_once.sh')
