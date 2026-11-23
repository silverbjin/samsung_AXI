"""G01: Qt first failure takes priority over generic owner or ROS shutdown."""
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('first_failure',ROOT/'scripts/s6_wslg_first_failure.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
def test_gui_failure_is_primary_and_goal_stays_unknown():
    d=m.classify('[gazebo-2] Failed to create OpenGL context\n[gazebo-2] Aborted (core dumped)\n[controller_server] rcl node'+"'"+'s context is invalid\n',
       'S3_NAV2_LAUNCH_EXITED:0',
       'PIN=937fbf025cefec01489c40bc5104c39e3d4709be\nRUN_RC=1\nFIRST_FAILED_MARKER=OWNER_NONZERO_EXIT\nGOAL_SENT=UNKNOWN\nGOAL_AUTHORIZED=FALSE\n')
    assert d['first_failure']=='S6_GUI_OPENGL_CONTEXT_CREATE_FAILED'
    assert d['gpu_gui_error']['line']==1
    assert d['gui_abort']['line']==2
    assert d['ros_context_after']['line']==3
    assert d['goal_sent']=='UNKNOWN'
    assert d['goal_authorized']=='FALSE'
def test_extract_does_not_modify_source_zip(tmp_path):
    p=tmp_path/'run.zip'
    with ZipFile(p,'w') as z:
        z.writestr('ci-s3-summary.txt','[gazebo-2] Failed to create OpenGL context\n')
        z.writestr('status.txt','GOAL_SENT=UNKNOWN\nRUN_RC=1\n')
        z.writestr('run.log','S3_NAV2_LAUNCH_EXITED:0\n')
    old=p.read_bytes()
    from unittest.mock import patch
    with patch('sys.argv',['s6_wslg_first_failure.py','--zip',str(p),'--out',str(tmp_path/'analysis.json')]):
        m.main()
    assert p.read_bytes()==old
    assert len(json.loads((tmp_path/'analysis.json').read_text())['zip_sha256'])==64
